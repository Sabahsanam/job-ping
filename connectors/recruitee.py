import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class RecruiteeConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json"
        })

    def get_company_subdomain(self):
        parsed = urlparse(
            self.careers_url
        )

        hostname = parsed.netloc

        # Example:
        # framestore.recruitee.com
        # becomes:
        # framestore

        if not hostname.endswith(
            ".recruitee.com"
        ):
            raise ValueError(
                "Not a valid Recruitee careers URL."
            )

        return hostname.split(".")[0]

    def fetch_jobs(self):
        company_subdomain = (
            self.get_company_subdomain()
        )

        api_url = (
            f"https://{company_subdomain}"
            f".recruitee.com/api/offers/"
        )

        response = self.session.get(
            api_url,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        offers = data.get(
            "offers",
            []
        )

        jobs = []

        for offer in offers:

            job_id = str(
                offer.get("id", "")
            )

            if not job_id:
                continue

            title = (
                offer.get("title")
                or ""
            )

            description = (
                offer.get("description")
                or offer.get("description_html")
                or ""
            )

            # ---------------------------------
            # LOCATION
            # ---------------------------------

            location_parts = []

            city = offer.get("city")
            state = offer.get("state")
            country = offer.get("country")

            if city:
                location_parts.append(city)

            if state:
                location_parts.append(state)

            if country:
                location_parts.append(country)

            location = ", ".join(
                location_parts
            )

            # Some Recruitee boards provide
            # locations as a list instead.
            locations = offer.get(
                "locations"
            )

            if locations:
                formatted_locations = []

                for item in locations:

                    if isinstance(item, dict):

                        parts = [
                            item.get("city"),
                            item.get("state"),
                            item.get("country")
                        ]

                        formatted = ", ".join(
                            part
                            for part in parts
                            if part
                        )

                        if formatted:
                            formatted_locations.append(
                                formatted
                            )

                if formatted_locations:
                    location = " | ".join(
                        formatted_locations
                    )

            # ---------------------------------
            # REMOTE
            # ---------------------------------

            remote = (
                offer.get("remote")
                or offer.get("remote_option")
            )

            if remote:
                if location:
                    location = (
                        f"Remote / {location}"
                    )
                else:
                    location = "Remote"

            # ---------------------------------
            # JOB URL
            # ---------------------------------

            job_url = (
                offer.get("careers_url")
                or offer.get("url")
                or offer.get("apply_url")
            )

            if not job_url:

                slug = (
                    offer.get("slug")
                    or job_id
                )

                job_url = (
                    f"https://"
                    f"{company_subdomain}"
                    f".recruitee.com/o/"
                    f"{slug}"
                )

            jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "location": location,
                "url": job_url,
                "description": description,
                "source": "recruitee"
            })

        return jobs