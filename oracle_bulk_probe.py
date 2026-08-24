import re
import requests
from bs4 import BeautifulSoup


API_VERSION = "11.13.18.05"

COMPANIES = {
    "Oracle": {
        "careers_url": "https://careers.oracle.com/jobs/",
        "api_base": "https://eeho.fa.us2.oraclecloud.com:443",
        "site_number": "CX_45001",
    },
    "Texas Instruments": {
        "careers_url": "https://careers.ti.com/",
        "api_base": "https://edbz.fa.us2.oraclecloud.com:443",
        "site_number": "CX",
    },
    "JPMorgan Chase": {
        "careers_url": "https://careers.jpmorgan.com/",
        "api_base": "https://jpmc.fa.oraclecloud.com",
        "site_number": "CX_1001",
    },
    "American Express": {
        "careers_url": "https://www.americanexpress.com/en-us/careers/",
        "api_base": "https://egug.fa.us2.oraclecloud.com",
        "site_number": None,
    },
}


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}


def discover_site_number(url):
    r = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
        timeout=30,
        allow_redirects=True,
    )

    text = r.text

    patterns = [
        r'data-sitenumber=["\']([^"\']+)',
        r'/sites/([^/"\'?&<>\s]+)',
        r'siteNumber[=:]["\']?([A-Za-z0-9_]+)',
        r'"siteNumber"\s*:\s*"([^"]+)"',
        r'CX_\d+',
    ]

    found = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.I,
        )

        for match in matches:
            if isinstance(match, tuple):
                match = match[0]

            value = str(match).strip()

            if (
                value
                and value not in found
                and len(value) < 100
            ):
                found.append(value)

    return r.url, found


def probe_jobs(
    api_base,
    site_number,
):
    endpoint = (
        api_base.rstrip("/")
        + f"/hcmRestApi/resources/{API_VERSION}"
        + "/recruitingCEJobRequisitions"
    )

    params = {
        "finder": (
            "findReqs;"
            f"siteNumber={site_number},"
            "limit=20,"
            "offset=0"
        ),
        "expand": "requisitionList",
        "onlyData": "true",
    }

    r = requests.get(
        endpoint,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    print("API STATUS:", r.status_code)
    print("API URL:", r.url)

    print(
        "BODY PREVIEW:",
        r.text[:500].replace(
            "\n",
            " "
        )
    )

    if r.status_code != 200:
        return

    try:
        payload = r.json()
    except Exception:
        print("JSON: could not parse")
        return

    print(
        "TOP KEYS:",
        list(payload.keys())
    )

    items = payload.get(
        "items",
        []
    )

    print(
        "ITEM COUNT:",
        len(items)
    )

    if not items:
        return

    first = items[0]

    print(
        "FIRST ITEM KEYS:",
        list(first.keys())[:30]
    )

    requisitions = first.get(
        "requisitionList",
        []
    )

    print(
        "REQUISITIONS ON PAGE:",
        len(requisitions)
    )

    for job in requisitions[:3]:
        print(
            "  ",
            {
                "Id": job.get("Id"),
                "Title": job.get("Title"),
                "PrimaryLocation": job.get("PrimaryLocation"),
                "PostedDate": job.get("PostedDate"),
            }
        )


for name, config in COMPANIES.items():

    print(
        "\n"
        + "=" * 90
    )

    print(name)

    print(
        "=" * 90
    )

    site_number = config[
        "site_number"
    ]

    if not site_number:

        final_url, candidates = (
            discover_site_number(
                config["careers_url"]
            )
        )

        print(
            "CAREERS FINAL URL:",
            final_url
        )

        print(
            "SITE NUMBER CANDIDATES:",
            candidates[:20]
        )

        if candidates:

            preferred = None

            for value in candidates:
                if value.upper().startswith(
                    "CX"
                ):
                    preferred = value
                    break

            site_number = (
                preferred
                or candidates[0]
            )

    print(
        "API BASE:",
        config["api_base"]
    )

    print(
        "SITE NUMBER:",
        site_number
    )

    if not site_number:

        print(
            "SKIP: no site number discovered"
        )

        continue

    try:
        probe_jobs(
            config["api_base"],
            site_number,
        )

    except Exception as error:
        print(
            "ERROR:",
            repr(error)
        )
