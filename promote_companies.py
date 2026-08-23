import json
import os


READY_FILE = "promotion_ready.json"
SOURCE_DIRECTORY = "company_sources"

CATEGORY_TO_FILE = {
    "tech": "tech.json",
    "ai": "tech.json",
    "fintech": "tech.json",
    "entertainment": "film_entertainment.json",
    "gaming": "gaming.json",
    "vfx": "vfx_animation.json",
    "animation": "vfx_animation.json",
    "creative_tech": "vfx_animation.json",
}


def load_json_file(filepath):
    if not os.path.exists(filepath):
        return {"companies": []}

    with open(filepath, "r") as file:
        return json.load(file)


def save_json_file(filepath, data):
    with open(filepath, "w") as file:
        json.dump(
            data,
            file,
            indent=2
        )
        file.write("\n")


def choose_source_file(company):
    categories = company.get(
        "categories",
        []
    )

    for category in categories:
        filename = CATEGORY_TO_FILE.get(
            category
        )

        if filename:
            return filename

    return "tech.json"


def normalize_company(company):
    return {
        "name": company["name"],
        "careers_url": company["careers_url"],
        "categories": sorted(
            set(
                company.get(
                    "categories",
                    []
                )
            )
        )
    }


def merge_company(existing, new_company):
    existing_categories = set(
        existing.get(
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

    existing["categories"] = sorted(
        existing_categories
        |
        new_categories
    )

    if not existing.get(
        "careers_url"
    ):
        existing["careers_url"] = (
            new_company["careers_url"]
        )

    return existing


def promote_company(company):
    filename = choose_source_file(
        company
    )

    filepath = os.path.join(
        SOURCE_DIRECTORY,
        filename
    )

    data = load_json_file(
        filepath
    )

    companies = data.get(
        "companies",
        []
    )

    normalized = normalize_company(
        company
    )

    key = normalized[
        "name"
    ].strip().lower()

    found = False

    for index, existing in enumerate(
        companies
    ):
        existing_key = (
            existing.get(
                "name",
                ""
            )
            .strip()
            .lower()
        )

        if existing_key == key:
            companies[index] = merge_company(
                existing,
                normalized
            )

            found = True
            break

    if not found:
        companies.append(
            normalized
        )

    companies.sort(
        key=lambda item: (
            item.get(
                "name",
                ""
            ).lower()
        )
    )

    data["companies"] = companies

    save_json_file(
        filepath,
        data
    )

    return {
        "name": normalized["name"],
        "file": filename,
        "already_existed": found
    }


def main():
    print()
    print("💌 JOB PING COMPANY PROMOTION")
    print()

    ready_data = load_json_file(
        READY_FILE
    )

    companies = ready_data.get(
        "companies",
        []
    )

    print(
        "PRODUCTION-READY COMPANIES:",
        len(companies)
    )

    if not companies:
        print(
            "Nothing to promote."
        )
        return

    results = []

    for company in companies:
        result = promote_company(
            company
        )

        results.append(
            result
        )

        if result[
            "already_existed"
        ]:
            symbol = "🔄"
            action = "updated"
        else:
            symbol = "✅"
            action = "added"

        print(
            f"{symbol} "
            f"{result['name']} "
            f"{action} → "
            f"company_sources/"
            f"{result['file']}"
        )

    print()
    print("=" * 72)
    print("💌 PROMOTION COMPLETE")
    print("=" * 72)

    added = sum(
        1
        for result in results
        if not result[
            "already_existed"
        ]
    )

    updated = (
        len(results)
        -
        added
    )

    print(
        "ADDED:",
        added
    )

    print(
        "UPDATED:",
        updated
    )

    print(
        "TOTAL PROCESSED:",
        len(results)
    )


if __name__ == "__main__":
    main()