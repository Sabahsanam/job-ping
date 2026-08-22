import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class SmartRecruitersConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*"
        })


    def get_company_identifier(self):
        parsed_url = urlparse(self.careers_url)

        parts = [
            part
            for part in parsed_url.path.split("/")
            if part
        ]

        if not parts:
            raise ValueError(
                "Could not determine SmartRecruiters company identifier."
            )

        return parts[0]


    def fetch_jobs(self):
        company_id = self.get_company_identifier()

        api_url = (
            f"https://api.smartrecruiters.com/v1/companies/"
            f"{company_id}/postings"
        )

        jobs = []

        offset = 0
        limit = 100

        while True:

            response = self.session.get(
                api_url,
                params={
                    "limit": limit,
                    "offset": offset
                },
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            postings = data.get(
                "content",
                []
            )

            if not postings:
                break

            for posting in postings:

                job_id = str(
                    posting.get("id")
                    or posting.get("uuid")
                    or ""
                )

                if not job_id:
                    continue

                title = posting.get(
                    "name",
                    ""
                )

                location_data = (
                    posting.get("location")
                    or {}
                )

                location_parts = [
                    location_data.get("city"),
                    location_data.get("region"),
                    location_data.get("country")
                ]

                location = ", ".join(
                    part
                    for part in location_parts
                    if part
                )

                if location_data.get("remote"):
                    if location:
                        location = f"Remote / {location}"
                    else:
                        location = "Remote"

                job_url = (
                    f"https://jobs.smartrecruiters.com/"
                    f"{company_id}/{job_id}"
                )

                description = ""

                try:
                    description = self.fetch_job_description(
                        company_id,
                        job_id
                    )

                except Exception as error:
                    print(
                        f"Could not load SmartRecruiters "
                        f"description for {job_id}: {error}"
                    )

                jobs.append({
                    "id": job_id,
                    "company": self.company_name,
                    "title": title,
                    "location": location,
                    "url": job_url,
                    "description": description,
                    "source": "smartrecruiters"
                })

            offset += len(postings)

            total = data.get(
                "totalFound",
                0
            )

            if offset >= total:
                break

            if len(postings) < limit:
                break

        return jobs


    def fetch_job_description(
        self,
        company_id,
        job_id
    ):
        detail_url = (
            f"https://api.smartrecruiters.com/v1/companies/"
            f"{company_id}/postings/{job_id}"
        )

        response = self.session.get(
            detail_url,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        sections = (
            data.get("jobAd", {})
            .get("sections", {})
        )

        description_parts = []

        for section_name in [
            "companyDescription",
            "jobDescription",
            "qualifications",
            "additionalInformation"
        ]:
            section = sections.get(
                section_name
            )

            if not section:
                continue

            text = section.get(
                "text",
                ""
            )

            if text:
                description_parts.append(
                    text
                )

        return " ".join(
            description_parts
        )