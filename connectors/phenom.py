import base64
import json
import re
import time
from urllib.parse import urlparse

import requests

from connectors.base import JobConnector


class PhenomConnector(JobConnector):
    """
    Generic connector for Phenom People / CareerConnect job boards.

    Phenom serves job-search data through POST /widgets.
    Individual tenants differ mainly in page metadata such as pageId,
    pageName, locale, and refNum. The search/pagination logic is shared.
    """

    PAGE_PAUSE = 0.25

    DDO_CANDIDATES = [
        "refineSearch",
        "eagerLoadRefineSearch",
        "eagerLoadRefineSearchSession",
    ]

    DEFAULT_ALL_FIELDS = [
        "category",
        "country",
        "state",
        "city",
        "type",
    ]

    CSRF_RE = re.compile(
        r'csrf[-_]?token["\'\s:=]+([A-Fa-f0-9]{32})',
        re.I,
    )

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )

    BOARD_CONFIGS = {
        "careers.hpe.com": {
            "warmup_path": "/us/en/search-results",
            "page_id": "page15",
            "page_name": "search-results1",
            "page_type": "search",
            "ref_num": "HPE1US",
            "lang": "en_us",
            "locale": "us",
            "page_size": 100,
            "all_fields": [
                "category",
                "country",
                "state",
                "city",
                "type",
                "postalCode",
                "remote",
            ],
            "extra": {},
        },
        "careers.bcg.com": {
            "warmup_path": "/global/en/search-results",
            "page_id": "page17-ds",
            "page_name": "search-results",
            "page_type": "search-results",
            "ref_num": None,
            "lang": "en_global",
            "locale": "global",
            "page_size": 30,
            "all_fields": [
                "country",
                "city",
                "category",
                "company",
                "type",
                "jobType",
            ],
            "extra": {
                "irs": False,
                "locationData": {},
            },
        },
    }

    def __init__(self, company_name, careers_url):
        super().__init__(company_name, careers_url)

        parsed = urlparse(careers_url)
        self.host = parsed.netloc.lower()

        config = self.BOARD_CONFIGS.get(self.host)

        if not config:
            raise ValueError(
                f"No Phenom tenant configuration exists yet for {self.host}"
            )

        self.config = config
        self.site = f"{parsed.scheme or 'https'}://{parsed.netloc}"

    @staticmethod
    def _csrf_from_play_session(cookie_value):
        try:
            payload_b64 = cookie_value.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)

            payload = json.loads(
                base64.urlsafe_b64decode(payload_b64)
            )

            return (
                payload.get("data") or {}
            ).get("csrfToken")

        except Exception:
            return None

    def _open_session(self):
        session = requests.Session()

        session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        })

        warmup_url = (
            self.site.rstrip("/")
            + self.config["warmup_path"]
        )

        response = session.get(
            warmup_url,
            timeout=30,
            allow_redirects=True,
        )

        response.raise_for_status()

        token = None

        play_session = session.cookies.get("PLAY_SESSION")

        if play_session:
            token = self._csrf_from_play_session(
                play_session
            )

        if not token:
            match = self.CSRF_RE.search(response.text)

            if match:
                token = match.group(1)

        return session, token, warmup_url

    def _build_payload(self, ddo_key, offset):
        cfg = self.config

        payload = {
            "lang": cfg["lang"],
            "deviceType": "desktop",
            "country": cfg["locale"],
            "sortBy": "",
            "subsearch": "",
            "keywords": "",
            "jobs": True,
            "counts": True,
            "global": True,
            "all_fields": (
                cfg.get("all_fields")
                or self.DEFAULT_ALL_FIELDS
            ),
            "pageName": cfg["page_name"],
            "pageType": cfg["page_type"],
            "pageId": cfg["page_id"],
            "siteType": "external",
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": False,
            "selected_fields": {},
        }

        payload.update(cfg.get("extra") or {})

        if cfg.get("ref_num"):
            payload["refNum"] = cfg["ref_num"]

        payload["ddoKey"] = ddo_key
        payload["from"] = offset
        payload["size"] = cfg["page_size"]

        return payload

    @classmethod
    def _find_jobs_list(cls, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    key == "jobs"
                    and isinstance(value, list)
                ):
                    return value

                found = cls._find_jobs_list(value)

                if found:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = cls._find_jobs_list(item)

                if found:
                    return found

        return []

    @classmethod
    def _find_total(cls, obj):
        if isinstance(obj, dict):
            for key in (
                "totalHits",
                "total",
                "totalCount",
                "count",
            ):
                value = obj.get(key)

                if isinstance(value, int):
                    return value

            for value in obj.values():
                found = cls._find_total(value)

                if found is not None:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = cls._find_total(item)

                if found is not None:
                    return found

        return None

    @staticmethod
    def _location(job):
        primary = (
            job.get("cityStateCountry")
            or job.get("location")
            or ""
        )

        multi = (
            job.get("multi_location")
            or job.get("multi_location_array")
            or []
        )

        if not primary:
            primary = ", ".join(
                part
                for part in (
                    job.get("city"),
                    job.get("state"),
                    job.get("country"),
                )
                if part
            )

        if len(multi) > 1:
            return (
                f"{primary} "
                f"(+{len(multi) - 1} more locations)"
            )

        return primary

    def _normalize_job(self, job):
        raw_id = (
            job.get("jobId")
            or job.get("reqId")
            or job.get("jobSeqNo")
        )

        if raw_id is None:
            return None

        description = (
            job.get("descriptionTeaser")
            or (
                job.get("ml_job_parser") or {}
            ).get("descriptionTeaser")
            or (
                job.get("ml_job_parser") or {}
            ).get("descriptionTeaser_ats")
            or ""
        )

        return {
            "id": str(raw_id),
            "company": self.company_name,
            "title": job.get("title", ""),
            "location": self._location(job),
            "url": (
                job.get("jobUrl")
                or job.get("applyUrl")
                or ""
            ),
            "description": description,
            "source": "phenom",
        }

    def fetch_jobs(self):
        session, csrf_token, warmup_url = (
            self._open_session()
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.site,
            "Referer": warmup_url,
            "User-Agent": self.USER_AGENT,
        }

        if csrf_token:
            headers["x-csrf-token"] = csrf_token

        widgets_url = (
            self.site.rstrip("/")
            + "/widgets"
        )

        page_size = self.config["page_size"]
        offset = 0
        working_ddo = None
        jobs_by_id = {}

        while True:
            candidates = (
                [working_ddo]
                if working_ddo
                else self.DDO_CANDIDATES
            )

            raw_jobs = []
            total = None

            for ddo_key in candidates:
                response = session.post(
                    widgets_url,
                    headers=headers,
                    json=self._build_payload(
                        ddo_key,
                        offset,
                    ),
                    timeout=30,
                )

                response.raise_for_status()
                data = response.json()

                raw_jobs = self._find_jobs_list(data)
                total = self._find_total(data)

                if raw_jobs:
                    working_ddo = ddo_key
                    break

            if not raw_jobs:
                break

            for raw_job in raw_jobs:
                job = self._normalize_job(raw_job)

                if job:
                    jobs_by_id[job["id"]] = job

            offset += page_size

            if total is not None and offset >= total:
                break

            if len(raw_jobs) < page_size:
                break

            time.sleep(self.PAGE_PAUSE)

        return list(jobs_by_id.values())