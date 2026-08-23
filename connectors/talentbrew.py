import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from connectors.base import JobConnector


class TalentBrewConnector(JobConnector):

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

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })


    def _search_url(
        self,
        page
    ):

        if page <= 1:
            return self.careers_url

        separator = (
            "&"
            if "?" in self.careers_url
            else "?"
        )

        return (
            f"{self.careers_url}"
            f"{separator}p={page}"
        )


    def _clean_text(
        self,
        value
    ):

        if not value:
            return ""

        return re.sub(
            r"\s+",
            " ",
            value
        ).strip()


    def _get_job_id(
        self,
        href
    ):

        match = re.search(
            r"/job/.+?/(\d+)/(\d+)$",
            href
        )

        if not match:
            return None

        return match.group(2)


    def _parse_page(
        self,
        html
    ):

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        results_section = soup.find(
            id="search-results"
        )

        total_pages = 1
        current_page = 1

        if results_section:

            try:
                total_pages = int(
                    results_section.get(
                        "data-total-pages",
                        1
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                total_pages = 1


            try:
                current_page = int(
                    results_section.get(
                        "data-current-page",
                        1
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                current_page = 1


        jobs = []
        seen_ids = set()

        for link in soup.find_all(
            "a",
            class_="sr-item",
            href=True
        ):

            href = link["href"]

            job_id = self._get_job_id(
                href
            )

            if not job_id:
                continue

            if job_id in seen_ids:
                continue

            title_element = link.find(
                "h2"
            )

            location_element = link.find(
                "span",
                class_="job-location"
            )

            title = self._clean_text(
                title_element.get_text(
                    " ",
                    strip=True
                )
                if title_element
                else link.get(
                    "data-title",
                    ""
                )
            )

            location = self._clean_text(
                location_element.get_text(
                    " ",
                    strip=True
                )
                if location_element
                else ""
            )

            if not title:
                continue

            seen_ids.add(
                job_id
            )

            jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "location": location,
                "url": urljoin(
                    self.careers_url,
                    href
                ),
                "description": "",
                "source": "talentbrew"
            })

        return (
            jobs,
            current_page,
            total_pages
        )


    def fetch_jobs(
        self
    ):

        all_jobs = []
        seen_ids = set()

        page = 1
        total_pages = None

        while True:

            url = self._search_url(
                page
            )

            response = self.session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            (
                jobs,
                current_page,
                detected_total_pages
            ) = self._parse_page(
                response.text
            )

            if total_pages is None:
                total_pages = (
                    detected_total_pages
                )

            if not jobs:
                break

            new_jobs = 0

            for job in jobs:

                if job["id"] in seen_ids:
                    continue

                seen_ids.add(
                    job["id"]
                )

                all_jobs.append(
                    job
                )

                new_jobs += 1

            if new_jobs == 0:
                break

            if current_page >= total_pages:
                break

            page += 1

            if page > 200:
                break

        return all_jobs