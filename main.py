import hashlib
import json

from company_loader import load_companies
from connectors.detector import get_connector
from matcher import matches_job
from location_filter import location_matches
from experience_filter import experience_matches
from emailer import send_job_digest


def load_json(filename, default=None):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return default if default is not None else {}


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def get_config_fingerprint(config):
    """
    Creates a stable fingerprint of the matching configuration.

    If config.json changes, the fingerprint changes and
    Job Ping runs one safe baseline scan so existing jobs
    are not accidentally sent as new alerts.
    """

    config_text = json.dumps(
        config,
        sort_keys=True
    )

    return hashlib.sha256(
        config_text.encode("utf-8")
    ).hexdigest()


# ------------------------------------------------
# LOAD CONFIG / COMPANIES / STATE
# ------------------------------------------------

config = load_json(
    "config.json"
)

companies = load_companies()

seen_jobs = load_json(
    "seen_jobs.json",
    {}
)

state = load_json(
    "state.json",
    {}
)


# ------------------------------------------------
# CHECK WHETHER CONFIG CHANGED
# ------------------------------------------------

current_config_fingerprint = get_config_fingerprint(
    config
)

previous_config_fingerprint = state.get(
    "config_fingerprint"
)

config_changed = (
    previous_config_fingerprint is not None
    and
    previous_config_fingerprint
    != current_config_fingerprint
)

first_state_run = (
    previous_config_fingerprint is None
)

baseline_mode = (
    config_changed
    or first_state_run
)


if config_changed:

    print(
        "\nJob matching configuration changed."
    )

    print(
        "Running in baseline mode: existing matching "
        "jobs will be saved without sending alerts."
    )


elif first_state_run:

    print(
        "\nInitializing Job Ping state."
    )

    print(
        "Running one safe baseline scan without alerts."
    )


# ------------------------------------------------
# STORE NEW JOBS FOUND DURING THIS SCAN
# ------------------------------------------------

new_jobs = []


# ------------------------------------------------
# SCAN ALL COMPANIES
# ------------------------------------------------

