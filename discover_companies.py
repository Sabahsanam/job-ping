import html
import json
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from company_loader import load_companies


TIMEOUT = 25

CANDIDATES_FILE = "company_candidates.json"
DISCOVERED_FILE = "discovered_companies.json"
UNRESOLVED_FILE = "unresolved_companies.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


SUPPORTED_ATS = {
    "greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "ashbyhq.com": "Ashby",
    "smartrecruiters.com": "SmartRecruiters",
    "icims.com": "iCIMS",
    "myworkdayjobs.com": "Workday",
    "recruitee.com": "Recruitee",
    "jobvite.com": "Jobvite",
    "workable.com": "Workable",
    "paycomonline.net": "Paycom",
}


ATS_SIGNATURES = {
    "Greenhouse": [
        "greenhouse.io",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "boards-api.greenhouse.io",
        "gh_jid",
    ],
    "Lever": [
        "jobs.lever.co",
        "api.lever.co",
    ],
    "Ashby": [
        "jobs.ashbyhq.com",
        "api.ashbyhq.com",
    ],
    "SmartRecruiters": [
        "jobs.smartrecruiters.com",
        "api.smartrecruiters.com",
    ],
    "iCIMS": [
        "icims.com",
        "careers.icims.com",
        "jobs.icims.com",
    ],
    "Workday": [
        "myworkdayjobs.com",
        "/wday/cxs/",
    ],
    "Recruitee": [
        "recruitee.com",
    ],
    "Jobvite": [
        "jobs.jobvite.com",
    ],
    "Workable": [
        "apply.workable.com",
        "workable.com/api/accounts/",
    ],
    "Paycom": [
        "paycomonline.net",
        "portal-applicant-tracking.us-cent.paycomonline.net",
    ],
}


def load_candidates():
    if not os.path.exists(CANDIDATES_FILE):
        raise FileNotFoundError(
            f"Missing {CANDIDATES_FILE}"
        )

    with open(CANDIDATES_FILE, "r") as file:
        data = json.load(file)

    return data.get("companies", [])


def get_existing_company_names():
    existing_companies = load_companies()

    return {
        company["name"].strip().lower()
        for company in existing_companies
    }


def normalize_url(url):
    if not url:
        return ""

    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().replace("www.", "")

    path = parsed.path.rstrip("/")

    return f"{scheme}://{netloc}{path}"


def normalize_html(text):
    if not text:
        return ""

    text = html.unescape(text)

    replacements = {
        "\\/": "/",
        "\\u002F": "/",
        "\\u003A": ":",
        "\\u0026": "&",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def detect_ats_from_url(url):
    if not url:
        return None

    value = url.lower()

    for domain, ats_name in SUPPORTED_ATS.items():
        if domain in value:
            return ats_name

    return None


def detect_signatures(text):
    text_lower = (text or "").lower()

    found = []

    for ats_name, signatures in ATS_SIGNATURES.items():
        matched = []

        for signature in signatures:
            if signature.lower() in text_lower:
                matched.append(signature)

        if matched:
            found.append({
                "ats": ats_name,
                "signatures": matched
            })

    return found


def extract_html_links(page_url, text):
    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    links = set()

    for tag in soup.find_all(
        ["a", "script", "iframe", "form"]
    ):
        candidate = (
            tag.get("href")
            or tag.get("src")
            or tag.get("action")
        )

        if not candidate:
            continue

        try:
            links.add(
                urljoin(
                    page_url,
                    candidate
                )
            )
        except Exception:
            continue

    return links


def extract_raw_urls(text):
    text = normalize_html(text)

    pattern = (
        r'https?://'
        r'[^\s"\'<>\\]+'
    )

    matches = re.findall(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    urls = set()

    for match in matches:
        cleaned = (
            match
            .rstrip("),];}")
            .strip()
        )

        if cleaned:
            urls.add(cleaned)

    return urls


def find_supported_urls(urls):
    results = []
    seen = set()

    for url in urls:
        ats = detect_ats_from_url(url)

        if not ats:
            continue

        key = (
            ats,
            normalize_url(url)
        )

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "ats": ats,
            "url": url
        })

    return results


