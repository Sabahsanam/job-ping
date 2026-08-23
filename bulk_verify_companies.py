import json
import time

from company_loader import load_companies
from connectors.detector import get_connector


CANDIDATE_FILES = [
    "company_candidates_scale_150.json",
    "company_candidates_batch_50.json",
    "company_candidates.json",
    "unresolved_companies.json",
    "secondary_unresolved.json",
]

ALIAS_FILE = "company_aliases.json"


def load_json(filename, default=None):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return default if default is not None else {}


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(
            data,
            file,
            indent=2
        )


def normalize_name(name):
    return (
        str(name)
        .strip()
        .lower()
    )


def load_aliases():
    data = load_json(
        ALIAS_FILE,
        {}
    )

    aliases = data.get(
        "aliases",
        {}
    )

    merged_redirects = data.get(
        "merged_redirects",
        {}
    )

    return aliases, merged_redirects


def normalize_alias_name(
    name,
    aliases,
    merged_redirects
):
    if name in aliases:
        return aliases[name]

    if name in merged_redirects:
        return merged_redirects[name]

    return name


def load_candidates():
    """
    Merge all candidate/unresolved files.

    Deduplicate by company name while preserving
    categories from every source.
    """

    companies_by_name = {}

    for filename in CANDIDATE_FILES:

        data = load_json(
            filename,
            {}
        )

        companies = data.get(
            "companies",
            []
        )

        for company in companies:

            name = str(
                company.get(
                    "name",
                    ""
                )
            ).strip()

            careers_url = str(
                company.get(
                    "careers_url",
                    ""
                )
            ).strip()

            if not name or not careers_url:
                continue

            key = normalize_name(
                name
            )

            categories = company.get(
                "categories",
                []
            )

            if key not in companies_by_name:

                companies_by_name[key] = {
                    "name": name,
                    "careers_url": careers_url,
                    "categories": list(
                        dict.fromkeys(
                            categories
                        )
                    ),
                }

            else:

                existing = (
                    companies_by_name[
                        key
                    ]
                )

                existing[
                    "categories"
                ] = list(
                    dict.fromkeys(
                        existing.get(
                            "categories",
                            []
                        )
                        + categories
                    )
                )

                if not existing.get(
                    "careers_url"
                ):
                    existing[
                        "careers_url"
                    ] = careers_url

    return list(
        companies_by_name.values()
    )


def get_live_company_names():
    live_companies = load_companies()

    return {
        normalize_name(
            company["name"]
        )
        for company in live_companies
    }


def verify_company(company):
    """
    Try the company's configured careers URL against
    our existing connector library.

    This does NOT reverse-engineer unsupported sites.
    """

    name = company["name"]
    careers_url = company["careers_url"]

    try:

        connector = get_connector(
            name,
            careers_url
        )

    except ValueError as error:

        return {
            **company,
            "verification_status": "review",
            "reason": "unsupported_platform",
            "details": str(error),
        }

    except Exception as error:

        return {
            **company,
            "verification_status": "review",
            "reason": "connector_detection_error",
            "details": repr(error),
        }

    try:

        jobs = connector.fetch_jobs()

    except Exception as error:

        return {
            **company,
            "verification_status": "review",
            "reason": "connector_fetch_error",
            "connector": type(
                connector
            ).__name__,
            "details": repr(error),
        }

    if not jobs:

        return {
            **company,
            "verification_status": "review",
            "reason": "zero_jobs_returned",
            "connector": type(
                connector
            ).__name__,
        }

    ids = {
        str(
            job.get(
                "id",
                ""
            )
        ).strip()
        for job in jobs
        if job.get("id")
    }

    if not ids:

        return {
            **company,
            "verification_status": "review",
            "reason": "jobs_missing_ids",
            "connector": type(
                connector
            ).__name__,
            "job_count": len(jobs),
        }

    return {
        **company,
        "verification_status": "ready",
        "connector": type(
            connector
        ).__name__,
        "job_count": len(jobs),
        "unique_job_ids": len(ids),
    }


# ------------------------------------------------
# LOAD INPUTS
# ------------------------------------------------

candidates = load_candidates()

live_names = get_live_company_names()

aliases, merged_redirects = load_aliases()