for company in companies:

    company_name = company["name"]
    careers_url = company["careers_url"]

    print(
        f"\nChecking {company_name}..."
    )


    # ------------------------------------------------
    # GET CONNECTOR + FETCH JOBS
    # ------------------------------------------------

    try:

        connector = get_connector(
            company_name,
            careers_url
        )

        jobs = connector.fetch_jobs()


    except Exception as error:

        print(
            f"Could not check {company_name}: "
            f"{error}"
        )

        continue


    # ------------------------------------------------
    # FILTER COUNTERS
    # ------------------------------------------------

    matching_jobs = []

    title_match_count = 0
    location_match_count = 0
    experience_match_count = 0


    # ------------------------------------------------
    # FILTER JOBS
    # ------------------------------------------------

    for job in jobs:

        # --------------------------------------------
        # FIRST TITLE FILTER
        # --------------------------------------------

        title_match = matches_job(
            job,
            config
        )

        if not title_match:
            continue

        title_match_count += 1


        # --------------------------------------------
        # FIRST LOCATION FILTER
        # --------------------------------------------

        # Some connectors provide a useful location
        # directly from the listing page.
        #
        # Other connectors, such as SEGA, may only
        # provide the location after opening the full
        # job page.
        #
        # If location is blank, do NOT reject the job
        # yet. Let enrichment load the real location.

        listing_location = (
            job.get(
                "location",
                ""
            )
            or ""
        ).strip()

        needs_location_enrichment = (
            not listing_location
            and hasattr(
                connector,
                "enrich_job"
            )
        )


        # If we already have a location, use the cheap
        # location filter before loading job details.

        if not needs_location_enrichment:

            location_match = location_matches(
                job,
                config.get(
                    "allowed_locations",
                    []
                )
            )

            if not location_match:
                continue

            location_match_count += 1


        # --------------------------------------------
        # FETCH FULL JOB DETAILS ONLY WHEN NEEDED
        # --------------------------------------------

        if hasattr(
            connector,
            "enrich_job"
        ):

            try:

                job = connector.enrich_job(
                    job
                )

            except Exception as error:

                print(
                    "Could not load full job details "
                    f"for {job.get('title', 'Unknown Job')}: "
                    f"{error}"
                )

                continue


        # --------------------------------------------
        # RECHECK TITLE AFTER ENRICHMENT
        # --------------------------------------------

        # Some ATS platforms show shortened titles
        # on the listing page.
        #
        # Example:
        #
        # Cloud Engineer
        #
        # may become:
        #
        # Senior Cloud Engineer
        #
        # after loading the full page.

        title_match_after_enrichment = matches_job(
            job,
            config
        )

        if not title_match_after_enrichment:
            continue


        # --------------------------------------------
        # CHECK / RECHECK LOCATION
        # --------------------------------------------

        # The enriched job may contain a more accurate
        # location or may provide a location that was
        # completely missing from the listing.

        location_match_after_enrichment = location_matches(
            job,
            config.get(
                "allowed_locations",
                []
            )
        )

        if not location_match_after_enrichment:
            continue


        # If location was blank on the listing page,
        # this is the first point where it has actually
        # passed the location filter.
        #
        # For jobs that already had a location, the
        # counter was incremented earlier.

        if needs_location_enrichment:
            location_match_count += 1


        # --------------------------------------------
        # UBER DESCRIPTION ENRICHMENT
        # --------------------------------------------

        # Uber's Oracle listing feed gives us the
        # title/location cheaply, but the complete
        # qualifications live in a separate detail
        # endpoint.
        #
        # Only fetch that description AFTER the job
        # already passed title + location filters.
        #
        # This prevents Job Ping from making detail
        # requests for all 700+ Uber jobs every scan.

        if (
            job.get("source") == "uber"
            and hasattr(
                connector,
                "fetch_description"
            )
        ):

            current_description = (
                job.get(
                    "description",
                    ""
                )
                or ""
            ).strip()

            if not current_description:

                try:

                    description = (
                        connector.fetch_description(
                            job["id"]
                        )
                    )

                    if description:

                        job[
                            "description"
                        ] = description


                except Exception as error:

                    print(
                        "Could not load Uber description "
                        f"for {job.get('title', 'Unknown Job')}: "
                        f"{error}"
                    )

                    # We do not want to let an Uber job
                    # through the experience filter using
                    # only its title when its qualification
                    # data failed to load.

                    continue


        # --------------------------------------------
        # EXPERIENCE FILTER
        # --------------------------------------------

        experience_match = experience_matches(
            job,
            config.get(
                "early_career_indicators",
                []
            )
        )

        if not experience_match:
            continue

        experience_match_count += 1


        # --------------------------------------------
        # FINAL MATCH
        # --------------------------------------------

        matching_jobs.append(
            job
        )


    # ------------------------------------------------
    # PRINT FILTER SUMMARY
    # ------------------------------------------------

    print(
        f"Found {len(jobs)} total jobs."
    )

    print(
        f"Title matches: "
        f"{title_match_count}"
    )

    print(
        f"US/location matches: "
        f"{location_match_count}"
    )

    print(
        f"Experience matches: "
        f"{experience_match_count}"
    )

    print(
        f"Final matches: "
        f"{len(matching_jobs)}"
    )


    # ------------------------------------------------
    # GLOBAL BASELINE MODE
    # ------------------------------------------------

    if baseline_mode:

        if company_name not in seen_jobs:
            seen_jobs[company_name] = []


        for job in matching_jobs:

            job_id = job["id"]

            if (
                job_id
                not in seen_jobs[company_name]
            ):

                seen_jobs[
                    company_name
                ].append(
                    job_id
                )


        print(
            f"Baseline updated for "
            f"{company_name}. "
            "No alerts sent."
        )

        continue


    # ------------------------------------------------
    # FIRST SCAN FOR A NEW COMPANY
    # ------------------------------------------------

    if company_name not in seen_jobs:

        print(
            f"First scan for {company_name}. "
            "Saving current jobs without "
            "sending alerts."
        )

        seen_jobs[company_name] = [
            job["id"]
            for job in matching_jobs
        ]

        continue


    # ------------------------------------------------
    # FIND GENUINELY NEW JOBS
    # ------------------------------------------------

    for job in matching_jobs:

        job_id = job["id"]

        if (
            job_id
            not in seen_jobs[company_name]
        ):

            print(
                "\nNEW JOB FOUND!"
            )

            print(
                f"Company: "
                f"{company_name}"
            )

            print(
                f"Title: "
                f"{job['title']}"
            )

            print(
                f"Location: "
                f"{job.get('location')}"
            )

            print(
                job["url"]
            )

            print(
                "-" * 50
            )

            new_jobs.append(
                job
            )


        else:

            print(
                f"Already seen: "
                f"{job['title']}"
            )


# ------------------------------------------------
# SCAN COMPLETE
# ------------------------------------------------

print(
    "\nScan complete."
)


# ------------------------------------------------
# BASELINE RUN
# ------------------------------------------------

if baseline_mode:

    print(
        "Baseline scan complete. "
        "No alerts were sent."
    )


# ------------------------------------------------
# NORMAL RUN
# ------------------------------------------------

else:

    if new_jobs:

        print(
            f"Found {len(new_jobs)} new job"
            f"{'s' if len(new_jobs) != 1 else ''}."
        )


        # --------------------------------------------
        # SEND ONE DIGEST EMAIL
        # --------------------------------------------

        email_sent = send_job_digest(
            new_jobs
        )


        if email_sent:

            # Only mark jobs as seen AFTER
            # the email successfully sends.

            for job in new_jobs:

                company_name = job["company"]
                job_id = job["id"]

                if company_name not in seen_jobs:
                    seen_jobs[
                        company_name
                    ] = []


                if (
                    job_id
                    not in seen_jobs[company_name]
                ):

                    seen_jobs[
                        company_name
                    ].append(
                        job_id
                    )


            print(
                "New jobs marked as seen."
            )


        else:

            print(
                "Digest failed. New jobs were NOT "
                "marked as seen, so Job Ping can "
                "try again next scan."
            )


    else:

        print(
            "No new matching jobs found."
        )


# ------------------------------------------------
# SAVE JOB HISTORY
# ------------------------------------------------

save_json(
    "seen_jobs.json",
    seen_jobs
)


# ------------------------------------------------
# SAVE CONFIG STATE
# ------------------------------------------------

state[
    "config_fingerprint"
] = current_config_fingerprint

save_json(
    "state.json",
    state
)