def extract_greenhouse_token(url):
    if not url:
        return None

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    valid_hosts = (
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "boards-api.greenhouse.io",
    )

    if not any(
        host.endswith(value)
        for value in valid_hosts
    ):
        return None

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if not parts:
        return None

    if host.endswith("boards-api.greenhouse.io"):
        if (
            len(parts) >= 3
            and parts[0] == "v1"
            and parts[1] == "boards"
        ):
            return parts[2]

    return parts[0]


def extract_lever_token(url):
    if not url:
        return None

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    if not (
        host.endswith("jobs.lever.co")
        or host.endswith("api.lever.co")
    ):
        return None

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if not parts:
        return None

    if host.endswith("api.lever.co"):
        if (
            len(parts) >= 3
            and parts[0] == "v0"
            and parts[1] == "postings"
        ):
            return parts[2]

    return parts[0]


def extract_ashby_token(url):
    if not url:
        return None

    parsed = urlparse(url)

    host = parsed.netloc.lower()

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if host.endswith("jobs.ashbyhq.com"):
        if parts:
            return parts[0]

    if host.endswith("api.ashbyhq.com"):
        if (
            len(parts) >= 3
            and parts[0] == "posting-api"
            and parts[1] == "job-board"
        ):
            return parts[2]

    return None


def verify_greenhouse_token(token, session):
    api_url = (
        "https://boards-api.greenhouse.io/"
        f"v1/boards/{token}/jobs"
    )

    try:
        response = session.get(
            api_url,
            timeout=TIMEOUT
        )
    except Exception:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except Exception:
        return None

    jobs = data.get("jobs", [])

    if (
        not isinstance(jobs, list)
        or not jobs
    ):
        return None

    return {
        "ats": "Greenhouse",
        "careers_url": (
            "https://boards.greenhouse.io/"
            f"{token}"
        ),
        "token": token,
        "job_count": len(jobs),
    }


def verify_lever_token(token, session):
    api_url = (
        "https://api.lever.co/"
        f"v0/postings/{token}"
    )

    try:
        response = session.get(
            api_url,
            params={"mode": "json"},
            timeout=TIMEOUT
        )
    except Exception:
        return None

    if response.status_code != 200:
        return None

    try:
        jobs = response.json()
    except Exception:
        return None

    if (
        not isinstance(jobs, list)
        or not jobs
    ):
        return None

    return {
        "ats": "Lever",
        "careers_url": (
            "https://jobs.lever.co/"
            f"{token}"
        ),
        "token": token,
        "job_count": len(jobs),
    }


def verify_ashby_token(token, session):
    api_url = (
        "https://api.ashbyhq.com/"
        "posting-api/job-board/"
        f"{token}"
    )

    try:
        response = session.get(
            api_url,
            timeout=TIMEOUT
        )
    except Exception:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except Exception:
        return None

    jobs = data.get("jobs", [])

    if (
        not isinstance(jobs, list)
        or not jobs
    ):
        return None

    return {
        "ats": "Ashby",
        "careers_url": (
            "https://jobs.ashbyhq.com/"
            f"{token}"
        ),
        "token": token,
        "job_count": len(jobs),
    }


def verify_discovered_ats_urls(
    supported_urls,
    session
):
    for result in supported_urls:
        ats = result["ats"]
        url = result["url"]

        if ats == "Greenhouse":
            token = extract_greenhouse_token(url)

            if token:
                verified = verify_greenhouse_token(
                    token,
                    session
                )

                if verified:
                    return verified

        elif ats == "Lever":
            token = extract_lever_token(url)

            if token:
                verified = verify_lever_token(
                    token,
                    session
                )

                if verified:
                    return verified

        elif ats == "Ashby":
            token = extract_ashby_token(url)

            if token:
                verified = verify_ashby_token(
                    token,
                    session
                )

                if verified:
                    return verified

    return None


