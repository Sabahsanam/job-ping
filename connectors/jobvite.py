import json
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
        """
        Supports multiple Jobvite URL formats.

        Examples:

        https://jobs.jobvite.com/dneg
        -> dneg

        https://jobs.jobvite.com/dneg/search
        -> dneg

        https://jobs.jobvite.com/careers/capcomusa/jobs
        -> capcomusa

        https://jobs.jobvite.com/capcomusa
        -> capcomusa
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
                "Could not determine Jobvite company slug."
            )


        # --------------------------------------------
        # NEWER JOBVITE / CAREERS FORMAT
        # --------------------------------------------
        #
        # /careers/capcomusa/jobs

        if (
            len(parts) >= 2
            and parts[0].lower() == "careers"
        ):
            return parts[1]


        # --------------------------------------------
        # STANDARD JOBVITE FORMAT
        # --------------------------------------------
        #
        # /dneg
        # /dneg/search

        return parts[0]


    def get_search_urls(self):
        """
        Jobvite companies can expose jobs through
        slightly different board layouts.

        Try both common formats.
        """

        company_slug = self.get_company_slug()

        return [
            (
                f"https://jobs.jobvite.com/"
                f"{company_slug}/search"
            ),
            (
                f"https://jobs.jobvite.com/"
                f"{company_slug}"
            )
        ]


    def extract_job_links(
        self,
        soup,
        company_slug
    ):
        """
        Extract:

        /dneg/job/...
        /capcomusa/job/...
        """

        job_links = []
        seen = set()

        expected_path = (
            f"/{company_slug}/job/"
        ).lower()


        for link in soup.find_all(
            "a",
            href=True
        ):

            href = (
                link.get(
                    "href",
                    ""
                )
                or ""
            )

            if (
                expected_path
                not in href.lower()
            ):
                continue


            job_url = urljoin(
                "https://jobs.jobvite.com",
                href
            )


            if job_url in seen:
                continue

            seen.add(
                job_url
            )

            job_links.append(
                job_url
            )


        return job_links


    def fetch_jobs(self):
        """
        Supports both:

        DNEG-style paginated Jobvite search pages

        and:

        Capcom-style direct company boards.
        """

        company_slug = (
            self.get_company_slug()
        )

        jobs = []
        seen_job_urls = set()

        search_urls = self.get_search_urls()


        for search_url in search_urls:

            page = 0
            found_any_jobs = False


            while True:

                print(
                    f"Loading Jobvite page "
                    f"{page + 1}..."
                )


                # ------------------------------------
                # SEARCH PAGE
                # ------------------------------------

                params = {}

                if search_url.endswith(
                    "/search"
                ):
                    params["p"] = page


                response = self.session.get(
                    search_url,
                    params=params,
                    timeout=30
                )

                response.raise_for_status()


                soup = BeautifulSoup(
                    response.text,
                    "html.parser"
                )


                job_links = (
                    self.extract_job_links(
                        soup,
                        company_slug
                    )
                )


                new_job_links = []

                for job_url in job_links:

                    if (
                        job_url
                        in seen_job_urls
                    ):
                        continue

                    seen_job_urls.add(
                        job_url
                    )

                    new_job_links.append(
                        job_url
                    )


                # ------------------------------------
                # NO JOBS
                # ------------------------------------

                if not new_job_links:

                    break


                found_any_jobs = True


                # ------------------------------------
                # LOAD JOB DETAILS
                # ------------------------------------

                for job_url in new_job_links:

                    try:

                        job = (
                            self.fetch_job_details(
                                job_url
                            )
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


                # ------------------------------------
                # DIRECT BOARD DOES NOT PAGINATE
                # ------------------------------------

                if not search_url.endswith(
                    "/search"
                ):
                    break


                # ------------------------------------
                # NEXT SEARCH PAGE
                # ------------------------------------

                page += 1


                if page >= 100:
                    break


            # If the first board format worked,
            # there is no need to try the fallback.
            if found_any_jobs:
                break


        return jobs


    def extract_location(self, soup):
        """
        Jobvite pages can represent locations differently.

        Try JSON-LD first because it is usually the
        cleanest source, then visible page elements,
        then metadata.
        """


        # --------------------------------------------
        # JSON-LD
        # --------------------------------------------

        json_ld_scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )


        for script in json_ld_scripts:

            try:

                data = json.loads(
                    script.string
                    or script.get_text()
                    or "{}"
                )


                if isinstance(
                    data,
                    list
                ):
                    items = data

                elif isinstance(
                    data,
                    dict
                ):

                    graph = data.get(
                        "@graph"
                    )

                    if isinstance(
                        graph,
                        list
                    ):
                        items = graph

                    else:
                        items = [data]

                else:
                    items = []


                for item in items:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue


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


                        locality = (
                            address.get(
                                "addressLocality"
                            )
                            or ""
                        ).strip()

                        region = (
                            address.get(
                                "addressRegion"
                            )
                            or ""
                        ).strip()

                        country = (
                            address.get(
                                "addressCountry"
                            )
                            or ""
                        )


                        if isinstance(
                            country,
                            dict
                        ):
                            country = (
                                country.get(
                                    "name"
                                )
                                or country.get(
                                    "@id"
                                )
                                or ""
                            )


                        country = str(
                            country
                        ).strip()


                        parts = []

                        if locality:
                            parts.append(
                                locality
                            )

                        if region:
                            parts.append(
                                region
                            )

                        if country:
                            parts.append(
                                country
                            )


                        location_text = (
                            ", ".join(
                                parts
                            )
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

                        return " | ".join(
                            location_strings
                        )


            except Exception:
                pass


        # --------------------------------------------
        # COMMON JOBVITE LOCATION ELEMENTS
        # --------------------------------------------

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


        # --------------------------------------------
        # META TAGS
        # --------------------------------------------

        meta_candidates = [
            "jobLocation",
            "location",
            "og:description"
        ]


        for name in meta_candidates:

            element = soup.find(
                "meta",
                attrs={
                    "name": name
                }
            )


            if not element:

                element = soup.find(
                    "meta",
                    attrs={
                        "property": name
                    }
                )


            if element:

                content = (
                    element.get(
                        "content",
                        ""
                    )
                    or ""
                ).strip()


                if content:
                    return content


        return ""


    def extract_title(self, soup):
        """
        Prefer structured JobPosting data,
        then visible headings.
        """

        json_ld_scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )


        for script in json_ld_scripts:

            try:

                data = json.loads(
                    script.string
                    or script.get_text()
                    or "{}"
                )


                if isinstance(
                    data,
                    list
                ):
                    items = data

                elif isinstance(
                    data,
                    dict
                ):

                    graph = data.get(
                        "@graph"
                    )

                    if isinstance(
                        graph,
                        list
                    ):
                        items = graph

                    else:
                        items = [data]

                else:
                    items = []


                for item in items:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue


                    if (
                        item.get(
                            "@type"
                        )
                        == "JobPosting"
                    ):

                        title = (
                            item.get(
                                "title"
                            )
                            or ""
                        ).strip()


                        if title:
                            return title


            except Exception:
                pass


        heading = soup.find(
            "h1"
        )


        if heading:

            title = heading.get_text(
                " ",
                strip=True
            )


            if title:
                return title


        title_tag = soup.find(
            "title"
        )


        if title_tag:

            return title_tag.get_text(
                " ",
                strip=True
            )


        return ""


    def extract_description(self, soup):
        """
        Prefer JobPosting JSON-LD description,
        then visible Jobvite description blocks.
        """


        json_ld_scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )


        for script in json_ld_scripts:

            try:

                data = json.loads(
                    script.string
                    or script.get_text()
                    or "{}"
                )


                if isinstance(
                    data,
                    list
                ):
                    items = data

                elif isinstance(
                    data,
                    dict
                ):

                    graph = data.get(
                        "@graph"
                    )

                    if isinstance(
                        graph,
                        list
                    ):
                        items = graph

                    else:
                        items = [data]

                else:
                    items = []


                for item in items:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue


                    if (
                        item.get(
                            "@type"
                        )
                        == "JobPosting"
                    ):

                        html_description = (
                            item.get(
                                "description"
                            )
                            or ""
                        )


                        if html_description:

                            description_soup = BeautifulSoup(
                                html_description,
                                "html.parser"
                            )


                            return description_soup.get_text(
                                "\n",
                                strip=True
                            )


            except Exception:
                pass


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


        if description:
            return description


        body = soup.find(
            "body"
        )


        if body:

            return body.get_text(
                "\n",
                strip=True
            )


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


        # --------------------------------------------
        # JOB ID
        # --------------------------------------------

        job_id = (
            job_url
            .rstrip("/")
            .split("/")[-1]
        )


        # --------------------------------------------
        # TITLE
        # --------------------------------------------

        title = self.extract_title(
            soup
        )


        # --------------------------------------------
        # LOCATION
        # --------------------------------------------

        location = self.extract_location(
            soup
        )


        # --------------------------------------------
        # DESCRIPTION
        # --------------------------------------------

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
            "source": "jobvite"
        }