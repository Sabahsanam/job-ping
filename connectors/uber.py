import requests
from bs4 import BeautifulSoup

from connectors.base import JobConnector


class UberConnector(JobConnector):
    """
    Uber Careers connector.

    Uber's public careers frontend is backed by Oracle Recruiting
    Candidate Experience.

    Listings:
        recruitingCEJobRequisitions
        finder=findReqs;siteNumber=CX_1,...

    Details:
        recruitingCEJobRequisitionDetails
        finder=ById;Id=<public Uber job ID>

    This lets us collect all jobs without scraping Uber's
    Cloudflare-protected pagination.
    """

    ORACLE_BASE = (
        "https://iaziqy.fa.ocs.oraclecloud.com/"
        "hcmRestApi/resources/11.13.18.05"
    )

    LISTINGS_URL = (
        ORACLE_BASE
        + "/recruitingCEJobRequisitions"
    )

    DETAILS_URL = (
        ORACLE_BASE
        + "/recruitingCEJobRequisitionDetails"
    )

    SITE_NUMBER = "CX_1"

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
        self.careers_url = careers_url

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _public_job_url(
        self,
        job_id
    ):
        return (
            "https://jobs.uber.com/"
            f"en/jobs/{job_id}/"
        )

    def _clean_html(
        self,
        value
    ):
        if not value:
            return ""

        soup = BeautifulSoup(
            value,
            "html.parser"
        )

        return soup.get_text(
            " ",
            strip=True
        )

    # ---------------------------------------------------------
    # Listing collection
    # ---------------------------------------------------------

    def fetch_jobs(self):
        """
        Fetch all currently available Uber jobs from Oracle.

        The Oracle findReqs response contains a wrapper object.
        expand=requisitionList embeds the actual job records.

        We paginate using the finder offset.
        """

        jobs = []
        seen_ids = set()

        offset = 0
        total_jobs = None

        while True:

            finder = (
                "findReqs;"
                f"siteNumber={self.SITE_NUMBER},"
                f"limit={self.PAGE_SIZE},"
                f"offset={offset}"
            )

            response = self.session.get(
                self.LISTINGS_URL,
                params={
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": finder,
                },
                timeout=45
            )

            response.raise_for_status()

            data = response.json()

            wrapper_items = data.get(
                "items",
                []
            )

            if not wrapper_items:
                break

            wrapper = wrapper_items[0]

            if total_jobs is None:
                raw_total = wrapper.get(
                    "TotalJobsCount"
                )

                try:
                    total_jobs = int(
                        raw_total
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    total_jobs = None

            batch = wrapper.get(
                "requisitionList",
                []
            )

            if not batch:
                break

            for raw_job in batch:

                job_id = str(
                    raw_job.get(
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

                title = str(
                    raw_job.get(
                        "Title",
                        ""
                    )
                ).strip()

                location = str(
                    raw_job.get(
                        "PrimaryLocation",
                        ""
                    )
                    or ""
                ).strip()

                jobs.append(
                    {
                        "id": job_id,
                        "company": self.company_name,
                        "title": title,
                        "location": location,
                        "url": self._public_job_url(
                            job_id
                        ),
                        "description": "",
                        "source": "uber",
                    }
                )

            offset += self.PAGE_SIZE

            if (
                total_jobs is not None
                and offset >= total_jobs
            ):
                break

            if len(batch) < self.PAGE_SIZE:
                break

            # Emergency safety stop.
            if offset > 5000:
                break

        return jobs

    # ---------------------------------------------------------
    # Description enrichment
    # ---------------------------------------------------------

    def fetch_description(
        self,
        job_id
    ):
        """
        Fetch the full posting text for one Uber job.

        We intentionally do this separately from fetch_jobs().
        Job Ping can run cheap title/location filtering first and
        only request descriptions for surviving candidates.
        """

        response = self.session.get(
            self.DETAILS_URL,
            params={
                "finder": (
                    f"ById;Id={job_id}"
                ),
                "fields": (
                    "Id,"
                    "Title,"
                    "ExternalDescriptionStr,"
                    "ExternalQualificationsStr,"
                    "ExternalResponsibilitiesStr,"
                    "ShortDescriptionStr"
                ),
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        items = data.get(
            "items",
            []
        )

        if not items:
            return ""

        item = items[0]

        sections = [
            item.get(
                "ExternalDescriptionStr"
            ),
            item.get(
                "ExternalQualificationsStr"
            ),
            item.get(
                "ExternalResponsibilitiesStr"
            ),
            item.get(
                "ShortDescriptionStr"
            ),
        ]

        cleaned_sections = []

        for section in sections:

            text = self._clean_html(
                section
            )

            if text:
                cleaned_sections.append(
                    text
                )

        return " ".join(
            cleaned_sections
        )