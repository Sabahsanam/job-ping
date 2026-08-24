import json
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


INPUT_FILE = "platform_discovery_150.json"
OUTPUT_FILE = "platform_resolved_150.json"

TIMEOUT = 15
REQUEST_DELAY = 0.15


PLATFORM_URL_SIGNATURES = {
    "Workday": [
        "myworkdayjobs.com",
    ],
    "Greenhouse": [
        "greenhouse.io",
    ],
    "Lever": [
        "lever.co",
    ],
    "Ashby": [
        "ashbyhq.com",
    ],
    "SmartRecruiters": [
        "smartrecruiters.com",
    ],
    "iCIMS": [
        "icims.com",
    ],
    "Jobvite": [
        "jobvite.com",
    ],
    "Recruitee": [
        "recruitee.com",
    ],
    "Workable": [
        "workable.com",
    ],
    "Paycom": [
        "paycomonline.net",
    ],
    "Jibe": [
        "jibeapply.com",
        "jobs.jibe.com",
    ],
    "TalentBrew/Radancy": [
        "talentbrew.com",
        "radancy.com",
    ],
    "Oracle": [
        "oraclecloud.com",
    ],
    "Eightfold": [
        "eightfold.ai",
    ],
    "Avature": [
        "avature.net",
        "avature.com",
    ],
    "SAP SuccessFactors": [
        "successfactors.com",
    ],
    "Phenom": [
        "phenompeople.com",
        "phenom.com",
    ],
}


# Platforms for which our connector is already intended
# to be reusable across companies.
GENERIC_CONNECTOR_PLATFORMS = {
    "Workday",
    "Greenhouse",
    "Lever",
    "Ashby",
    "SmartRecruiters",
    "iCIMS",
    "Jobvite",
    "Recruitee",
    "Workable",
    "Paycom",
    "Jibe",
    "Eightfold",
    "Avature",
    "SAP SuccessFactors",
}


def load_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def url_matches_platform(url, platform):
    if not url:
        return False

    lowered = url.lower()

    for signature in PLATFORM_URL_SIGNATURES.get(platform, []):
        if signature.lower() in lowered:
            return True

    return False


def candidate_urls(response):
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    values = []

    # Redirect destination first.
    values.append(
        (
            "final_url",
            response.url,
        )
    )

    # Then actual URLs exposed in the page.
    for tag in soup.find_all(
        [
            "a",
            "script",
            "iframe",
            "form",
            "link",
        ]
    ):
        raw = (
            tag.get("href")
            or tag.get("src")
            or tag.get("action")
        )

        if not raw:
            continue

        values.append(
            (
                tag.name,
                urljoin(
                    response.url,
                    raw
                ),
            )
        )

    return values


def choose_resolved_url(
    company,
    response
):
    platform = company["platform"]
    careers_url = company["careers_url"]

    # Configured URL is already directly on the ATS.
    if url_matches_platform(
        careers_url,
        platform
    ):
        return (
            careers_url,
            "configured_url"
        )

    matches = []

    for source, value in candidate_urls(
        response
    ):
        if url_matches_platform(
            value,
            platform
        ):
            matches.append(
                (
                    source,
                    value,
                )
            )

    if matches:
        # Prefer links/iframes/forms over static JS/CSS assets.
        priority = {
            "a": 0,
            "iframe": 1,
            "form": 2,
            "final_url": 3,
            "script": 4,
            "link": 5,
        }

        matches.sort(
            key=lambda item: (
                priority.get(
                    item[0],
                    99
                ),
                len(item[1]),
            )
        )

        source, value = matches[0]

        return (
            value,
            source
        )

    # Some platforms commonly operate behind a first-party vanity
    # careers domain. Their generic connector can often use that
    # first-party careers URL directly.
    if platform in {
        "Eightfold",
        "SAP SuccessFactors",
    }:
        return (
            response.url,
            "first_party_platform_site"
        )

    return (
        None,
        None
    )


data = load_json(
    INPUT_FILE
)

companies = [
    company
    for company in data.get(
        "companies",
        []
    )
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


resolved = []
needs_platform_connector = []
unresolved_url = []


print(
    "\n💌 JOB PING PLATFORM URL RESOLUTION"
)

print(
    "=" * 72
)

print(
    f"Detected platform companies: "
    f"{len(companies)}"
)


for index, company in enumerate(
    companies,
    start=1
):
    name = company["name"]
    platform = company["platform"]
    careers_url = company["careers_url"]

    print(
        f"\n[{index}/{len(companies)}] "
        f"{name} → {platform}"
    )

    # These platforms were detected, but Job Ping does not yet
    # have a reusable generic connector for them.
    if platform not in GENERIC_CONNECTOR_PLATFORMS:
        result = {
            **company,
            "resolution_status": "needs_platform_connector",
            "resolved_platform_url": None,
        }

        needs_platform_connector.append(
            result
        )

        resolved.append(
            result
        )

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

        unresolved_url.append(
            result
        )

        resolved.append(
            result
        )

        print(
            "  🟡 REQUEST ERROR"
        )

        continue

    resolved_url, source = choose_resolved_url(
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

        unresolved_url.append(
            result
        )

        print(
            "  🟡 ATS URL NOT FOUND"
        )

    resolved.append(
        result
    )

    time.sleep(
        REQUEST_DELAY
    )


save_json(
    OUTPUT_FILE,
    {
        "companies": resolved,
    }
)


ready_count = sum(
    1
    for company in resolved
    if company.get(
        "resolution_status"
    )
    == "ready_for_connector_test"
)


print(
    "\n"
    + "=" * 72
)

print(
    "💌 PLATFORM URL RESOLUTION COMPLETE"
)

print(
    "=" * 72
)

print(
    f"READY FOR CONNECTOR TEST: "
    f"{ready_count}"
)

print(
    f"NEEDS NEW GENERIC CONNECTOR: "
    f"{len(needs_platform_connector)}"
)

print(
    f"URL UNRESOLVED: "
    f"{len(unresolved_url)}"
)

print(
    f"\nSaved: {OUTPUT_FILE}"
)


if needs_platform_connector:
    print(
        "\nPLATFORM CONNECTORS STILL NEEDED:"
    )

    grouped = {}

    for company in needs_platform_connector:
        grouped.setdefault(
            company["platform"],
            []
        ).append(
            company["name"]
        )

    for platform, names in sorted(
        grouped.items()
    ):
        print(
            f"  {platform}: "
            + ", ".join(names)
        )