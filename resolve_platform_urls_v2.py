import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


INPUT_FILE = "platform_discovery_150.json"
OUTPUT_FILE = "platform_resolved_150_v2.json"

TIMEOUT = 15
REQUEST_DELAY = 0.15


SUPPORTED_GENERIC_PLATFORMS = {
    "Workday",
    "Greenhouse",
    "Lever",
    "Ashby",
    "SmartRecruiters",
    "iCIMS",
    "Workable",
    "Eightfold",
    "SAP SuccessFactors",
}

PLATFORM_PATTERNS = {
    "Workday": [
        r"https?://[^\"'\s<>]+\.myworkdayjobs\.com/[^\"'\s<>]+",
    ],
    "Greenhouse": [
        r"https?://(?:boards|job-boards|jobs)\.greenhouse\.io/[^\"'\s<>]+",
        r"https?://greenhouse\.io/[^\"'\s<>]+",
    ],
    "Lever": [
        r"https?://jobs\.lever\.co/[^\"'\s<>]+",
    ],
    "Ashby": [
        r"https?://jobs\.ashbyhq\.com/[^\"'\s<>]+",
    ],
    "SmartRecruiters": [
        r"https?://jobs\.smartrecruiters\.com/[^\"'\s<>]+",
    ],
    "iCIMS": [
        r"https?://[^\"'\s<>]*\.icims\.com/jobs/[^\"'\s<>]*",
        r"https?://[^\"'\s<>]*\.icims\.com/[^\"'\s<>]*",
    ],
    "Workable": [
        r"https?://apply\.workable\.com/[^\"'\s<>]+",
    ],
    "Eightfold": [
        r"https?://[^\"'\s<>]+\.eightfold\.ai/careers(?:/[^\"'\s<>]*)?",
    ],
}


def load_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def clean_url(url):
    if not url:
        return None

    url = url.strip().rstrip("\"'<>),;")

    # Ignore obvious static assets.
    lowered = url.lower()

    static_suffixes = (
        ".css",
        ".js",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
        ".ico",
    )

    if lowered.endswith(static_suffixes):
        return None

    return url


def bad_candidate_url(url, platform):
    if not url:
        return True

    lowered = url.lower()

    # Login / account / event pages are not job-board roots.
    bad_fragments = [
        "/login",
        "loginonly=1",
        "/events/candidate",
        "/event/candidate",
        "plannedeventid=",
        "/connect",
        "/jobalerts",
        "/userhome",
    ]

    if any(fragment in lowered for fragment in bad_fragments):
        return True

    if platform == "Workday":
        return "myworkdayjobs.com" not in lowered

    if platform == "Greenhouse":
        return "greenhouse.io" not in lowered

    if platform == "Lever":
        return "jobs.lever.co" not in lowered

    if platform == "Ashby":
        return "jobs.ashbyhq.com" not in lowered

    if platform == "SmartRecruiters":
        return "jobs.smartrecruiters.com" not in lowered

    if platform == "iCIMS":
        return "icims.com" not in lowered

    if platform == "Workable":
        return "apply.workable.com" not in lowered

    if platform == "Eightfold":
        return (
            "eightfold.ai" not in lowered
            or "/careers" not in lowered
        )

    return False


def normalize_platform_url(url, platform):
    if not url:
        return None

    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc
    path = parsed.path

    if platform == "Workday":
        # Strip login/userHome/job-specific suffixes.
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        # Keep tenant career-site root. Usually first path segment,
        # but locale prefixes such as en-US may appear before it.
        locale_pattern = re.compile(r"^[a-z]{2}-[A-Z]{2}$")

        if locale_pattern.match(pieces[0]) and len(pieces) >= 2:
            pieces = pieces[1:]

        root = pieces[0]

        return f"{scheme}://{host}/{root}"

    if platform == "Greenhouse":
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        return f"{scheme}://{host}/{pieces[0]}"

    if platform == "Lever":
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        return f"{scheme}://{host}/{pieces[0]}"

    if platform == "Ashby":
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        return f"{scheme}://{host}/{pieces[0]}"

    if platform == "SmartRecruiters":
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        return f"{scheme}://{host}/{pieces[0]}"

    if platform == "Workable":
        pieces = [p for p in path.split("/") if p]

        if not pieces:
            return None

        return f"{scheme}://{host}/{pieces[0]}/"

    if platform == "Eightfold":
        # Eightfold generic connector expects first-party /careers root.
        match = re.search(
            r"^(https?://[^/]+/careers)",
            url,
            flags=re.I,
        )

        if match:
            return match.group(1)

        return None

    if platform == "iCIMS":
        # iCIMS varies heavily by tenant. Keep the URL for a later
        # connector test, but reject obvious login/connect endpoints.
        return url.split("?")[0]

    return url


