import re

import requests
from bs4 import BeautifulSoup

from connectors.base import JobConnector


class SuccessFactorsConnector(JobConnector):
    """
    Generic SAP SuccessFactors / RMK connector.

    SuccessFactors RMK career sites expose search pages like:

        /search/?startrow=0
        /search/?startrow=25
        /search/?startrow=50

    Job cards are rendered in .job-row containers and
    job detail URLs contain a stable numeric job ID.
    """

    PAGE_SIZE = 25


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
                "Accept": "text/html,application/xhtml+xml",
            }
        )

        self.base_url = self._get_base_url()


    def _get_base_url(self):
        match = re.match(
            r"^(https?://[^/]+)",
            self.careers_url
        )

        if not match:
            raise ValueError(
                f"Invalid SuccessFactors careers URL: "
                f"{self.careers_url}"
            )

        return match.group(1)


    def _search_url(self):
        return (
            self.base_url
            + "/search/"
        )


    def _extract_total_count(
        self,
        soup
    ):
        """
        Example:
            Showing 1 to 25 of 294 Jobs
        """

        label = soup.find(
            id="tile-search-results-label"
        )

        if not label:
            return None

        text = label.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"of\s+([\d,]+)\s+Jobs",
            text,
            flags=re.I
        )

        if not match:
            return None

        try:
            return int(
                match.group(1)
                .replace(",", "")
            )
        except ValueError:
            return None


    def _extract_job_id(
        self,
        url
    ):
        match = re.search(
            r"/(\d+)/?$",
            url
        )

        if not match:
            return ""

        return match.group(1)


    def _extract_location(
        self,
        row
    ):
        """
        Try common SuccessFactors location elements first.
        """

        selectors = [
            ".jobLocation",
            ".job-location",
            "[class*=location]",
        ]

        for selector in selectors:

            element = row.select_one(
                selector
            )

            if element:

                text = element.get_text(
                    " ",
                    strip=True
                )

                if text:
                    return text

        return ""


    def fetch_jobs(self):

        jobs = []

        seen_ids = set()

        startrow = 0
        total_count = None


        while True:

            response = self.session.get(
                self._search_url(),
                params={
                    "startrow": startrow,
                },
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )


            if total_count is None:

                total_count = (
                    self._extract_total_count(
                        soup
                    )
                )


            rows = soup.select(
                ".job-row"
            )


            if not rows:
                break


            new_jobs_this_page = 0


            for row in rows:

                link = row.find(
                    "a",
                    href=True
                )

                if not link:
                    continue


                href = link.get(
                    "href",
                    ""
                ).strip()

                if not href:
                    continue


                if href.startswith(
                    "http://"
                ) or href.startswith(
                    "https://"
                ):

                    job_url = href

                else:

                    job_url = (
                        self.base_url
                        + href
                    )


                job_id = self._extract_job_id(
                    job_url
                )

                if not job_id:
                    continue

                if job_id in seen_ids:
                    continue


                seen_ids.add(
                    job_id
                )

                new_jobs_this_page += 1


                title = link.get_text(
                    " ",
                    strip=True
                )


                jobs.append(
                    {
                        "id": job_id,
                        "company": self.company_name,
                        "title": title,
                        "location": self._extract_location(
                            row
                        ),
                        "url": job_url,
                        "description": "",
                        "source": "successfactors",
                    }
                )


            if new_jobs_this_page == 0:
                break


            startrow += self.PAGE_SIZE


            if (
                total_count is not None
                and startrow >= total_count
            ):
                break


            if len(rows) < self.PAGE_SIZE:
                break


            if startrow > 10000:
                break


        return jobs