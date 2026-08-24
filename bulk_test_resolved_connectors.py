import json
import time

from connectors.workday import WorkdayConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.ashby import AshbyConnector
from connectors.smartrecruiters import SmartRecruitersConnector
from connectors.icims import ICIMSConnector
from connectors.workable import WorkableConnector
from connectors.eightfold import EightfoldConnector
from connectors.successfactors import SuccessFactorsConnector


INPUT_FILE = "platform_resolved_150_v2.json"
READY_FILE = "platform_connector_ready_150.json"
REVIEW_FILE = "platform_connector_review_150.json"

REQUEST_DELAY = 0.25


CONNECTORS = {
    "Workday": WorkdayConnector,
    "Greenhouse": GreenhouseConnector,
    "Lever": LeverConnector,
    "Ashby": AshbyConnector,
    "SmartRecruiters": SmartRecruitersConnector,
    "iCIMS": ICIMSConnector,
    "Workable": WorkableConnector,
    "Eightfold": EightfoldConnector,
    "SAP SuccessFactors": SuccessFactorsConnector,
}


def load_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def verify_job_shape(jobs):
    if not jobs:
        return False, "zero_jobs_returned"

    ids = set()

    for job in jobs:
        job_id = str(
            job.get("id", "")
        ).strip()

        if job_id:
            ids.add(job_id)

    if not ids:
        return False, "jobs_missing_ids"

    return True, len(ids)


data = load_json(INPUT_FILE)

companies = [
    company
    for company in data.get("companies", [])
    if company.get("resolution_status")
    == "ready_for_connector_test"
]


print("\n💌 JOB PING BULK CONNECTOR TEST")
print("=" * 72)
print(f"Companies ready for connector test: {len(companies)}")


ready = []
review = []


for index, company in enumerate(
    companies,
    start=1,
):
    name = company["name"]
    platform = company["platform"]
    resolved_url = company.get(
        "resolved_platform_url"
    )

    print(
        f"\n[{index}/{len(companies)}] "
        f"{name} → {platform}"
    )

    print(
        f"  URL: {resolved_url}"
    )

    connector_class = CONNECTORS.get(
        platform
    )

    if connector_class is None:
        result = {
            **company,
            "connector_test_status": "review",
            "reason": "no_connector_mapping",
        }

        review.append(result)

        print("  🟡 REVIEW: no connector mapping")
        continue

    try:
        connector = connector_class(
            name,
            resolved_url,
        )
    except Exception as error:
        result = {
            **company,
            "connector_test_status": "review",
            "reason": "connector_init_error",
            "details": repr(error),
            "connector": connector_class.__name__,
        }

        review.append(result)

        print(
            f"  🟡 REVIEW: init failed → "
            f"{repr(error)}"
        )
        continue

    try:
        jobs = connector.fetch_jobs()
    except Exception as error:
        result = {
            **company,
            "connector_test_status": "review",
            "reason": "connector_fetch_error",
            "details": repr(error),
            "connector": type(connector).__name__,
        }

        review.append(result)

        print(
            f"  🟡 REVIEW: fetch failed → "
            f"{repr(error)}"
        )
        continue

    valid, details = verify_job_shape(
        jobs
    )

    if not valid:
        result = {
            **company,
            "connector_test_status": "review",
            "reason": details,
            "connector": type(connector).__name__,
            "job_count": len(jobs),
        }

        review.append(result)

        print(
            f"  🟡 REVIEW: {details}"
        )
        continue

    unique_ids = details

    sample_jobs = []

    for job in jobs[:3]:
        sample_jobs.append(
            {
                "id": job.get("id"),
                "title": job.get("title"),
                "location": job.get("location"),
                "url": job.get("url"),
            }
        )

    result = {
        **company,
        "connector_test_status": "ready",
        "connector": type(connector).__name__,
        "job_count": len(jobs),
        "unique_job_ids": unique_ids,
        "sample_jobs": sample_jobs,
    }

    ready.append(result)

    print("  ✅ READY")
    print(
        f"  Jobs: {len(jobs)}"
    )
    print(
        f"  Unique IDs: {unique_ids}"
    )

    time.sleep(REQUEST_DELAY)


save_json(
    READY_FILE,
    {
        "companies": ready,
    },
)

save_json(
    REVIEW_FILE,
    {
        "companies": review,
    },
)


print("\n" + "=" * 72)
print("💌 BULK CONNECTOR TEST COMPLETE")
print("=" * 72)

print(
    f"READY: {len(ready)}"
)

print(
    f"REVIEW: {len(review)}"
)

print("\nFiles updated:")
print(f"  {READY_FILE}")
print(f"  {REVIEW_FILE}")


if ready:
    print("\nREADY COMPANIES:")

    for company in ready:
        print(
            f"  ✅ {company['name']} "
            f"({company['job_count']} jobs, "
            f"{company['connector']})"
        )


if review:
    print("\nNEEDS REVIEW:")

    for company in review:
        print(
            f"  🟡 {company['name']} "
            f"→ {company['reason']}"
        )
        