def extract_urls(response):
    urls = []

    # Final redirect destination.
    urls.append(response.url)

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for tag in soup.find_all(
        ["a", "script", "iframe", "form", "link"]
    ):
        raw = (
            tag.get("href")
            or tag.get("src")
            or tag.get("action")
        )

        if not raw:
            continue

        urls.append(
            urljoin(
                response.url,
                raw,
            )
        )

    # Also scan raw HTML because many ATS URLs are embedded in JS/config.
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            for match in re.findall(
                pattern,
                response.text,
                flags=re.I,
            ):
                urls.append(match)

    # Deduplicate while preserving order.
    seen = set()
    output = []

    for url in urls:
        url = clean_url(url)

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)
        output.append(url)

    return output


def find_platform_url(
    company,
    response,
):
    platform = company["platform"]
    careers_url = company["careers_url"]

    candidates = []

    # Configured URL is strongest when already on ATS domain.
    candidates.append(
        (
            0,
            careers_url,
            "configured_url",
        )
    )

    for url in extract_urls(response):
        priority = 10

        if "/jobs" in url.lower():
            priority -= 2

        if "/careers" in url.lower():
            priority -= 1

        candidates.append(
            (
                priority,
                url,
                "page_evidence",
            )
        )

    valid = []

    for priority, url, source in candidates:
        if bad_candidate_url(
            url,
            platform,
        ):
            continue

        normalized = normalize_platform_url(
            url,
            platform,
        )

        if not normalized:
            continue

        if bad_candidate_url(
            normalized,
            platform,
        ):
            continue

        valid.append(
            (
                priority,
                len(normalized),
                normalized,
                source,
            )
        )

    if not valid:
        # SuccessFactors often runs entirely on the company's
        # first-party domain. Use first-party URL when platform
        # detection already proved RMK/SuccessFactors.
        if platform == "SAP SuccessFactors":
            return (
                response.url.rstrip("/") + "/",
                "first_party_successfactors",
            )

        return (
            None,
            None,
        )

    valid.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    _, _, url, source = valid[0]

    return (
        url,
        source,
    )


data = load_json(INPUT_FILE)

companies = [
    company
    for company in data.get("companies", [])
    if company.get("platform")
    not in {
        None,
        "",
        "UNKNOWN",
    }
]

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
)

results = []

print(
    "\n💌 JOB PING PLATFORM URL RESOLUTION V2"
)

print(
    "=" * 72
)

print(
    f"Detected platform companies: {len(companies)}"
)


for index, company in enumerate(
    companies,
    start=1,
):
    name = company["name"]
    platform = company["platform"]
    careers_url = company["careers_url"]

    print(
        f"\n[{index}/{len(companies)}] "
        f"{name} → {platform}"
    )

    if platform not in SUPPORTED_GENERIC_PLATFORMS:
        result = {
            **company,
            "resolution_status": "needs_platform_connector",
            "resolved_platform_url": None,
        }

        results.append(result)

        print(
            "  🟠 PLATFORM CONNECTOR NEEDED"
        )

        continue

    try:
        response = session.get(
            careers_url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except Exception as error:
        result = {
            **company,
            "resolution_status": "url_unresolved",
            "resolved_platform_url": None,
            "resolution_error": repr(error),
        }

        results.append(result)

        print(
            "  🟡 REQUEST ERROR"
        )

        continue

    resolved_url, source = find_platform_url(
        company,
        response,
    )

    if resolved_url:
        result = {
            **company,
            "resolution_status": "ready_for_connector_test",
            "resolved_platform_url": resolved_url,
            "resolved_from": source,
        }

        print(
            f"  ✅ {resolved_url}"
        )
    else:
        result = {
            **company,
            "resolution_status": "url_unresolved",
            "resolved_platform_url": None,
        }

        print(
            "  🟡 ATS URL NOT FOUND"
        )

    results.append(result)

    time.sleep(REQUEST_DELAY)


save_json(
    OUTPUT_FILE,
    {
        "companies": results,
    },
)


ready = [
    company
    for company in results
    if company.get("resolution_status")
    == "ready_for_connector_test"
]

needs_connector = [
    company
    for company in results
    if company.get("resolution_status")
    == "needs_platform_connector"
]

unresolved = [
    company
    for company in results
    if company.get("resolution_status")
    == "url_unresolved"
]


print(
    "\n"
    + "=" * 72
)

print(
    "💌 PLATFORM URL RESOLUTION V2 COMPLETE"
)

print(
    "=" * 72
)

print(
    f"READY FOR CONNECTOR TEST: "
    f"{len(ready)}"
)

print(
    f"NEEDS NEW GENERIC CONNECTOR: "
    f"{len(needs_connector)}"
)

print(
    f"URL UNRESOLVED: "
    f"{len(unresolved)}"
)

print(
    f"\nSaved: {OUTPUT_FILE}"
)