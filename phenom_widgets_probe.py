import base64
import json
import re
import requests

TESTS = {
    "HPE": {
        "site": "https://careers.hpe.com",
        "warmup": "/us/en/search-results",
        "page_id": "page15",
        "page_name": "search-results1",
        "page_type": "search",
        "ref_num": "HPE1US",
        "lang": "en_us",
        "locale": "us",
        "page_size": 10,
        "all_fields": [
            "category", "country", "state", "city",
            "type", "postalCode", "remote"
        ],
        "extra": {},
    },
    "Boston Consulting Group": {
        "site": "https://careers.bcg.com",
        "warmup": "/global/en/search-results",
        "page_id": "page17-ds",
        "page_name": "search-results",
        "page_type": "search-results",
        "ref_num": None,
        "lang": "en_global",
        "locale": "global",
        "page_size": 10,
        "all_fields": [
            "country", "city", "category",
            "company", "type", "jobType"
        ],
        "extra": {
            "irs": False,
            "locationData": {},
        },
    },
}

DDO_KEYS = [
    "refineSearch",
    "eagerLoadRefineSearch",
    "eagerLoadRefineSearchSession",
]

CSRF_RE = re.compile(
    r'csrf[-_]?token["\'\s:=]+([A-Fa-f0-9]{32})',
    re.I,
)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)


def csrf_from_cookie(cookie):
    try:
        payload = cookie.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        return (data.get("data") or {}).get("csrfToken")
    except Exception:
        return None


def find_jobs(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "jobs" and isinstance(value, list):
                return value
            found = find_jobs(value)
            if found:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = find_jobs(item)
            if found:
                return found

    return []


for company, cfg in TESTS.items():
    print("\n" + "=" * 100)
    print(company)
    print("=" * 100)

    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
    })

    warmup_url = cfg["site"] + cfg["warmup"]

    try:
        warmup = session.get(
            warmup_url,
            timeout=30,
            allow_redirects=True,
        )

        print("WARMUP STATUS:", warmup.status_code)
        print("WARMUP FINAL:", warmup.url)

        play_session = session.cookies.get("PLAY_SESSION")
        csrf = csrf_from_cookie(play_session) if play_session else None

        if not csrf:
            match = CSRF_RE.search(warmup.text)
            csrf = match.group(1) if match else None

        print("PLAY_SESSION:", "yes" if play_session else "no")
        print("CSRF TOKEN:", "yes" if csrf else "no")

    except Exception as exc:
        print("WARMUP ERROR:", repr(exc))
        continue

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": cfg["site"],
        "Referer": warmup_url,
        "User-Agent": UA,
    }

    if csrf:
        headers["x-csrf-token"] = csrf

    for ddo_key in DDO_KEYS:
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
            "all_fields": cfg["all_fields"],
            "pageName": cfg["page_name"],
            "pageType": cfg["page_type"],
            "pageId": cfg["page_id"],
            "siteType": "external",
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": False,
            "selected_fields": {},
            **cfg["extra"],
            "ddoKey": ddo_key,
            "from": 0,
            "size": cfg["page_size"],
        }

        if cfg["ref_num"]:
            payload["refNum"] = cfg["ref_num"]

        print(f"\n--- {ddo_key} ---")

        try:
            response = session.post(
                cfg["site"] + "/widgets",
                headers=headers,
                json=payload,
                timeout=30,
            )

            print("STATUS:", response.status_code)
            print("CONTENT-TYPE:", response.headers.get("content-type"))

            try:
                data = response.json()
            except Exception:
                print("NOT JSON:", response.text[:500].replace("\n", " "))
                continue

            print("TOP KEYS:", list(data.keys())[:20])

            jobs = find_jobs(data)

            print("JOBS FOUND:", len(jobs))

            if jobs:
                first = jobs[0]
                print("FIRST JOB KEYS:", list(first.keys())[:30])
                print(
                    "FIRST JOB:",
                    json.dumps(first, indent=2)[:2500]
                )
                break

        except Exception as exc:
            print("ERROR:", repr(exc))