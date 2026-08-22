import requests
from urllib.parse import urlparse

from connectors.base import JobConnector


class LeverConnector(JobConnector):

    def get_site_name(self):
        parsed_url = urlparse(
            self.careers_url
        )

        path_parts = [
            part
            for part in parsed_url.path.split("/")
            if part
        ]

        if not path_parts:
            raise ValueError(
                "Could not determine Lever site name."
            )

        return path_parts[0]


    def build_location(self, job):
        """
        Build a reliable location string from Lever.

        Lever does not always provide a country field,
        so keep every location value it gives us.
        """

        categories = job.get(
            "categories",
            {}
        ) or {}

        primary_location = (
            categories.get("location")
            or ""
        )

        all_locations = (
            categories.get("allLocations")
            or []
        )

        workplace_type = (
            job.get("workplaceType")
            or ""
        ).strip()


        # -------------------------------------
        # COLLECT LOCATIONS
        # -------------------------------------

        location_parts = []

        if primary_location:
            location_parts.append(
                primary_location
            )


        if isinstance(
            all_locations,
            list
        ):

            for location in all_locations:

                if not location:
                    continue

                if location not in location_parts:
                    location_parts.append(
                        location
                    )


        elif isinstance(
            all_locations,
            str
        ):

            if (
                all_locations
                and all_locations not in location_parts
            ):
                location_parts.append(
                    all_locations
                )


        # -------------------------------------
        # BUILD LOCATION STRING
        # -------------------------------------

        location = " / ".join(
            location_parts
        )


        # -------------------------------------
        # REMOTE / HYBRID / ON-SITE
        # -------------------------------------

        workplace_type = (
            workplace_type
            .lower()
            .strip()
        )


        if workplace_type == "remote":

            if location:
                location = (
                    f"Remote / {location}"
                )
            else:
                location = "Remote"


        elif workplace_type == "hybrid":

            if location:
                location = (
                    f"Hybrid / {location}"
                )
            else:
                location = "Hybrid"


        elif workplace_type in [
            "on-site",
            "onsite"
        ]:

            if location:
                location = (
                    f"On-site / {location}"
                )


        return location


    def fetch_jobs(self):
        site_name = (
            self.get_site_name()
        )

        api_url = (
            f"https://api.lever.co/v0/postings/"
            f"{site_name}"
        )

        response = requests.get(
            api_url,
            params={
                "mode": "json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        jobs = []


        for job in data:

            # -------------------------------------
            # JOB ID
            # -------------------------------------

            job_id = (
                job.get("id")
                or job.get("hostedUrl")
            )

            if not job_id:
                continue


            # -------------------------------------
            # TITLE
            # -------------------------------------

            title = (
                job.get("text")
                or ""
            )


            # -------------------------------------
            # LOCATION
            # -------------------------------------

            location = self.build_location(
                job
            )


            # -------------------------------------
            # DESCRIPTION
            # -------------------------------------

            description = (
                job.get("descriptionPlain")
                or ""
            )


            # -------------------------------------
            # EXTRA REQUIREMENT SECTIONS
            # -------------------------------------

            lists = (
                job.get("lists")
                or []
            )

            list_text = []


            for item in lists:

                heading = (
                    item.get("text")
                    or ""
                )

                content = (
                    item.get("content")
                    or ""
                )


                if heading:
                    list_text.append(
                        heading
                    )


                if content:
                    list_text.append(
                        content
                    )


            if list_text:

                description = (
                    description
                    + "\n"
                    + "\n".join(
                        list_text
                    )
                )


            # -------------------------------------
            # ADDITIONAL DESCRIPTION
            # -------------------------------------

            additional = (
                job.get("additionalPlain")
                or ""
            )


            if additional:

                description = (
                    description
                    + "\n"
                    + additional
                )


            # -------------------------------------
            # JOB URL
            # -------------------------------------

            job_url = (
                job.get("hostedUrl")
                or job.get("applyUrl")
            )


            if not job_url:
                continue


            # -------------------------------------
            # NORMALIZED JOB
            # -------------------------------------

            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "location": location,
                "url": job_url,
                "description": description,
                "source": "lever"
            })


        return jobs