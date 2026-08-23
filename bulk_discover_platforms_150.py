import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from company_loader import load_companies


CANDIDATE_FILES = [
    "company_candidates_scale_150.json",
    "company_candidates_batch_50.json",
    "company_candidates.json",
    "unresolved_companies.json",
    "secondary_unresolved.json",
]

ALIAS_FILE = "company_aliases.json"

OUTPUT_FILE = "platform_discovery_150.json"
UNKNOWN_FILE = "platform_unknown_150.json"

TIMEOUT = 15
REQUEST_DELAY = 0.15


PLATFORM_SIGNATURES = [
    ("Workday", ["myworkdayjobs.com"]),
    ("Greenhouse", ["greenhouse.io", "boards.greenhouse.io"]),
    ("Lever", ["lever.co", "jobs.lever.co"]),
    ("Ashby", ["ashbyhq.com", "jobs.ashbyhq.com"]),
    ("SmartRecruiters", ["smartrecruiters.com"]),
    ("iCIMS", ["icims.com"]),
    ("Jobvite", ["jobvite.com"]),
    ("Recruitee", ["recruitee.com"]),
    ("Workable", ["workable.com", "apply.workable.com"]),
    ("Paycom", ["paycomonline.net"]),
    ("Jibe", ["jibeapply.com", "jobs.jibe.com"]),
    ("TalentBrew/Radancy", ["talentbrew.com", "radancy.com"]),
    ("Oracle", ["oraclecloud.com", "fa.ocs.oraclecloud.com"]),
    ("Eightfold", ["eightfold.ai", "/api/pcsx/", "pcsx-data"]),
    ("Avature", ["avature.net", "avature.com"]),
    ("SAP SuccessFactors", [
        "successfactors.com",
        "rmkcdn.successfactors.com",
        "/platform/js/j2w/",
        "j2w.searchresults",
    ]),
    ("Phenom", ["phenompeople.com", "phenom.com"]),
]


def load_json(filename, default=None):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return default if default is not None else {}


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def normalize_name(name):
    return str(name).strip().lower()


def load_aliases():
    data = load_json(ALIAS_FILE, {})
    return (
        data.get("aliases", {}),
        data.get("merged_redirects", {}),
    )


def resolve_alias(name, aliases, merged_redirects):
    if name in aliases:
        return aliases[name]

    if name in merged_redirects:
        return merged_redirects[name]

    return name


def load_candidates():
    companies_by_name = {}

    for filename in CANDIDATE_FILES:
        data = load_json(filename, {})

        for company in data.get("companies", []):
            name = str(company.get("name", "")).strip()
            careers_url = str(company.get("careers_url", "")).strip()

            if not name or not careers_url:
                continue

            key = normalize_name(name)
            categories = company.get("categories", [])

            if key not in companies_by_name:
                companies_by_name[key] = {
                    "name": name,
                    "careers_url": careers_url,
                    "categories": list(dict.fromkeys(categories)),
                }
            else:
                existing = companies_by_name[key]

                existing["categories"] = list(
                    dict.fromkeys(
                        existing.get("categories", [])
                        + categories
                    )
                )

    return list(companies_by_name.values())


def live_company_names():
    return {
        normalize_name(company["name"])
        for company in load_companies()
    }


def classify_text(text):
    lowered = text.lower()

    for platform, signatures in PLATFORM_SIGNATURES:
        for signature in signatures:
            if signature.lower() in lowered:
                return platform, signature

    return None, None


def collect_page_evidence(response):
    soup = BeautifulSoup(response.text, "html.parser")

    values = [
        response.url,
        response.text,
    ]

    for tag in soup.find_all(
        ["a", "script", "iframe", "form", "link"]
    ):
        value = (
            tag.get("href")
            or tag.get("src")
            or tag.get("action")
        )

        if value:
            values.append(
                urljoin(response.url, value)
            )

    return "\n".join(values)


def classify_company(company, session):
    name = company["name"]
    careers_url = company["careers_url"]

    # First classify the configured URL itself.
    platform, signature = classify_text(careers_url)

    if platform:
        return {
            **company,
            "platform": platform,
            "evidence": "configured_url",
            "matched_signature": signature,
            "final_url": careers_url,
            "http_status": None,
        }

    try:
        response = session.get(
            careers_url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except Exception as error:
        return {
            **company,
            "platform": "UNKNOWN",
            "reason": "request_error",
            "details": repr(error),
        }

    evidence = collect_page_evidence(response)

    platform, signature = classify_text(evidence)

    result = {
        **company,
        "platform": platform or "UNKNOWN",
        "final_url": response.url,
        "http_status": response.status_code,
    }

    if platform:
        result["evidence"] = "redirect_or_html"
        result["matched_signature"] = signature
    else:
        result["reason"] = "no_supported_platform_signature"

    return result


candidates = load_candidates()
live_names = live_company_names()
aliases, merged_redirects = load_aliases()

pending = []
skipped = []

for company in candidates:
    resolved = resolve_alias(
        company["name"],
        aliases,
        merged_redirects,
    )

    if normalize_name(resolved) in live_names:
        skipped.append(
            {
                "original": company["name"],
                "resolved": resolved,
            }
        )
        continue

    pending.append(company)


print("\n💌 JOB PING PLATFORM DISCOVERY")
print("=" * 72)
print(f"Candidate companies found: {len(candidates)}")
print(f"Companies already live: {len(live_names)}")
print(f"Companies needing platform discovery: {len(pending)}")


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
unknown = []

for index, company in enumerate(pending, start=1):
    print(
        f"[{index}/{len(pending)}] "
        f"{company['name']}"
    )

    result = classify_company(
        company,
        session,
    )

    results.append(result)

    if result["platform"] == "UNKNOWN":
        unknown.append(result)
        print("  🟡 UNKNOWN")
    else:
        print(
            f"  ✅ {result['platform']}"
        )

    time.sleep(REQUEST_DELAY)


save_json(
    OUTPUT_FILE,
    {
        "companies": results,
        "skipped_live_or_alias": skipped,
    },
)

save_json(
    UNKNOWN_FILE,
    {
        "companies": unknown,
    },
)


counts = {}

for result in results:
    platform = result["platform"]
    counts[platform] = counts.get(platform, 0) + 1


print("\n" + "=" * 72)
print("💌 PLATFORM DISCOVERY COMPLETE")
print("=" * 72)

for platform, count in sorted(
    counts.items(),
    key=lambda item: (-item[1], item[0])
):
    print(
        f"{platform}: {count}"
    )

print(
    f"\nUNKNOWN: {len(unknown)}"
)

print(
    f"SKIPPED LIVE / ALIASES: {len(skipped)}"
)

print("\nFiles updated:")
print(f"  {OUTPUT_FILE}")
print(f"  {UNKNOWN_FILE}")