def generate_slug_candidates(company):
    name = (
        company["name"]
        .lower()
        .strip()
    )

    parsed = urlparse(
        company["careers_url"]
    )

    domain = (
        parsed.netloc
        .lower()
        .replace("www.", "")
    )

    domain_parts = domain.split(".")

    domain_root = (
        domain_parts[0]
        if domain_parts
        else ""
    )

    cleaned_name = re.sub(
        r"[^a-z0-9]+",
        "",
        name
    )

    hyphen_name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name
    ).strip("-")

    candidates = [
        cleaned_name,
        hyphen_name,
        domain_root,
    ]

    common_words = [
        "inc",
        "corporation",
        "corp",
        "company",
        "technologies",
        "technology",
        "holdings",
        "group",
    ]

    simplified = cleaned_name

    for word in common_words:
        simplified = simplified.replace(
            word,
            ""
        )

    candidates.append(simplified)

    unique = []

    for candidate in candidates:
        candidate = (
            candidate or ""
        ).strip()

        if (
            candidate
            and candidate not in unique
        ):
            unique.append(candidate)

    return unique


def probe_greenhouse(company, session):
    for token in generate_slug_candidates(company):
        result = verify_greenhouse_token(
            token,
            session
        )

        if result:
            return result

    return None


def probe_lever(company, session):
    for token in generate_slug_candidates(company):
        result = verify_lever_token(
            token,
            session
        )

        if result:
            return result

    return None


def probe_ashby(company, session):
    for token in generate_slug_candidates(company):
        result = verify_ashby_token(
            token,
            session
        )

        if result:
            return result

    return None


def probe_known_ats(company, session):
    probes = [
        probe_greenhouse,
        probe_lever,
        probe_ashby,
    ]

    for probe in probes:
        result = probe(
            company,
            session
        )

        if result:
            return result

    return None


