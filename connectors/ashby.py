import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class AshbyConnector(JobConnector):

    def get_board_name(self):
        parsed_url = urlparse(self.careers_url)

        path_parts = [
            part
            for part in parsed_url.path.split("/")
            if part
        ]

        if not path_parts:
            raise ValueError(
                "Could not determine the Ashby job board name."
            )

        return path_parts[0]

    def fetch_jobs(self):
        board_name = self.get_board_name()

        api_url = (
            f"https://api.ashbyhq.com/posting-api/"
            f"job-board/{board_name}"
        )

        response = requests.get(
            api_url,
            params={
                "includeCompensation": "true"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        jobs = []

        for job in data.get("jobs", []):

            # Ignore unlisted/private postings
            if not job.get("isListed", True):
                continue

            job_url = (
                job.get("jobUrl")
                or job.get("applyUrl")
            )

            if not job_url:
                continue

            # Ashby already gives us the full
            # plain-text description.
            description = (
                job.get("descriptionPlain")
                or ""
            )

            location = job.get(
                "location",
                ""
            )

            # Add a little more useful location context
            # for remote jobs.
            if job.get("isRemote"):
                if location:
                    location = f"Remote / {location}"
                else:
                    location = "Remote"

            jobs.append({
                "id": job_url,
                "company": self.company_name,
                "title": job.get("title", ""),
                "location": location,
                "url": job_url,
                "description": description,
                "source": "ashby"
            })

        return jobs