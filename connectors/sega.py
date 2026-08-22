import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from connectors.base import JobConnector


class SegaConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        })


    def extract_job_id(self, job_url):
        """
        Example:

        https://careers.sega.co.uk/vacancies/ai-designer

        becomes:

        ai-designer
        """

        parsed = urlparse(job_url)

        parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if (
            len(parts) >= 2
            and parts[-2] == "vacancies"
        ):
            return parts[-1]

        return job_url


    def is_real_job_url(self, job_url):
        """
        Accept only:

        /vacancies/<job-slug>

        Reject:

        /vacancies
        /vacancies?page=1
        /vacancies?f[0]=...
        """

        parsed = urlparse(job_url)

        parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) != 2:
            return False

        if parts[0] != "vacancies":
            return False

        if not parts[1]:
            return False

        return True


    def extract_listing_jobs(self, soup):
        jobs = []
        seen_ids = set()

        for anchor in soup.find_all(
            "a",
            href=True
        ):

            href = anchor.get(
                "href",
                ""
            )

            job_url = urljoin(
                self.careers_url,
                href
            )

            if not self.is_real_job_url(
                job_url
            ):
                continue

            job_id = self.extract_job_id(
                job_url
            )

            if job_id in seen_ids:
                continue

            title = anchor.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            seen_ids.add(
                job_id
            )

            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,

                # SEGA listing pages do not reliably
                # provide location beside each role.
                "location": "",

                "url": job_url,
                "description": "",
                "source": "sega"
            })

        return jobs


    def fetch_jobs(self):
        """
        FAST PHASE

        Keep requesting SEGA listing pages until
        a page contains no new jobs.

        This avoids relying on the site's Next button.
        """

        all_jobs = []
        seen_ids = set()

        page = 0

        while True:

            print(
                f"Loading SEGA jobs page "
                f"{page + 1}..."
            )

            response = self.session.get(
                self.careers_url,
                params={
                    "page": page
                },
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            page_jobs = self.extract_listing_jobs(
                soup
            )

            new_jobs = []

            for job in page_jobs:

                job_id = job["id"]

                if job_id in seen_ids:
                    continue

                seen_ids.add(
                    job_id
                )

                new_jobs.append(
                    job
                )

            # No unseen jobs means pagination is done.
            if not new_jobs:
                break

            all_jobs.extend(
                new_jobs
            )

            print(
                f"Found {len(all_jobs)} "
                f"SEGA jobs so far..."
            )

            page += 1

            # Safety limit.
            if page > 50:
                break

        return all_jobs


    def enrich_job(self, job):
        """
        Load the full SEGA job page only after
        the title is potentially relevant.

        Provides:
        - canonical title
        - country/location
        - full description
        """

        job_url = job.get(
            "url"
        )

        if not job_url:
            return job

        response = self.session.get(
            job_url,
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

        location = self.extract_location(
            soup
        )

        description = self.extract_description(
            soup
        )

        if title:
            job["title"] = title

        if location:
            job["location"] = location

        job["description"] = description

        return job


    def extract_title(self, soup):
        """
        SEGA pages contain:

        h1 -> SEGA Careers
        h1 -> Actual Job Title

        Return the actual role title.
        """

        headings = soup.find_all(
            "h1"
        )

        for heading in headings:

            title = heading.get_text(
                " ",
                strip=True
            )

            if (
                title
                and title.lower()
                != "sega careers"
            ):
                return title

        return ""


    def extract_location(self, soup):
        """
        Example:

        <span class="job-country">
            United Kingdom
        </span>
        """

        location_element = soup.select_one(
            ".job-country"
        )

        if location_element:

            return location_element.get_text(
                " ",
                strip=True
            )

        return ""


    def extract_description(self, soup):

        for tag in soup(
            [
                "script",
                "style",
                "noscript"
            ]
        ):
            tag.decompose()

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