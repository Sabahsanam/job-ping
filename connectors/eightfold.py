import html
import json
import re

import requests
from bs4 import BeautifulSoup

from connectors.base import JobConnector


class EightfoldConnector(JobConnector):
    """
    Generic Eightfold careers connector.

    Public careers sites expose:

        GET /api/pcsx/search
            ?domain=<tenant domain>
            &start=<offset>

    The endpoint normally returns 10 jobs at a time.

    Eightfold's timestamp ordering can shift slightly between
    requests, so we intentionally overlap pages by one result:
        0, 9, 18, 27, ...

    This prevents jobs from being lost at page boundaries.
    """

    PAGE_SIZE = 10
    PAGE_STEP = 9

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
                "Accept": "application/json, text/plain, */*",
            }
        )

        self.base_url = self._get_base_url()

        self.domain = None


    def _get_base_url(self):
        match = re.match(
            r"^(https?://[^/]+)",
            self.careers_url
        )

        if not match:
            raise ValueError(
                f"Invalid Eightfold careers URL: "
                f"{self.careers_url}"
            )

        return match.group(1)


    def _load_domain(self):
        """
        Extract the Eightfold PCS domain from the hidden
        pcsx-data configuration.
        """

        response = self.session.get(
            self.careers_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        pcsx_data = soup.find(
            "code",
            id="pcsx-data"
        )

        if pcsx_data:

            raw_text = pcsx_data.get_text(
                strip=True
            )

            raw_text = html.unescape(
                raw_text
            )

            try:

                data = json.loads(
                    raw_text
                )

                domain = str(
                    data.get(
                        "domain",
                        ""
                    )
                ).strip()

                if domain:
                    return domain

            except Exception:
                pass


        decoded_html = html.unescape(
            response.text
        )

        match = re.search(
            r'"domain"\s*:\s*"([^"]+)"',
            decoded_html
        )

        if match:
            return match.group(1)


        raise ValueError(
            f"Could not determine Eightfold domain "
            f"for {self.company_name}"
        )


    def _public_job_url(
        self,
        position_url
    ):
        if not position_url:
            return self.careers_url

        if (
            position_url.startswith("http://")
            or position_url.startswith("https://")
        ):
            return position_url

        return (
            self.base_url
            + position_url
        )


    def _format_location(
        self,
        raw_job
    ):
        locations = raw_job.get(
            "locations",
            []
        )

        if (
            isinstance(locations, list)
            and locations
        ):

            return " | ".join(
                str(location).strip()
                for location in locations
                if str(location).strip()
            )


        standardized = raw_job.get(
            "standardizedLocations",
            []
        )

        if (
            isinstance(standardized, list)
            and standardized
        ):

            return " | ".join(
                str(location).strip()
                for location in standardized
                if str(location).strip()
            )


        return ""


    def fetch_jobs(self):
        """
        Fetch all publicly visible jobs.

        Uses overlapping pagination to avoid losing jobs
        when Eightfold's timestamp ordering changes at
        page boundaries.
        """

        if not self.domain:
            self.domain = self._load_domain()


        jobs = []

        seen_ids = set()

        start = 0
        total_count = None

        consecutive_no_new_pages = 0


        while True:

            response = self.session.get(
                self.base_url
                + "/api/pcsx/search",
                params={
                    "domain": self.domain,
                    "start": start,
                },
                timeout=30
            )

            response.raise_for_status()

            payload = response.json()


            if payload.get(
                "status"
            ) != 200:

                raise RuntimeError(
                    f"Eightfold returned "
                    f"status={payload.get('status')} "
                    f"for {self.company_name}"
                )


            data = payload.get(
                "data",
                {}
            )

            positions = data.get(
                "positions",
                []
            )


            if total_count is None:

                raw_count = data.get(
                    "count"
                )

                try:
                    total_count = int(
                        raw_count
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    total_count = None


            if not positions:
                break


            new_jobs_this_page = 0


            for raw_job in positions:

                job_id = str(
                    raw_job.get(
                        "id",
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

                new_jobs_this_page += 1


                title = str(
                    raw_job.get(
                        "name",
                        ""
                    )
                ).strip()


                position_url = str(
                    raw_job.get(
                        "positionUrl",
                        ""
                    )
                ).strip()


                jobs.append(
                    {
                        "id": job_id,
                        "company": self.company_name,
                        "title": title,
                        "location": self._format_location(
                            raw_job
                        ),
                        "url": self._public_job_url(
                            position_url
                        ),
                        "description": "",
                        "source": "eightfold",
                    }
                )


            if new_jobs_this_page == 0:
                consecutive_no_new_pages += 1
            else:
                consecutive_no_new_pages = 0


            if (
                total_count is not None
                and len(seen_ids) >= total_count
            ):
                break


            if consecutive_no_new_pages >= 3:
                break


            if len(positions) < self.PAGE_SIZE:

                if (
                    total_count is None
                    or len(seen_ids) >= total_count
                ):
                    break


            start += self.PAGE_STEP


            if start > 10000:
                break


        return jobs