print(
    "\n💌 JOB PING BULK VERIFICATION"
)

print(
    "=" * 72
)

print(
    f"Candidate companies found: "
    f"{len(candidates)}"
)

print(
    f"Companies already live: "
    f"{len(live_names)}"
)


# ------------------------------------------------
# REMOVE COMPANIES ALREADY LIVE / ALIASES
# ------------------------------------------------

pending = []

alias_skipped = []


for company in candidates:

    original_name = company["name"]

    resolved_name = normalize_alias_name(
        original_name,
        aliases,
        merged_redirects
    )

    if normalize_name(
        resolved_name
    ) in live_names:

        alias_skipped.append(
            {
                "original": original_name,
                "resolved": resolved_name,
            }
        )

        continue

    pending.append(
        company
    )


print(
    f"Companies needing verification: "
    f"{len(pending)}"
)


# ------------------------------------------------
# VERIFY
# ------------------------------------------------

ready = []
review = []
skipped = []


for index, company in enumerate(
    candidates,
    start=1
):

    name = company["name"]

    resolved_name = normalize_alias_name(
        name,
        aliases,
        merged_redirects
    )

    if normalize_name(
        resolved_name
    ) in live_names:

        skipped.append(
            company
        )

        continue


    print(
        "\n"
        + "-" * 72
    )

    print(
        f"[{index}/{len(candidates)}] "
        f"Checking {name}"
    )

    print(
        company[
            "careers_url"
        ]
    )


    result = verify_company(
        company
    )


    if (
        result[
            "verification_status"
        ]
        == "ready"
    ):

        ready.append(
            result
        )

        print(
            "✅ READY"
        )

        print(
            f"Connector: "
            f"{result.get('connector')}"
        )

        print(
            f"Jobs: "
            f"{result.get('job_count')}"
        )

        print(
            f"Unique IDs: "
            f"{result.get('unique_job_ids')}"
        )

    else:

        review.append(
            result
        )

        print(
            "🟡 REVIEW"
        )

        print(
            f"Reason: "
            f"{result.get('reason')}"
        )

        if result.get(
            "connector"
        ):

            print(
                f"Connector: "
                f"{result['connector']}"
            )

    time.sleep(
        0.3
    )


# ------------------------------------------------
# WRITE READY QUEUE
# ------------------------------------------------

promotion_ready = {
    "companies": []
}


for company in ready:

    promotion_ready[
        "companies"
    ].append(
        {
            "name": company["name"],
            "careers_url": company[
                "careers_url"
            ],
            "categories": company.get(
                "categories",
                []
            ),
            "verification_status": "ready",
        }
    )


save_json(
    "promotion_ready.json",
    promotion_ready
)


# ------------------------------------------------
# WRITE REVIEW / FAILED QUEUE
# ------------------------------------------------

promotion_failed = {
    "companies": review
}


save_json(
    "promotion_failed.json",
    promotion_failed
)


# ------------------------------------------------
# SUMMARY
# ------------------------------------------------

print(
    "\n"
    + "=" * 72
)

print(
    "💌 BULK VERIFICATION COMPLETE"
)

print(
    "=" * 72
)

print(
    f"READY: {len(ready)}"
)

print(
    f"REVIEW: {len(review)}"
)

print(
    f"ALREADY LIVE / SKIPPED: "
    f"{len(skipped)}"
)

print(
    "\nFiles updated:"
)

print(
    "  promotion_ready.json"
)

print(
    "  promotion_failed.json"
)


if ready:

    print(
        "\nREADY COMPANIES:"
    )

    for company in ready:

        print(
            f"  ✅ {company['name']} "
            f"({company['job_count']} jobs, "
            f"{company['connector']})"
        )


if review:

    print(
        "\nNEEDS REVIEW:"
    )

    for company in review:

        print(
            f"  🟡 {company['name']} "
            f"→ {company['reason']}"
        )


if alias_skipped:

    print(
        "\nALIASES / MERGED COMPANIES SKIPPED:"
    )

    for item in alias_skipped:

        if (
            item["original"]
            == item["resolved"]
        ):
            continue

        print(
            f"  ⏭️ {item['original']} "
            f"→ {item['resolved']}"
        )