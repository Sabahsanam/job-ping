from connectors.oracle import OracleConnector


companies = {
    "Oracle": (
        "https://eeho.fa.us2.oraclecloud.com"
        "/hcmUI/CandidateExperience/en/sites/CX_45001/requisitions"
    ),
    "Texas Instruments": (
        "https://edbz.fa.us2.oraclecloud.com"
        "/hcmUI/CandidateExperience/en/sites/CX/requisitions"
    ),
    "JPMorgan Chase": (
        "https://jpmc.fa.oraclecloud.com"
        "/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions"
    ),
    "American Express": (
        "https://egug.fa.us2.oraclecloud.com"
        "/hcmUI/CandidateExperience/en/sites/CX_1/requisitions"
    ),
}


for name, url in companies.items():
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    connector = OracleConnector(
        name,
        url
    )

    jobs = connector.fetch_jobs()

    print(
        "TOTAL JOBS:",
        len(jobs)
    )

    print(
        "UNIQUE IDS:",
        len(
            {
                job["id"]
                for job in jobs
            }
        )
    )

    if jobs:
        print(
            "FIRST JOB:",
            jobs[0]
        )