import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from connectors.base import JobConnector


class ICIMSConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        self.base_url = careers_url.rstrip("/")

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        })


    def prime_session(self):
        """
        Visit the iCIMS intro page first so the session can
        receive any cookies iCIMS expects before job searching.
        """

        intro_url = f"{self.base_url}/jobs/intro"

        response = self.session.get(
            intro_url,
            params={
                "mobile": "true",
                "needsRedirect": "false"
            },
            timeout=30
        )

        response.raise_for_status()


    def fetch_jobs(self):

        self.prime_session()

        jobs = []
        seen_ids = set()

        page = 0

        while True:

            print(f"Loading iCIMS page {page + 1}...")

            search_url = f"{self.base_url}/jobs/search"

            response = self.session.get(
                search_url,
                params={
                    "o": "",
                    "pr": page,
                    "schemaId": "",
                    "mobile": "true",
                    "needsRedirect": "false"
                },
                headers={
                    "Referer": (
                        f"{self.base_url}/jobs/intro"
                        "?mobile=true&needsRedirect=false"
                    )
                },
                timeout=30
            )

            response.raise_for_status()

            html = response.text

            # Useful diagnostic
            print(
                f"iCIMS response: "
                f"{response.status_code}, "
                f"{len(html)} characters"
            )

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            job_links = self.extract_job_links(
                soup,
                html
            )

            print(
                f"Found {len(job_links)} job links "
                f"on iCIMS page {page + 1}."
            )

            # If page 1 contains no jobs, iCIMS likely
            # returned an interstitial/cookie page.
            if not job_links:

                if page == 0:

                    page_text = soup.get_text(
                        " ",
                        strip=True
                    )

                    if (
                        "Enable Cookies" in page_text
                        or "Please Enable Cookies" in page_text
                    ):
                        print(
                            "iCIMS returned its cookie/interstitial "
                            "page instead of job listings."
                        )

                    else:
                        print(
                            "iCIMS returned a page, but no job "
                            "links could be detected."
                        )

                break

            new_jobs_this_page = 0

            for job_id, job_url in job_links:

                if job_id in seen_ids:
                    continue

                seen_ids.add(job_id)
                new_jobs_this_page += 1

                try:
                    job = self.fetch_job_details(
                        job_id,
                        job_url
                    )

                    if job:
                        jobs.append(job)

                except Exception as error:
                    print(
                        f"Could not load iCIMS job "
                        f"{job_id}: {error}"
                    )

            if new_jobs_this_page == 0:
                break

            page += 1

            # Safety limit
            if page >= 50:
                print(
                    "Stopped iCIMS pagination at "
                    "50 pages for safety."
                )
                break

        return jobs


    def extract_job_links(
        self,
        soup,
        html
    ):
        links = {}

        # -----------------------------
        # METHOD 1:
        # Parse normal <a href=""> tags
        # -----------------------------

        for anchor in soup.find_all(
            "a",
            href=True
        ):

            href = anchor.get(
                "href",
                ""
            )

            match = re.search(
                r"/jobs/(\d+)/.*?/job",
                href,
                re.IGNORECASE
            )

            if match:

                job_id = match.group(1)

                full_url = urljoin(
                    self.base_url,
                    href
                )

                # Remove iframe/query information
                full_url = full_url.split("?")[0]

                links[job_id] = full_url

        # -----------------------------
        # METHOD 2:
        # Raw HTML fallback
        # -----------------------------

        if not links:

            matches = re.findall(
                r'["\']([^"\']*/jobs/'
                r'(\d+)/[^"\']*/job'
                r'(?:\?[^"\']*)?)["\']',
                html,
                re.IGNORECASE
            )

            for href, job_id in matches:

                full_url = urljoin(
                    self.base_url,
                    href
                )

                full_url = full_url.split("?")[0]

                links[job_id] = full_url

        return list(
            links.items()
        )


    def fetch_job_details(
        self,
        job_id,
        job_url
    ):

        response = self.session.get(
            job_url,
            params={
                "in_iframe": "1"
            },
            headers={
                "Referer": (
                    f"{self.base_url}/jobs/search"
                )
            },
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = self.extract_title(
            soup
        )

        if not title:
            return None

        location = self.extract_location(
            soup
        )

        description = self.extract_description(
            soup
        )

        return {
            "id": str(job_id),
            "company": self.company_name,
            "title": title,
            "location": location,
            "url": job_url,
            "description": description,
            "source": "icims"
        }


    def extract_title(
        self,
        soup
    ):

        # iCIMS normally places the title in h1
        heading = soup.find("h1")

        if heading:
            title = heading.get_text(
                " ",
                strip=True
            )

            if title:
                return title

        # Fallback to page title
        if soup.title:

            title = soup.title.get_text(
                " ",
                strip=True
            )

            if " in " in title:
                title = title.split(
                    " in ",
                    1
                )[0]

            return title.strip()

        return ""


    def extract_location(
        self,
        soup
    ):

        text = soup.get_text(
            "\n",
            strip=True
        )

        match = re.search(
            r"Job Locations?\s+"
            r"(.*?)\s+"
            r"Requisition ID",
            text,
            re.IGNORECASE
            | re.DOTALL
        )

        if match:

            location = match.group(1)

            return " ".join(
                location.split()
            )

        return ""


    def extract_description(
        self,
        soup
    ):

        text = soup.get_text(
            " ",
            strip=True
        )

        return " ".join(
            text.split()
        )