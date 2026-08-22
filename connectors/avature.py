import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

from connectors.base import JobConnector


class AvatureConnector(JobConnector):

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


    def get_base_url(self):
        parsed = urlparse(self.careers_url)

        path_parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if "Home" in path_parts:
            home_index = path_parts.index("Home")
            path_parts = path_parts[:home_index]

        base_path = "/".join(path_parts)

        return (
            f"{parsed.scheme}://"
            f"{parsed.netloc}/"
            f"{base_path}"
        ).rstrip("/")


    def extract_job_id(self, job_url):
        match = re.search(
            r"/(?:JobDetail|FolderDetail)/.*?/(\d+)",
            job_url
        )

        if match:
            return match.group(1)

        return job_url


    def clean_title_from_url(self, job_url):
        """
        Example:

        /JobDetail/Senior-Cloud-Engineer/215349

        becomes:

        Senior Cloud Engineer
        """

        match = re.search(
            r"/(?:JobDetail|FolderDetail)/([^/]+)/\d+",
            job_url
        )

        if not match:
            return ""

        slug = unquote(match.group(1))

        title = slug.replace("-", " ")

        title = re.sub(
            r"\s+",
            " ",
            title
        )

        return title.strip()


    def extract_listing_jobs(self, soup):
        jobs = []
        seen = set()

        for anchor in soup.find_all("a", href=True):

            href = anchor.get("href", "")

            if (
                "/JobDetail/" not in href
                and "/FolderDetail/" not in href
            ):
                continue

            job_url = urljoin(
                self.careers_url,
                href
            )

            job_id = self.extract_job_id(
                job_url
            )

            if job_id in seen:
                continue

            seen.add(job_id)

            # IMPORTANT:
            # Avature listing text can sometimes shorten
            # the real title and hide seniority words.
            #
            # The URL usually contains the canonical title:
            #
            # /JobDetail/Senior-Cloud-Engineer/215349
            #
            # so use that first.
            title = self.clean_title_from_url(
                job_url
            )

            # Fall back to visible anchor text only if
            # the URL did not provide a usable title.
            if not title:
                title = anchor.get_text(
                    " ",
                    strip=True
                )

            location = self.extract_listing_location(
                anchor
            )

            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "location": location,
                "url": job_url,

                # Description stays empty during the
                # fast listing phase.
                #
                # main.py will call enrich_job()
                # only after title/location filtering.
                "description": "",

                "source": "avature"
            })

        return jobs


    def extract_listing_location(self, anchor):
        """
        Search nearby listing containers for a location.

        Avature layouts vary between companies, so we
        walk upward through several parent containers.
        """

        candidates = []

        parent = anchor.parent

        for _ in range(6):

            if parent is None:
                break

            candidates.append(parent)
            parent = parent.parent


        for container in candidates:

            location_element = container.select_one(
                ".field--locations"
            )

            if location_element:

                location = self.clean_location(
                    location_element.get_text(
                        " ",
                        strip=True
                    )
                )

                if location:
                    return location


            for element in container.select(
                "[class*='location'], "
                "[class*='Location']"
            ):

                text = self.clean_location(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if (
                    text
                    and len(text) < 250
                    and text.lower()
                    != self.company_name.lower()
                ):
                    return text

        return ""


    def clean_location(self, location):
        location = location or ""

        location = re.sub(
            r"^Locations?\s*:\s*",
            "",
            location,
            flags=re.IGNORECASE
        )

        location = re.sub(
            r"\s+",
            " ",
            location
        )

        return location.strip()


    def fetch_jobs(self):
        """
        FAST PHASE

        Loads only Avature search-result pages.

        It does NOT open every individual job page.
        """

        base_url = self.get_base_url()

        search_url = (
            f"{base_url}/SearchJobs/"
        )

        jobs = []
        seen_job_ids = set()

        offset = 0

        while True:

            print(
                f"Loading Avature listings "
                f"from offset {offset}..."
            )

            response = self.session.get(
                search_url,
                params={
                    "jobOffset": offset
                },
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            page_jobs = self.extract_listing_jobs(
                soup
            )

            if not page_jobs:
                break

            new_jobs = []

            for job in page_jobs:

                job_id = job["id"]

                if job_id in seen_job_ids:
                    continue

                seen_job_ids.add(job_id)
                new_jobs.append(job)

            if not new_jobs:
                break

            jobs.extend(new_jobs)

            print(
                f"Found {len(jobs)} "
                f"Avature listings so far..."
            )

            offset += len(new_jobs)

            if offset > 5000:
                break

        return jobs


    def enrich_job(self, job):
        """
        SLOW PHASE

        Fetch the full job detail page only after the
        listing has already passed cheaper filters.

        This provides:
        - canonical title
        - full location
        - description
        """

        job_url = job.get("url")

        if not job_url:
            return job

        response = self.session.get(
            job_url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = self.extract_detail_title(
            soup
        )

        location = self.extract_detail_location(
            soup
        )

        description = self.extract_description(
            soup
        )

        if title:
            job["title"] = title

        if location:
            job["location"] = location

        job["description"] = description

        return job


    def extract_detail_title(self, soup):

        # EA's actual visible job title
        title_element = soup.select_one(
            "h2.banner__text__title"
        )

        if title_element:

            title = title_element.get_text(
                " ",
                strip=True
            )

            if title:
                return title


        # OpenGraph fallback
        meta_title = soup.find(
            "meta",
            attrs={
                "property": "og:title"
            }
        )

        if meta_title:

            title = (
                meta_title.get("content")
                or ""
            ).strip()

            if title:
                return title


        # Twitter metadata fallback
        twitter_title = soup.find(
            "meta",
            attrs={
                "name": "twitter:title"
            }
        )

        if twitter_title:

            title = (
                twitter_title.get("content")
                or ""
            ).strip()

            if title:
                return title


        # Final fallback:
        #
        # Core Software Engineer -
        # 215613 - Electronic Arts
        if soup.title:

            page_title = soup.title.get_text(
                " ",
                strip=True
            )

            page_title = re.sub(
                r"\s*-\s*\d+\s*-\s*.*$",
                "",
                page_title
            )

            return page_title.strip()

        return ""


    def extract_detail_location(self, soup):

        # EA's primary Avature location field
        location_element = soup.select_one(
            ".field--locations"
        )

        if location_element:

            location = self.clean_location(
                location_element.get_text(
                    " ",
                    strip=True
                )
            )

            if location:
                return location


        # Generic Avature fallback
        selectors = [
            "[class*='location']",
            "[class*='Location']",
            "[data-field*='location']",
            "[data-field*='Location']"
        ]

        for selector in selectors:

            for element in soup.select(
                selector
            ):

                text = self.clean_location(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if (
                    text
                    and len(text) < 250
                ):
                    return text

        return ""


    def extract_description(self, soup):

        sections = soup.select(
            ".article__content"
        )

        description_parts = []

        for section in sections:

            text = section.get_text(
                "\n",
                strip=True
            )

            if text:
                description_parts.append(
                    text
                )

        if description_parts:

            return "\n\n".join(
                description_parts
            )


        main = soup.find("main")

        if main:

            return main.get_text(
                "\n",
                strip=True
            )


        body = soup.find("body")

        if body:

            return body.get_text(
                "\n",
                strip=True
            )

        return ""