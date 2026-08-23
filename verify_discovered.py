import json

from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.ashby import AshbyConnector


DISCOVERED_FILE = "discovered_companies.json"
READY_FILE = "promotion_ready.json"
FAILED_FILE = "promotion_failed.json"


CONNECTORS = {
    "Greenhouse": GreenhouseConnector,
    "Lever": LeverConnector,
    "Ashby": AshbyConnector,
}


def load_discovered():
    with open(DISCOVERED_FILE, "r") as file:
        data = json.load(file)

    return data.get("companies", [])


def verify_company(company):
    name = company["name"]
    careers_url = company["careers_url"]
    ats = company["ats"]

    print()
    print("=" * 72)
    print("VERIFYING:", name)
    print("ATS:", ats)
    print("URL:", careers_url)

    connector_class = CONNECTORS.get(ats)

    if not connector_class:
        print("⚠️ No verification connector configured.")

        return {
            **company,
            "verification_status": "unsupported_connector"
        }

    try:
        connector = connector_class(
            name,
            careers_url
        )

        jobs = connector.fetch_jobs()

    except Exception as error:
        print(
            "❌ CONNECTOR FAILED:",
            error
        )

        return {
            **company,
            "verification_status": "failed",
            "verification_error": str(error)
        }

    if not jobs:
        print("❌ Connector returned 0 jobs.")

        return {
            **company,
            "verification_status": "failed",
            "verification_error": "Connector returned zero jobs."
        }

    valid_jobs = []

    for job in jobs:
        if (
            job.get("id")
            and job.get("title")
            and job.get("url")
        ):
            valid_jobs.append(job)

    if not valid_jobs:
        print(
            "❌ Jobs returned, but none passed "
            "basic normalization validation."
        )

        return {
            **company,
            "verification_status": "failed",
            "verification_error": (
                "No normalized jobs contained "
                "id, title, and URL."
            )
        }

    print("✅ CONNECTOR VERIFIED")
    print("JOBS FETCHED:", len(jobs))
    print("VALID JOBS:", len(valid_jobs))

    print("\nSAMPLE:")

    for job in valid_jobs[:3]:
        print(
            "-",
            job.get("title"),
            "|",
            job.get("location")
        )

    return {
        **company,
        "verified_job_count": len(valid_jobs),
        "verification_status": "ready"
    }


def save_json(filename, companies):
    with open(filename, "w") as file:
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
    print("💌 JOB PING DISCOVERY VERIFICATION")
    print()

    companies = load_discovered()

    print(
        "DISCOVERED COMPANIES:",
        len(companies)
    )

    ready = []
    failed = []

    for company in companies:
        result = verify_company(company)

        if result["verification_status"] == "ready":
            ready.append(result)
        else:
            failed.append(result)

    save_json(
        READY_FILE,
        ready
    )

    save_json(
        FAILED_FILE,
        failed
    )

    print()
    print()
    print("=" * 72)
    print("💌 VERIFICATION SUMMARY")
    print("=" * 72)

    print(
        "INPUT:",
        len(companies)
    )

    print(
        "PRODUCTION READY:",
        len(ready)
    )

    print(
        "FAILED:",
        len(failed)
    )

    if companies:
        rate = (
            len(ready) /
            len(companies)
        ) * 100

        print(
            "CONNECTOR SUCCESS RATE:",
            f"{rate:.1f}%"
        )

    print()
    print(
        "Saved →",
        READY_FILE
    )

    print(
        "Saved →",
        FAILED_FILE
    )


if __name__ == "__main__":
    main()