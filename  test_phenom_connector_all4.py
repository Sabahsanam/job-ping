from connectors.phenom import PhenomConnector


TESTS = {
    "HPE": "https://careers.hpe.com/us/en/search-results",
    "eBay": "https://jobs.ebayinc.com/us/en/search-results",
    "Chewy": "https://careers.chewy.com/us/en/search-results",
    "Boston Consulting Group": (
        "https://careers.bcg.com/global/en/search-results"
    ),
}


all_good = True

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

    ok = (
        len(jobs) > 0
        and len(jobs) == len(unique_ids)
    )

    print("PASS:", ok)

    if not ok:
        all_good = False

    if jobs:
        first = jobs[0]

        print("FIRST JOB:")
        print("  id:", first["id"])
        print("  title:", first["title"])
        print("  location:", first["location"])
        print("  source:", first["source"])
        print("  url:", first["url"])
        print(
            "  description chars:",
            len(first.get("description") or "")
        )


print("\n" + "=" * 90)
print("FINAL RESULT")
print("=" * 90)
print("ALL FOUR PASS:", all_good)