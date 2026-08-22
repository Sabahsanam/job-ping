import json
import os


COMPANY_SOURCE_DIRECTORY = "company_sources"


def load_company_file(filepath):
    with open(filepath, "r") as file:
        data = json.load(file)

    return data.get(
        "companies",
        []
    )


def merge_company(
    existing_company,
    new_company
):
    existing_categories = set(
        existing_company.get(
            "categories",
            []
        )
    )

    new_categories = set(
        new_company.get(
            "categories",
            []
        )
    )

    existing_company["categories"] = sorted(
        existing_categories
        | new_categories
    )

    if not existing_company.get(
        "careers_url"
    ):
        existing_company["careers_url"] = (
            new_company.get(
                "careers_url"
            )
        )

    return existing_company


def load_companies():
    companies_by_name = {}


    if not os.path.exists(
        COMPANY_SOURCE_DIRECTORY
    ):
        raise FileNotFoundError(
            f"Missing directory: "
            f"{COMPANY_SOURCE_DIRECTORY}"
        )


    filenames = sorted(
        os.listdir(
            COMPANY_SOURCE_DIRECTORY
        )
    )


    for filename in filenames:

        if not filename.endswith(
            ".json"
        ):
            continue


        filepath = os.path.join(
            COMPANY_SOURCE_DIRECTORY,
            filename
        )


        companies = load_company_file(
            filepath
        )


        for company in companies:

            name = (
                company.get(
                    "name",
                    ""
                )
                .strip()
            )

            careers_url = (
                company.get(
                    "careers_url",
                    ""
                )
                .strip()
            )


            if not name:

                print(
                    f"Skipping company with no name "
                    f"in {filename}."
                )

                continue


            if not careers_url:

                print(
                    f"Skipping {name}: "
                    "no careers URL."
                )

                continue


            key = name.lower()


            if key in companies_by_name:

                companies_by_name[key] = (
                    merge_company(
                        companies_by_name[key],
                        company
                    )
                )

            else:

                companies_by_name[key] = {
                    "name": name,
                    "careers_url": careers_url,
                    "categories": sorted(
                        set(
                            company.get(
                                "categories",
                                []
                            )
                        )
                    )
                }


    companies = list(
        companies_by_name.values()
    )


    companies.sort(
        key=lambda company:
        company["name"].lower()
    )


    print(
        f"\nLoaded "
        f"{len(companies)} "
        f"unique companies."
    )


    return companies