def inspect_company(company):
    name = company["name"]
    careers_url = company["careers_url"]

    print()
    print("=" * 72)
    print("COMPANY:", name)
    print("START URL:", careers_url)

    session = requests.Session()
    session.headers.update(HEADERS)

    response = None
    supported_urls = []

    try:
        response = session.get(
            careers_url,
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

    except Exception as error:
        print(
            "⚠️ CAREERS PAGE REQUEST FAILED:",
            error
        )

    if (
        response is not None
        and response.status_code < 400
    ):
        final_ats = detect_ats_from_url(
            response.url
        )

        if final_ats:
            print(
                "🟢 ATS FOUND FROM REDIRECT:",
                final_ats
            )

            supported_urls.append({
                "ats": final_ats,
                "url": response.url
            })

        normalized_text = normalize_html(
            response.text
        )

        html_links = extract_html_links(
            response.url,
            normalized_text
        )

        raw_urls = extract_raw_urls(
            normalized_text
        )

        page_supported_urls = find_supported_urls(
            html_links | raw_urls
        )

        supported_urls.extend(
            page_supported_urls
        )

        if page_supported_urls:
            print(
                "🟢 ATS CLUE FROM PAGE:",
                page_supported_urls[0]["ats"]
            )

        signatures = detect_signatures(
            normalized_text
        )

        if signatures:
            print(
                "🟡 ATS SIGNATURES:",
                ", ".join(
                    result["ats"]
                    for result in signatures
                )
            )

    elif response is not None:
        if response.status_code in [
            401,
            403,
            429
        ]:
            print(
                "🚧 CAREERS SITE BLOCKED"
            )
        else:
            print(
                "⚠️ CAREERS PAGE HTTP ERROR"
            )

    if supported_urls:
        print(
            "🔗 Verifying ATS found on careers page..."
        )

        verified_from_page = (
            verify_discovered_ats_urls(
                supported_urls,
                session
            )
        )

        if verified_from_page:
            print(
                "✅ VERIFIED FROM PAGE:",
                verified_from_page["ats"]
            )

            print(
                "TOKEN:",
                verified_from_page["token"]
            )

            print(
                "JOBS:",
                verified_from_page["job_count"]
            )

            return {
                "name": name,
                "careers_url": (
                    verified_from_page[
                        "careers_url"
                    ]
                ),
                "categories": company.get(
                    "categories",
                    []
                ),
                "ats": verified_from_page["ats"],
                "ats_token": (
                    verified_from_page["token"]
                ),
                "job_count": (
                    verified_from_page[
                        "job_count"
                    ]
                ),
                "status": "verified"
            }

    print(
        "🔎 Verifying ATS APIs..."
    )

    verified = probe_known_ats(
        company,
        session
    )

    if verified:
        print(
            "✅ VERIFIED:",
            verified["ats"]
        )

        print(
            "TOKEN:",
            verified["token"]
        )

        print(
            "JOBS:",
            verified["job_count"]
        )

        return {
            "name": name,
            "careers_url": verified[
                "careers_url"
            ],
            "categories": company.get(
                "categories",
                []
            ),
            "ats": verified["ats"],
            "ats_token": verified["token"],
            "job_count": verified[
                "job_count"
            ],
            "status": "verified"
        }

    print(
        "⚠️ COULD NOT VERIFY ATS"
    )

    return {
        "name": name,
        "careers_url": (
            response.url
            if response is not None
            else careers_url
        ),
        "categories": company.get(
            "categories",
            []
        ),
        "status": "unresolved"
    }


def save_results(
    discovered,
    unresolved
):
    with open(
        DISCOVERED_FILE,
        "w"
    ) as file:
        json.dump(
            {
                "companies": discovered
            },
            file,
            indent=2
        )

        file.write("\n")

    with open(
        UNRESOLVED_FILE,
        "w"
    ) as file:
        json.dump(
            {
                "companies": unresolved
            },
            file,
            indent=2
        )

        file.write("\n")


def main():
    print()
    print(
        "💌 JOB PING BULK COMPANY DISCOVERY"
    )
    print()

    candidates = load_candidates()

    existing_names = (
        get_existing_company_names()
    )

    print(
        f"Loaded {len(candidates)} candidate companies."
    )

    discovered = []
    unresolved = []

    skipped_existing = 0
    skipped_duplicates = 0

    seen_candidate_urls = set()

    for company in candidates:
        name = (
            company.get(
                "name",
                ""
            )
            .strip()
        )

        careers_url = (
            company.get(
                "careers_url",
                ""
            )
            .strip()
        )

        if not name:
            print(
                "⚠️ Skipping candidate with no name."
            )
            continue

        if not careers_url:
            print(
                f"⚠️ Skipping {name}: "
                "missing careers URL."
            )
            continue

        if name.lower() in existing_names:
            skipped_existing += 1

            print()
            print(
                f"⏭️ {name} already exists "
                "in Job Ping."
            )

            continue

        normalized_candidate_url = normalize_url(
            careers_url
        )

        if (
            normalized_candidate_url
            in seen_candidate_urls
        ):
            skipped_duplicates += 1

            print()
            print(
                f"♻️ {name} skipped: "
                "duplicate careers URL in candidate batch."
            )

            continue

        seen_candidate_urls.add(
            normalized_candidate_url
        )

        result = inspect_company(
            company
        )

        if result["status"] == "verified":
            discovered.append(result)
        else:
            unresolved.append(result)

    save_results(
        discovered,
        unresolved
    )

    print()
    print()
    print("=" * 72)
    print(
        "💌 JOB PING BULK DISCOVERY SUMMARY"
    )
    print("=" * 72)

    print(
        "INPUT CANDIDATES:",
        len(candidates)
    )

    print(
        "ALREADY IN JOB PING:",
        skipped_existing
    )

    print(
        "DUPLICATE CANDIDATES:",
        skipped_duplicates
    )

    print(
        "NEWLY VERIFIED:",
        len(discovered)
    )

    print(
        "UNRESOLVED:",
        len(unresolved)
    )

    attempted = (
        len(discovered)
        +
        len(unresolved)
    )

    if attempted:
        rate = (
            len(discovered)
            /
            attempted
        ) * 100

        print(
            "VERIFICATION RATE:",
            f"{rate:.1f}%"
        )

    print()

    if discovered:
        print(
            "✅ NEW VERIFIED COMPANIES"
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
            "⚠️ NEEDS DEEPER DISCOVERY"
        )

        for company in unresolved:
            print(
                "-",
                company["name"]
            )

    print()

    print(
        f"Saved → {DISCOVERED_FILE}"
    )

    print(
        f"Saved → {UNRESOLVED_FILE}"
    )


if __name__ == "__main__":
    main()