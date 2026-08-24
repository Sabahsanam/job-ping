import re
import requests

from connectors.base import JobConnector


class OracleConnector(JobConnector):
    """
    Generic Oracle Recruiting Candidate Experience connector.

    Expected careers URL format:
        https://<tenant>.oraclecloud.com/hcmUI/CandidateExperience/en/sites/<SITE>/requisitions

    The connector derives:
      - Oracle API host from the URL
      - Candidate Experience site number from /sites/<SITE>
      - Public requisitions from recruitingCEJobRequisitions
    """

    API_VERSION = "11.13.18.05"
    PAGE_SIZE = 100


    def __init__(
        self,
        company_name,
        careers_url
    ):
        super().__init__(
            company_name,
            careers_url
        )

        self.company_name = company_name
        self.careers_url = careers_url.rstrip("/")

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
            }
        )

        self.api_base = self._extract_api_base()
        self.site_number = self._extract_site_number()


    def _extract_api_base(self):
        match = re.match(
            r"^(https?://[^/]+)",
            self.careers_url
        )

        if not match:
            raise ValueError(
                f"Could not determine Oracle API host from "
                f"{self.careers_url}"
            )

        return match.group(1)


    def _extract_site_number(self):
        match = re.search(
            r"/sites/([^/?#]+)",
            self.careers_url,
            flags=re.I,
        )

        if not match:
            raise ValueError(
                f"Could not determine Oracle site number from "
                f"{self.careers_url}"
            )

        return match.group(1)


    def _listing_endpoint(self):
        return (
            self.api_base
            + f"/hcmRestApi/resources/{self.API_VERSION}"
            + "/recruitingCEJobRequisitions"
        )


    def _detail_endpoint(self):
        return (
            self.api_base
            + f"/hcmRestApi/resources/{self.API_VERSION}"
            + "/recruitingCEJobRequisitionDetails"
        )


    def _public_job_url(self, job_id):
        return (
            self.api_base
            + "/hcmUI/CandidateExperience/en/sites/"
            + self.site_number
            + "/job/"
            + str(job_id)
        )


    def _fetch_page(
        self,
        offset
    ):
        response = self.session.get(
            self._listing_endpoint(),
            params={
                "finder": (
                    "findReqs;"
                    f"siteNumber={self.site_number},"
                    f"limit={self.PAGE_SIZE},"
                    f"offset={offset}"
                ),
                "expand": "requisitionList",
                "onlyData": "true",
            },
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        items = payload.get(
            "items",
            []
        )

        if not items:
            return [], None

        result = items[0]

        jobs = result.get(
            "requisitionList",
            []
        )

        total = result.get(
            "TotalJobsCount"
        )

        return jobs, total


    def fetch_jobs(self):
        jobs = []
        seen_ids = set()

        offset = 0
        total = None

        while True:
            page_jobs, reported_total = self._fetch_page(
                offset
            )

            if total is None and reported_total is not None:
                try:
                    total = int(
                        reported_total
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    total = None

            if not page_jobs:
                break

            for item in page_jobs:
                job_id = str(
                    item.get(
                        "Id",
                        ""
                    )
                ).strip()

                if not job_id:
                    continue

                if job_id in seen_ids:
                    continue

                seen_ids.add(
                    job_id
                )

                jobs.append(
                    {
                        "id": job_id,
                        "company": self.company_name,
                        "title": (
                            item.get("Title")
                            or ""
                        ).strip(),
                        "location": (
                            item.get(
                                "PrimaryLocation"
                            )
                            or ""
                        ).strip(),
                        "url": self._public_job_url(
                            job_id
                        ),
                        "description": "",
                        "source": "oracle",
                    }
                )

            if (
                total is not None
                and len(seen_ids) >= total
            ):
                break

            if len(page_jobs) < self.PAGE_SIZE:
                break

            offset += self.PAGE_SIZE

            if offset > 20000:
                break

        return jobs


    def fetch_description(
        self,
        job_id
    ):
        response = self.session.get(
            self._detail_endpoint(),
            params={
                "finder": (
                    "ById;"
                    f"Id={job_id}"
                ),
                "onlyData": "true",
            },
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        items = payload.get(
            "items",
            []
        )

        if not items:
            return ""

        item = items[0]

        fields = [
            "ExternalDescriptionStr",
            "ExternalResponsibilitiesStr",
            "ExternalQualificationsStr",
            "ExternalJobDescriptionStr",
            "JobDescription",
        ]

        parts = []

        for field in fields:
            value = item.get(
                field
            )

            if value:
                parts.append(
                    str(value)
                )

        return "\n\n".join(
            parts
        )