import base64
import json
import re
import requests

BOARDS = {
    "eBay": {
        "site": "https://jobs.ebayinc.com",
        "warmup": "/us/en/search-results",
        "ref_num": "EBAEBAUS",
        "lang": "en_us",
        "locale": "us",
        "page_ids": ["page15", "page15-ds"],
        "page_names": ["search-results"],
        "page_types": ["default", "search", "search-results"],
    },
    "Chewy": {
        "site": "https://careers.chewy.com",
        "warmup": "/us/en/search-results",
        "ref_num": "CHINUS",
        "lang": "en_us",
        "locale": "us",
        "page_ids": ["page13", "page13-ds"],
        "page_names": ["search-results"],
        "page_types": ["default", "search", "search-results"],
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


for company, cfg in BOARDS.items():
    print("\n" + "=" * 100)
    print(company)
    print("=" * 100)

    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
    })

    warmup_url = cfg["site"] + cfg["warmup"]
    warmup = session.get(warmup_url, timeout=30)
    warmup.raise_for_status()

    play_session = session.cookies.get("PLAY_SESSION")
    csrf = csrf_from_cookie(play_session) if play_session else None

    if not csrf:
        match = CSRF_RE.search(warmup.text)
        csrf = match.group(1) if match else None

    print("PLAY_SESSION:", "yes" if play_session else "no")
    print("CSRF:", "yes" if csrf else "no")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": cfg["site"],
        "Referer": warmup_url,
        "User-Agent": UA,
    }

    if csrf:
        headers["x-csrf-token"] = csrf

    found_combo = None

    for page_id in cfg["page_ids"]:
        for page_name in cfg["page_names"]:
            for page_type in cfg["page_types"]:
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
                        "all_fields": [
                            "category",
                            "country",
                            "state",
                            "city",
                            "type",
                        ],
                        "pageName": page_name,
                        "pageType": page_type,
                        "pageId": page_id,
                        "siteType": "external",
                        "clearAll": False,
                        "jdsource": "facets",
                        "isSliderEnable": False,
                        "selected_fields": {},
                        "refNum": cfg["ref_num"],
                        "ddoKey": ddo_key,
                        "from": 0,
                        "size": 10,
                    }

                    try:
                        r = session.post(
                            cfg["site"] + "/widgets",
                            headers=headers,
                            json=payload,
                            timeout=30,
                        )

                        if r.status_code != 200:
                            continue

                        data = r.json()
                        jobs = find_jobs(data)

                        print(
                            f"TRY pageId={page_id} "
                            f"pageType={page_type} "
                            f"ddoKey={ddo_key} "
                            f"→ jobs={len(jobs)}"
                        )

                        if jobs:
                            first = jobs[0]
                            print("\n✅ WORKING CONFIG")
                            print("page_id:", page_id)
                            print("page_name:", page_name)
                            print("page_type:", page_type)
                            print("ddo_key:", ddo_key)
                            print("ref_num:", cfg["ref_num"])
                            print("first title:", first.get("title"))
                            print("first id:", first.get("jobId") or first.get("reqId"))
                            found_combo = True
                            break

                    except Exception as exc:
                        print(
                            f"ERROR pageId={page_id} "
                            f"pageType={page_type} "
                            f"ddoKey={ddo_key}: {exc}"
                        )

                if found_combo:
                    break
            if found_combo:
                break
        if found_combo:
            break

    if not found_combo:
        print("\n❌ No working combination found.")