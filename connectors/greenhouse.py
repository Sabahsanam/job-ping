import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class GreenhouseConnector(JobConnector):

    def get_board_token(self):
        parsed_url = urlparse(self.careers_url)

        path_parts = [
            part
            for part in parsed_url.path.split("/")
            if part
        ]

        if not path_parts:
            raise ValueError(
                "Could not determine the Greenhouse company token."
            )

        return path_parts[0]

    def fetch_jobs(self):

        board_token = self.get_board_token()

        api_url = (
            f"https://boards-api.greenhouse.io/"
            f"v1/boards/{board_token}/jobs"
        )

        response = requests.get(
            api_url,
            params={"content": "true"},
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        jobs = []

        for job in data.get("jobs", []):

            jobs.append({
    "id": str(job["id"]),
    "company": self.company_name,
    "title": job.get("title", ""),
    "location": (
        job.get("location") or {}
    ).get("name"),
    "url": job.get("absolute_url"),
    "description": job.get("content", ""),
    "source": "greenhouse"
})

        return jobs