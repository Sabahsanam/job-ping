import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from connectors.workday import WorkdayConnector
from connectors.icims import ICIMSConnector


INPUT_FILE = "company_candidates.json"

DISCOVERED_FILE = "secondary_discovered.json"
UNRESOLVED_FILE = "secondary_unresolved.json"

TIMEOUT = 12


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


def load_candidates():
    with open(INPUT_FILE, "r") as file:
        data = json.load(file)

    return data.get("companies", [])


def normalize_text(text):
    if not text:
        return ""

    return (
        text
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u003A", ":")
    )


def extract_urls(page_url, text):
    urls = set()

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    for tag in soup.find_all(
        ["a", "script", "iframe", "form"]
    ):
        value = (
            tag.get("href")
            or tag.get("src")
            or tag.get("action")
        )

        if not value:
            continue

        try:
            urls.add(
                urljoin(
                    page_url,
                    value
                )
            )
        except Exception:
            pass

    raw_text = normalize_text(text)

    raw_urls = re.findall(
        r'https?://[^\s"\'<>\\]+',
        raw_text,
        re.IGNORECASE
    )

    for url in raw_urls:
        urls.add(
            url.rstrip(
                ".,);]}"
            )
        )

    return urls


def canonicalize_workday_url(url):
    parsed = urlparse(url)

    host = parsed.netloc.lower()

    if "myworkdayjobs.com" not in host:
        return None

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    locale = None
    site = None

    if parts:
        if re.fullmatch(
            r"[a-z]{2}-[A-Z]{2}",
            parts[0]
        ):
            locale = parts[0]

            if len(parts) > 1:
                site = parts[1]

        else:
            site = parts[0]

    if not site:
        return None

    base = (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
    )

    if locale:
        return (
            f"{base}/"
            f"{locale}/"
            f"{site}"
        )

    return (
        f"{base}/"
        f"{site}"
    )


def canonicalize_icims_url(url):
    parsed = urlparse(url)

    host = parsed.netloc.lower()

    if "icims.com" not in host:
        return None

    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
    )


def find_workday_urls(
    final_url,
    urls
):
    candidates = []

    all_urls = set(urls)

    if final_url:
        all_urls.add(
            final_url
        )

    for url in all_urls:

        canonical = (
            canonicalize_workday_url(
                url
            )
        )

        if (
            canonical
            and canonical not in candidates
        ):
            candidates.append(
                canonical
            )

    return candidates


def find_icims_urls(
    final_url,
    urls
):
    candidates = []

    all_urls = set(urls)

    if final_url:
        all_urls.add(
            final_url
        )

    for url in all_urls:

        canonical = (
            canonicalize_icims_url(
                url
            )
        )

        if (
            canonical
            and canonical not in candidates
        ):
            candidates.append(
                canonical
            )

    return candidates


def verify_workday(
    company,
    urls
):
    for careers_url in urls:

        print(
            "   Testing Workday:",
            careers_url
        )

        try:
            connector = WorkdayConnector(
                company["name"],
                careers_url
            )

            jobs = connector.fetch_jobs()

        except Exception as error:

            print(
                "   ❌ Workday failed:",
                str(error)[:150]
            )

            continue

        if jobs:

            print(
                "   ✅ Workday verified:",
                len(jobs),
                "jobs"
            )

            return {
                "name": company["name"],
                "careers_url": careers_url,
                "categories": company.get(
                    "categories",
                    []
                ),
                "ats": "Workday",
                "job_count": len(jobs),
                "status": "verified"
            }

    return None


def verify_icims(
    company,
    urls
):
    for careers_url in urls:

        print(
            "   Testing iCIMS:",
            careers_url
        )

        try:
            connector = ICIMSConnector(
                company["name"],
                careers_url
            )

            jobs = connector.fetch_jobs()

        except Exception as error:

            print(
                "   ❌ iCIMS failed:",
                str(error)[:150]
            )

            continue

        if jobs:

            print(
                "   ✅ iCIMS verified:",
                len(jobs),
                "jobs"
            )

            return {
                "name": company["name"],
                "careers_url": careers_url,
                "categories": company.get(
                    "categories",
                    []
                ),
                "ats": "iCIMS",
                "job_count": len(jobs),
                "status": "verified"
            }

    return None


def inspect_company(
    company,
    session
):
    name = company["name"]
    start_url = company["careers_url"]

    print()
    print("=" * 72)
    print(
        "SECONDARY DISCOVERY:",
        name
    )

    try:

        response = session.get(
            start_url,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        print(
            "STATUS:",
            response.status_code
        )

        print(
            "FINAL URL:",
            response.url
        )

        final_url = response.url

        text = response.text

    except Exception as error:

        print(
            "⚠️ PAGE REQUEST FAILED:",
            error
        )

        final_url = start_url
        text = ""


    urls = extract_urls(
        final_url,
        text
    )


    # -----------------------------------------
    # WORKDAY
    # -----------------------------------------

    workday_urls = find_workday_urls(
        final_url,
        urls
    )

    if workday_urls:

        print(
            "🟢 WORKDAY CANDIDATES:",
            len(workday_urls)
        )

        result = verify_workday(
            company,
            workday_urls
        )

        if result:
            return result


    # -----------------------------------------
    # iCIMS
    # -----------------------------------------

    icims_urls = find_icims_urls(
        final_url,
        urls
    )

    if icims_urls:

        print(
            "🟢 iCIMS CANDIDATES:",
            len(icims_urls)
        )

        result = verify_icims(
            company,
            icims_urls
        )

        if result:
            return result


    print(
        "⚠️ Still unresolved"
    )

    return {
        "name": name,
        "careers_url": final_url,
        "categories": company.get(
            "categories",
            []
        ),
        "status": "unresolved"
    }


def save_file(
    filename,
    companies
):
    with open(
        filename,
        "w"
    ) as file:

        json.dump(
            {
                "companies": companies
            },
            file,
            indent=2
        )

        file.write("\n")


def main():

    print()
    print(
        "💌 JOB PING SECONDARY DISCOVERY"
    )

    print(
        "Workday + iCIMS only"
    )

    candidates = load_candidates()

    print()
    print(
        "INPUT:",
        len(candidates)
    )

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    discovered = []
    unresolved = []

    for company in candidates:

        result = inspect_company(
            company,
            session
        )

        if (
            result["status"]
            == "verified"
        ):
            discovered.append(
                result
            )

        else:
            unresolved.append(
                result
            )


    save_file(
        DISCOVERED_FILE,
        discovered
    )

    save_file(
        UNRESOLVED_FILE,
        unresolved
    )


    print()
    print()
    print("=" * 72)
    print(
        "💌 SECONDARY DISCOVERY SUMMARY"
    )
    print("=" * 72)

    print(
        "INPUT:",
        len(candidates)
    )

    print(
        "VERIFIED:",
        len(discovered)
    )

    print(
        "STILL UNRESOLVED:",
        len(unresolved)
    )

    print()

    if discovered:

        print(
            "✅ VERIFIED"
        )

        for company in discovered:

            print(
                f"- {company['name']} "
                f"→ {company['ats']} "
                f"({company['job_count']} jobs)"
            )


    if unresolved:

        print()
        print(
            "⚠️ STILL UNRESOLVED"
        )

        for company in unresolved:

            print(
                "-",
                company["name"]
            )


    print()

    print(
        "Saved →",
        DISCOVERED_FILE
    )

    print(
        "Saved →",
        UNRESOLVED_FILE
    )


if __name__ == "__main__":
    main()