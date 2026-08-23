import html
import re
from urllib.parse import urlparse

import requests

from connectors.base import JobConnector


class PaycomConnector(JobConnector):
    API_BASE = "https://portal-applicant-tracking.us-cent.paycomonline.net"

    def get_portal_key(self):
        parsed = urlparse(self.careers_url)
        parts = [part for part in parsed.path.split("/") if part]

        try:
            portal_index = parts.index("portal")
            return parts[portal_index + 1]
        except (ValueError, IndexError):
            raise ValueError(
                f"Could not determine Paycom portal key from {self.careers_url}"
            )

    def get_session(self):
        session = requests.Session()

        session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

        return session

    def get_session_jwt(self, session):
        response = session.get(
            self.careers_url,
            timeout=30
        )

        response.raise_for_status()

        text = html.unescape(response.text)

        match = re.search(
            r'"sessionJWT":"([^"]+)"',
            text
        )

        if not match:
            raise RuntimeError(
                f"Could not find Paycom session JWT for {self.company_name}"
            )

        return match.group(1)

    def build_location(self, job):
        location = (job.get("locations") or "").strip()

     # Paycom often formats locations like:
     # "Progress - Irvine, CA 92618"
     # "Burbank Office - Burbank, CA 91505"
     #
     # Strip the office/site name and ZIP so Job Ping's
     # existing location filter receives:
     # "Irvine, CA"
     # "Burbank, CA"

        if " - " in location:
            location = location.split(" - ", 1)[1].strip()

        location = re.sub(
            r"\s+\d{5}(?:-\d{4})?$",
            "",
            location
        ).strip()

        description = job.get("description") or ""
        description_lower = description.lower()

        if "hybrid work model" in description_lower:
            if location:
                return f"Hybrid / {location}"
            return "Hybrid"

        if "remote work model" in description_lower:
            if location:
                return f"Remote / {location}"
            return "Remote"

        return location

    def build_job_url(self, job_id):
        portal_key = self.get_portal_key()

        return (
            "https://www.paycomonline.net/v4/ats/web.php/"
            f"portal/{portal_key}/career-page/jobs/{job_id}"
        )

    def fetch_jobs(self):
        session = self.get_session()

        token = self.get_session_jwt(session)

        api_url = (
            f"{self.API_BASE}/"
            "api/ats/job-posting-previews/search"
        )

        payload = {
            "skip": 0,
            "take": 500,
            "filtersForQuery": {
                "distanceFrom": None,
                "workEnvironments": [],
                "positionTypes": [],
                "educationLevels": [],
                "categories": [],
                "travelTypes": [],
                "shiftTypes": [],
                "otherFilters": [],
                "keywordSearchText": "",
                "location": "",
                "sortOption": ""
            }
        }

        headers = {
            "Authorization": token,
            "Locale": "en-US",
            "Translation-Highlights": "false",
            "Content-Type": "application/json"
        }

        response = session.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        jobs = []

        for job in data.get("jobPostingPreviews", []):
            job_id = job.get("jobId")
            title = (job.get("jobTitle") or "").strip()

            if not job_id or not title:
                continue

            description = job.get("description") or ""

            jobs.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "location": self.build_location(job),
                "url": self.build_job_url(job_id),
                "description": description,
                "source": "paycom"
            })

        return jobs