import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from connectors.base import JobConnector


class RobloxConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(
            company_name,
            careers_url
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        })


    def fetch_jobs(self):
        print(
            "Loading Roblox careers..."
        )

        response = self.session.get(
            self.careers_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        seen_urls = set()


        # -------------------------------------
        # FIND ROBLOX JOB LINKS
        # -------------------------------------

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            if not re.search(
                r"/jobs/\d+",
                href
            ):
                continue


            job_url = urljoin(
                "https://careers.roblox.com",
                href
            )


            if job_url in seen_urls:
                continue


            seen_urls.add(
                job_url
            )


            try:

                job = self.fetch_job_details(
                    job_url
                )

                if job:
                    jobs.append(
                        job
                    )

            except Exception as error:

                print(
                    "Could not load Roblox job "
                    f"{job_url}: {error}"
                )


        return jobs


    def fetch_job_details(
        self,
        job_url
    ):

        response = self.session.get(
            job_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # -------------------------------------
        # TITLE
        # -------------------------------------

        heading = soup.find(
            "h1"
        )

        if not heading:
            return None


        title = heading.get_text(
            " ",
            strip=True
        )


        # -------------------------------------
        # PAGE TEXT
        # -------------------------------------

        page_text = soup.get_text(
            "\n",
            strip=True
        )


        # -------------------------------------
        # JOB ID
        # -------------------------------------

        job_id_match = re.search(
            r"\bID:\s*(\d+)",
            page_text,
            re.IGNORECASE
        )


        if job_id_match:

            job_id = (
                job_id_match.group(1)
            )

        else:

            url_id_match = re.search(
                r"/jobs/(\d+)",
                job_url
            )

            if url_id_match:

                job_id = (
                    url_id_match.group(1)
                )

            else:

                job_id = job_url


        # -------------------------------------
        # LOCATION
        # -------------------------------------

        location = self.extract_location(
            page_text
        )


        # -------------------------------------
        # DESCRIPTION
        # -------------------------------------

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
            "source": "roblox"
        }


    def extract_location(
        self,
        page_text
    ):

        patterns = [
            (
                r"(San Mateo,\s*CA,\s*"
                r"United States)"
            ),
            (
                r"(San Mateo,\s*California,\s*"
                r"United States)"
            ),
            (
                r"(United States[^\\n]*)"
            )
        ]


        for pattern in patterns:

            match = re.search(
                pattern,
                page_text,
                re.IGNORECASE
            )

            if match:

                return (
                    match.group(1)
                    .strip()
                )


        return ""


    def extract_description(
        self,
        soup
    ):

        main = soup.find(
            "main"
        )


        if main:

            return main.get_text(
                "\n",
                strip=True
            )


        body = soup.find(
            "body"
        )


        if body:

            return body.get_text(
                "\n",
                strip=True
            )


        return ""