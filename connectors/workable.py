import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from connectors.base import JobConnector


class WorkableConnector(JobConnector):

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


    def get_account_name(self):
        """
        Example:

        https://apply.workable.com/square-enix-america/

        becomes:

        square-enix-america
        """

        parsed = urlparse(
            self.careers_url
        )

        parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if not parts:
            raise ValueError(
                "Could not determine Workable account name."
            )

        return parts[0]


    def clean_html(self, html):
        """
        Convert Workable's HTML job description
        into normal readable text.
        """

        if not html:
            return ""

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        return soup.get_text(
            "\n",
            strip=True
        )


    def build_location(self, job):
        """
        Workable may provide:

        country
        city
        state

        and/or:

        locations: [
            {
                country,
                countryCode,
                city,
                region
            }
        ]

        Prefer the structured locations array.
        """

        locations = job.get(
            "locations",
            []
        ) or []

        location_strings = []


        for location in locations:

            if location.get(
                "hidden"
            ):
                continue

            country = (
                location.get(
                    "country"
                )
                or ""
            ).strip()

            city = (
                location.get(
                    "city"
                )
                or ""
            ).strip()

            region = (
                location.get(
                    "region"
                )
                or ""
            ).strip()


            parts = []

            if country:
                parts.append(
                    country
                )

            if city:
                parts.append(
                    city
                )

            if region:
                parts.append(
                    region
                )


            location_text = ", ".join(
                parts
            )

            if (
                location_text
                and location_text
                not in location_strings
            ):
                location_strings.append(
                    location_text
                )


        if location_strings:

            return " / ".join(
                location_strings
            )


        # --------------------------------------------
        # FALLBACK LOCATION
        # --------------------------------------------

        country = (
            job.get(
                "country"
            )
            or ""
        ).strip()

        city = (
            job.get(
                "city"
            )
            or ""
        ).strip()

        state = (
            job.get(
                "state"
            )
            or ""
        ).strip()


        parts = []

        if country:
            parts.append(
                country
            )

        if city:
            parts.append(
                city
            )

        if state:
            parts.append(
                state
            )


        return ", ".join(
            parts
        )


    def fetch_jobs(self):
        """
        Fetch all published jobs from Workable's
        public account endpoint.

        Example:

        https://www.workable.com/api/accounts/
        square-enix-america?details=true
        """

        account_name = self.get_account_name()

        api_url = (
            "https://www.workable.com/api/accounts/"
            f"{account_name}"
        )


        response = self.session.get(
            api_url,
            params={
                "details": "true"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        raw_jobs = data.get(
            "jobs",
            []
        ) or []

        jobs = []


        for raw_job in raw_jobs:

            job_id = (
                raw_job.get(
                    "shortcode"
                )
                or raw_job.get(
                    "id"
                )
                or raw_job.get(
                    "url"
                )
            )

            if not job_id:
                continue


            title = (
                raw_job.get(
                    "title"
                )
                or ""
            ).strip()


            if not title:
                continue


            job_url = (
                raw_job.get(
                    "url"
                )
                or raw_job.get(
                    "shortlink"
                )
                or raw_job.get(
                    "application_url"
                )
            )


            if not job_url:
                continue


            location = self.build_location(
                raw_job
            )


            description = self.clean_html(
                raw_job.get(
                    "description",
                    ""
                )
            )


            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "location": location,
                "url": job_url,
                "description": description,
                "source": "workable"
            })


        return jobs