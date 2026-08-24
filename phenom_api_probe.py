import json
import re
import requests
from urllib.parse import urljoin, urlparse


COMPANIES = {
    "HPE": "https://careers.hpe.com/us/en/search-results",
    "eBay": "https://jobs.ebayinc.com/us/en/search-results",
    "Chewy": "https://careers.chewy.com/us/en/search-results",
    "Boston Consulting Group": "https://careers.bcg.com/global/en/search-results",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}


def preview_response(response):
    print("STATUS:", response.status_code)
    print("URL:", response.url)
    print("CONTENT-TYPE:", response.headers.get("content-type"))

    text = response.text.strip()

    if not text:
        print("BODY: <empty>")
        return

    try:
        payload = response.json()

        if isinstance(payload, dict):
            print("JSON KEYS:", list(payload.keys())[:30])

            for key in [
                "jobs",
                "data",
                "results",
                "jobResults",
                "searchResults",
                "total",
                "totalCount",
                "count",
            ]:
                if key in payload:
                    value = payload[key]

                    if isinstance(value, list):
                        print(f"{key}: list[{len(value)}]")
                        if value:
                            print(
                                "FIRST ITEM:",
                                json.dumps(
                                    value[0],
                                    indent=2
                                )[:1000]
                            )
                    else:
                        print(
                            f"{key}:",
                            str(value)[:500]
                        )
        elif isinstance(payload, list):
            print("JSON LIST LENGTH:", len(payload))
            if payload:
                print(
                    "FIRST ITEM:",
                    json.dumps(
                        payload[0],
                        indent=2
                    )[:1000]
                )

    except Exception:
        print(
            "BODY PREVIEW:",
            text[:700].replace("\n", " ")
        )


for name, search_url in COMPANIES.items():

    print("\n" + "=" * 100)
    print(name)
    print("=" * 100)

    try:
        page = requests.get(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
            allow_redirects=True,
        )

        print("SEARCH PAGE:", page.status_code, page.url)

        origin = (
            f"{urlparse(page.url).scheme}://"
            f"{urlparse(page.url).netloc}"
        )

        # First show any API-looking paths embedded directly in HTML.
        api_paths = []

        patterns = [
            r'["\']([^"\']*/api/[^"\']+)["\']',
            r'["\']([^"\']*(?:job|search)[^"\']*(?:api|endpoint)[^"\']*)["\']',
        ]

        for pattern in patterns:
            for match in re.findall(
                pattern,
                page.text,
                flags=re.I,
            ):
                value = str(match)

                if value not in api_paths:
                    api_paths.append(value)

        print("\nEMBEDDED API-LIKE VALUES:")

        if api_paths:
            for value in api_paths[:30]:
                print(value)
        else:
            print("<none>")

        # Probe common Phenom first-party API routes.
        candidates = [
            "/api/jobs",
            "/api/jobs?from=0&size=10",
            "/api/jobs?from=0&s=1",
            "/api/search",
            "/api/jobsearch",
            "/api/jobs/search",
        ]

        print("\nCOMMON ENDPOINT PROBES:")

        for path in candidates:
            url = urljoin(
                origin + "/",
                path.lstrip("/")
            )

            print("\n---", path, "---")

            try:
                r = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=20,
                    allow_redirects=True,
                )

                preview_response(r)

            except Exception as error:
                print("ERROR:", repr(error))

    except Exception as error:
        print("PAGE ERROR:", repr(error))