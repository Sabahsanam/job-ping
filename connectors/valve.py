import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

from connectors.base import JobConnector


class ValveConnector(JobConnector):

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


    def extract_job_id(self, job_url):
        parsed = urlparse(job_url)
        params = parse_qs(parsed.query)

        job_ids = params.get("job_id", [])

        if job_ids:
            return job_ids[0]

        return job_url


    def fetch_jobs(self):
        """
        FAST PHASE

        Valve lists all roles on one careers page.
        We only collect title / URL / location here.
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

        jobs = []
        seen_ids = set()

        for anchor in soup.find_all(
            "a",
            href=True
        ):

            href = anchor.get(
                "href",
                ""
            )

            if "job_id=" not in href:
                continue

            job_url = urljoin(
                self.careers_url,
                href
            )

            job_id = self.extract_job_id(
                job_url
            )

            if job_id in seen_ids:
                continue

            seen_ids.add(job_id)

            title = anchor.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            # Ignore Valve's generic catch-all link.
            if title.lower() == "did we miss something?":
                continue

            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "location": "Bellevue, WA",
                "url": job_url,
                "description": "",
                "source": "valve"
            })

        return jobs


    def enrich_job(self, job):
        """
        Load the individual Valve job page only after
        the cheap title/location filters pass.
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

        description = self.extract_description(
            soup,
            job.get("title", "")
        )

        job["description"] = description

        return job


    def extract_description(
        self,
        soup,
        title
    ):

        # Remove script/style noise first.
        for tag in soup(
            [
                "script",
                "style",
                "noscript"
            ]
        ):
            tag.decompose()

        body = soup.find("body")

        if not body:
            return ""

        text = body.get_text(
            "\n",
            strip=True
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text