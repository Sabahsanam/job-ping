import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from connectors.base import JobConnector


class JobviteConnector(JobConnector):

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

    def get_company_slug(self):
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
                "Could not determine Jobvite company slug."
            )

        return parts[0]

    def fetch_jobs(self):
        company_slug = (
            self.get_company_slug()
        )

        search_url = (
            f"https://jobs.jobvite.com/"
            f"{company_slug}/search"
        )

        jobs = []
        seen_urls = set()

        page = 0

        while True:

            print(
                f"Loading Jobvite page {page + 1}..."
            )

            response = self.session.get(
                search_url,
                params={
                    "p": page
                },
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            job_links = []

            for link in soup.find_all(
                "a",
                href=True
            ):

                href = link.get(
                    "href",
                    ""
                )

                if (
                    f"/{company_slug}/job/"
                    not in href
                ):
                    continue

                job_url = urljoin(
                    "https://jobs.jobvite.com",
                    href
                )

                if job_url in seen_urls:
                    continue

                seen_urls.add(
                    job_url
                )

                job_links.append(
                    job_url
                )

            if not job_links:
                break

            for job_url in job_links:

                try:
                    job = self.fetch_job_details(
                        job_url
                    )

                    if job:
                        jobs.append(
                            job
                        )

                except Exception as error:

                    print(
                        "Could not load Jobvite job "
                        f"{job_url}: {error}"
                    )

            page += 1

            if page >= 100:
                break

        return jobs

    def extract_location(self, soup):
        """
        Jobvite pages can represent locations differently.

        Try structured/meta data first, then fall back
        to visible page text.
        """

        # ---------------------------------
        # META TAGS
        # ---------------------------------

        meta_candidates = [
            "jobLocation",
            "location",
            "og:description"
        ]

        for name in meta_candidates:

            element = soup.find(
                "meta",
                attrs={"name": name}
            )

            if not element:

                element = soup.find(
                    "meta",
                    attrs={"property": name}
                )

            if element:

                content = element.get(
                    "content",
                    ""
                ).strip()

                if content:
                    return content


        # ---------------------------------
        # COMMON JOBVITE LOCATION ELEMENTS
        # ---------------------------------

        selectors = [
            ".jv-job-detail-location",
            ".jv-job-detail-meta",
            "[class*='job-location']",
            "[class*='location']",
            "[data-qa*='location']"
        ]

        for selector in selectors:

            elements = soup.select(
                selector
            )

            for element in elements:

                text = element.get_text(
                    " ",
                    strip=True
                )

                if (
                    text
                    and len(text) < 250
                ):
                    return text


        # ---------------------------------
        # JSON-LD
        # ---------------------------------

        json_ld_scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )

        for script in json_ld_scripts:

            try:
                import json

                data = json.loads(
                    script.string or "{}"
                )

                if isinstance(
                    data,
                    list
                ):
                    items = data
                else:
                    items = [data]

                for item in items:

                    locations = item.get(
                        "jobLocation"
                    )

                    if not locations:
                        continue

                    if not isinstance(
                        locations,
                        list
                    ):
                        locations = [
                            locations
                        ]

                    location_strings = []

                    for location in locations:

                        if not isinstance(
                            location,
                            dict
                        ):
                            continue

                        address = location.get(
                            "address",
                            {}
                        )

                        if not isinstance(
                            address,
                            dict
                        ):
                            continue

                        parts = [
                            address.get(
                                "addressLocality"
                            ),
                            address.get(
                                "addressRegion"
                            ),
                            address.get(
                                "addressCountry"
                            )
                        ]

                        location_text = ", ".join(
                            str(part)
                            for part in parts
                            if part
                        )

                        if location_text:
                            location_strings.append(
                                location_text
                            )

                    if location_strings:

                        return " | ".join(
                            location_strings
                        )

            except Exception:
                pass


        return ""

    def fetch_job_details(
        self,
        job_url
    ):
        response = self.session.get(
            job_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # ---------------------------------
        # JOB ID
        # ---------------------------------

        job_id = (
            job_url
            .rstrip("/")
            .split("/")[-1]
        )


        # ---------------------------------
        # TITLE
        # ---------------------------------

        title = ""

        heading = soup.find(
            "h1"
        )

        if heading:

            title = heading.get_text(
                " ",
                strip=True
            )

        if not title:

            title_tag = soup.find(
                "title"
            )

            if title_tag:

                title = title_tag.get_text(
                    " ",
                    strip=True
                )


        # ---------------------------------
        # LOCATION
        # ---------------------------------

        location = self.extract_location(
            soup
        )


        # ---------------------------------
        # DESCRIPTION
        # ---------------------------------

        description = ""

        description_selectors = [
            ".jv-job-detail-description",
            ".job-description",
            "[class*='description']",
            "main"
        ]

        for selector in description_selectors:

            element = soup.select_one(
                selector
            )

            if not element:
                continue

            text = element.get_text(
                "\n",
                strip=True
            )

            if len(text) > len(
                description
            ):
                description = text


        if not description:

            body = soup.find(
                "body"
            )

            if body:

                description = body.get_text(
                    "\n",
                    strip=True
                )


        return {
            "id": job_id,
            "company": self.company_name,
            "title": title,
            "location": location,
            "url": job_url,
            "description": description,
            "source": "jobvite"
        }