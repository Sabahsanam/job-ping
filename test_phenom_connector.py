from connectors.phenom import PhenomConnector


TESTS = {
    "HPE": "https://careers.hpe.com/us/en/search-results",
    "Boston Consulting Group": (
        "https://careers.bcg.com/global/en/search-results"
    ),
}


for company, url in TESTS.items():
    print("\n" + "=" * 90)
    print(company)
    print("=" * 90)

    connector = PhenomConnector(company, url)
    jobs = connector.fetch_jobs()

    unique_ids = {
        job["id"]
        for job in jobs
    }

    print("TOTAL:", len(jobs))
    print("UNIQUE IDS:", len(unique_ids))

    if jobs:
        print("FIRST JOB:")
        print("  id:", jobs[0]["id"])
        print("  title:", jobs[0]["title"])
        print("  location:", jobs[0]["location"])
        print("  source:", jobs[0]["source"])
        print("  url:", jobs[0]["url"])
        print(
            "  description chars:",
            len(jobs[0].get("description") or "")
        )