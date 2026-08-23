import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class WorkdayConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        })

        self.tenant = None
        self.locale = None
        self.site = None
        self.origin = None


    def parse_workday_url(self):
        parsed = urlparse(
            self.careers_url
        )

        hostname = parsed.netloc

        tenant = hostname.split(".")[0]

        path_parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        locale = "en-US"
        site = None

        if path_parts:

            if "-" in path_parts[0]:

                locale = path_parts[0]

                if len(path_parts) > 1:
                    site = path_parts[1]

            else:
                site = path_parts[0]

        if not site:
            site = "External"

        origin = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
        )

        return (
            tenant,
            locale,
            site,
            origin
        )


    def fetch_jobs(self):

        (
            self.tenant,
            self.locale,
            self.site,
            self.origin
        ) = self.parse_workday_url()

        api_url = (
            f"{self.origin}/wday/cxs/"
            f"{self.tenant}/{self.site}/jobs"
        )

        jobs = []

        offset = 0
        limit = 20

        # Workday often reports the real total ONLY
        # on the first response.
        expected_total = None

        while True:

            print(
                f"Loading Workday jobs "
                f"{offset + 1}-{offset + limit}..."
            )

            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }

            response = self.session.post(
                api_url,
                json=payload,
                headers={
                    "Referer": self.careers_url
                },
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            postings = data.get(
                "jobPostings",
                []
            )

            # Capture the real total whenever Workday
            # actually provides a useful positive value.
            reported_total = data.get(
                "total"
            )

            if (
                expected_total is None
                and isinstance(
                    reported_total,
                    int
                )
                and reported_total > 0
            ):
                expected_total = reported_total

                print(
                    "Workday reports total:",
                    expected_total
                )


            # No postings means we reached the end.
            if not postings:
                break


            for posting in postings:

                title = posting.get(
                    "title",
                    ""
                )

                location = posting.get(
                    "locationsText",
                    ""
                )

                external_path = posting.get(
                    "externalPath",
                    ""
                )

                if not external_path:
                    continue

                job_url = (
                    f"{self.origin}/"
                    f"{self.locale}/"
                    f"{self.site}"
                    f"{external_path}"
                )

                job_id = (
                    external_path
                    .rstrip("/")
                    .split("/")[-1]
                )

                jobs.append({
                    "id": job_id,
                    "company": self.company_name,
                    "title": title,
                    "location": location,
                    "url": job_url,

                    # Description gets fetched later,
                    # only after title/location filtering.
                    "description": "",

                    "external_path": external_path,

                    "source": "workday"
                })


            offset += len(postings)


            # -----------------------------------------
            # STOP CONDITION 1:
            # We reached the total reported on page 1.
            # -----------------------------------------

            if (
                expected_total is not None
                and offset >= expected_total
            ):
                break


            # -----------------------------------------
            # STOP CONDITION 2:
            # Partial page means no more jobs.
            # -----------------------------------------

            if len(postings) < limit:
                break


            # -----------------------------------------
            # SAFETY LIMIT
            # -----------------------------------------

            # Protect against an unexpected Workday API
            # loop without interfering with normal boards.

            if offset >= 10000:
                print(
                    "Stopped Workday pagination at "
                    "10,000 jobs for safety."
                )
                break


        return jobs


    def enrich_job(self, job):
        """
        Fetch the full description only after a job has
        already passed title + location filtering.
        """

        external_path = job.get(
            "external_path"
        )

        if not external_path:
            return job

        try:

            description = (
                self.fetch_job_description(
                    external_path
                )
            )

            job["description"] = (
                description
            )

        except Exception as error:

            print(
                f"Could not load Workday "
                f"description for "
                f"{job['id']}: "
                f"{error}"
            )

        return job


    def fetch_job_description(
        self,
        external_path
    ):

        detail_url = (
            f"{self.origin}/wday/cxs/"
            f"{self.tenant}/{self.site}"
            f"{external_path}"
        )

        response = self.session.get(
            detail_url,
            headers={
                "Referer": self.careers_url,
                "Accept": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        job_posting = data.get(
            "jobPostingInfo",
            {}
        )

        description = (
            job_posting.get(
                "jobDescription"
            )
            or job_posting.get(
                "description"
            )
            or ""
        )

        return description