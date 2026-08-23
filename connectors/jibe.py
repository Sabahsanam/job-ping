import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from connectors.base import JobConnector


class JibeConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        parsed = urlparse(careers_url)

        self.origin = (
            f"{parsed.scheme}://{parsed.netloc}"
        )

        self.api_url = (
            f"{self.origin}/api/jobs"
        )

        self.job_base_url = (
            f"{self.origin}/careers-home/jobs"
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        })


    def clean_html(self, value):
        if not value:
            return ""

        soup = BeautifulSoup(
            value,
            "html.parser"
        )

        return " ".join(
            soup.get_text(
                " ",
                strip=True
            ).split()
        )


    def build_location(self, data):
        location = (
            data.get("full_location")
            or data.get("location_name")
            or data.get("short_location")
            or ""
        )

        location_type = (
            data.get("location_type")
            or ""
        )

        if (
            location_type
            and location_type.lower() == "remote"
            and "remote" not in location.lower()
        ):
            location = (
                f"Remote / {location}"
                if location
                else "Remote"
            )

        return location.strip()


    def fetch_jobs(self):

        jobs = []
        seen_ids = set()

        page = 1

        while True:

            print(
                f"Loading Jibe jobs page {page}..."
            )

            response = self.session.get(
                self.api_url,
                params={
                    "page": page
                },
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            raw_jobs = data.get(
                "jobs",
                []
            )

            print(
                "Jibe jobs returned:",
                len(raw_jobs)
            )

            if not raw_jobs:
                break

            new_jobs_this_page = 0

            for item in raw_jobs:

                job_data = item.get(
                    "data",
                    {}
                )

                job_id = str(
                    job_data.get("req_id")
                    or job_data.get("slug")
                    or ""
                ).strip()

                title = (
                    job_data.get("title")
                    or ""
                ).strip()

                if (
                    not job_id
                    or not title
                ):
                    continue

                if job_id in seen_ids:
                    continue

                seen_ids.add(
                    job_id
                )

                new_jobs_this_page += 1

                location = self.build_location(
                    job_data
                )

                description_parts = [
                    job_data.get(
                        "description",
                        ""
                    ),
                    job_data.get(
                        "qualifications",
                        ""
                    ),
                    job_data.get(
                        "responsibilities",
                        ""
                    )
                ]

                description = " ".join(
                    part
                    for part in [
                        self.clean_html(value)
                        for value in description_parts
                    ]
                    if part
                )

                job_url = (
                    f"{self.job_base_url}/"
                    f"{job_id}"
                )

                jobs.append({
                    "id": job_id,
                    "company": self.company_name,
                    "title": title,
                    "location": location,
                    "url": job_url,
                    "description": description,
                    "source": "jibe"
                })

            if new_jobs_this_page == 0:
                break

            if len(raw_jobs) < 10:
                break

            page += 1

            if page > 200:
                print(
                    "Stopped Jibe pagination "
                    "at 200 pages for safety."
                )
                break

        return jobs