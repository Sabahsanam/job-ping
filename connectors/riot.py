import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from connectors.base import JobConnector


class RiotConnector(JobConnector):

    def __init__(self, company_name, careers_url):
        super().__init__(
            company_name,
            careers_url
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        })


    def fetch_jobs(self):
        print(
            "Loading Riot Games careers..."
        )

        response = self.session.get(
            self.careers_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        seen_urls = set()


        # -------------------------------------
        # FIND RIOT JOB LINKS
        # -------------------------------------

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            # Riot currently uses URLs such as:
            #
            # /en/work-with-us/job/7844349/...
            # /en/j/7844349

            if (
                "/work-with-us/job/"
                not in href
                and
                not re.search(
                    r"/[a-z]{2}/j/\d+",
                    href
                )
            ):
                continue


            job_url = urljoin(
                "https://www.riotgames.com",
                href
            )


            if job_url in seen_urls:
                continue


            seen_urls.add(
                job_url
            )


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
                    "Could not load Riot job "
                    f"{job_url}: {error}"
                )


        return jobs


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


        # -------------------------------------
        # TITLE
        # -------------------------------------

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
            return None


        # -------------------------------------
        # JOB ID
        # -------------------------------------

        page_text = soup.get_text(
            "\n",
            strip=True
        )

        job_id_match = re.search(
            r"Job\s+Id:\s*(REQ-[A-Za-z0-9-]+)",
            page_text,
            re.IGNORECASE
        )


        if job_id_match:

            job_id = (
                job_id_match.group(1)
            )

        else:

            # Fall back to Riot's numeric
            # career page ID.

            numeric_match = re.search(
                r"/(?:job|j)/(\d+)",
                job_url
            )

            if numeric_match:

                job_id = (
                    numeric_match.group(1)
                )

            else:

                job_id = job_url


        # -------------------------------------
        # LOCATION
        # -------------------------------------

        location = self.extract_location(
            soup,
            title
        )


        # -------------------------------------
        # DESCRIPTION
        # -------------------------------------

        description = self.extract_description(
            soup
        )


        return {
            "id": str(job_id),
            "company": self.company_name,
            "title": title,
            "location": location,
            "url": job_url,
            "description": description,
            "source": "riot"
        }


    def extract_location(
        self,
        soup,
        title
    ):
        """
        Riot pages usually put location immediately
        below the title.

        We also scan for recognizable USA/location
        text as a fallback.
        """

        heading = soup.find(
            "h1"
        )


        # -------------------------------------
        # TRY ELEMENTS AFTER H1
        # -------------------------------------

        if heading:

            current = heading.find_next()

            checked = 0

            while (
                current
                and checked < 12
            ):

                text = current.get_text(
                    " ",
                    strip=True
                )

                if (
                    text
                    and text != title
                    and len(text) < 150
                ):

                    lower_text = (
                        text.lower()
                    )

                    location_markers = [
                        "usa",
                        "united states",
                        "los angeles",
                        "mercer island",
                        "sf bay area",
                        "seattle",
                        "bellevue",
                        "des moines",
                        "dublin",
                        "singapore",
                        "sydney",
                        "shanghai",
                        "seoul",
                        "tokyo",
                        "berlin",
                        "barcelona",
                        "guangzhou",
                        "bangkok",
                        "manila",
                        "paris",
                        "london"
                    ]

                    if any(
                        marker in lower_text
                        for marker
                        in location_markers
                    ):

                        return text

                current = (
                    current.find_next()
                )

                checked += 1


        # -------------------------------------
        # FALLBACK: PAGE TEXT
        # -------------------------------------

        page_text = soup.get_text(
            "\n",
            strip=True
        )

        patterns = [
            r"Los Angeles,\s*USA",
            r"Mercer Island,\s*USA",
            r"SF Bay Area,\s*USA",
            r"Bellevue,\s*USA",
            r"Des Moines,\s*USA"
        ]

        found_locations = []

        for pattern in patterns:

            matches = re.findall(
                pattern,
                page_text,
                re.IGNORECASE
            )

            for match in matches:

                if (
                    match
                    not in found_locations
                ):
                    found_locations.append(
                        match
                    )


        return " | ".join(
            found_locations
        )


    def extract_description(
        self,
        soup
    ):
        """
        Extract the useful job-page text.

        Riot's experience requirements are included
        so experience_filter.py can analyze them.
        """

        main = soup.find(
            "main"
        )

        if main:

            return main.get_text(
                "\n",
                strip=True
            )


        # Some versions of Riot's page do not
        # expose a semantic <main> element.

        body = soup.find(
            "body"
        )

        if body:

            return body.get_text(
                "\n",
                strip=True
            )


        return ""