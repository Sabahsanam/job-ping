import json
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


INPUT_FILE = "promotion_failed.json"

OUTPUT_FILE = "platform_clusters.json"
UNKNOWN_FILE = "platform_unknown.json"


# ------------------------------------------------
# STRONG PLATFORM SIGNATURES
# ------------------------------------------------

PLATFORM_SIGNATURES = {
    "Workday": [
        "myworkdayjobs.com",
    ],

    "Greenhouse": [
        "greenhouse.io",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
    ],

    "Lever": [
        "lever.co",
        "jobs.lever.co",
    ],

    "Ashby": [
        "ashbyhq.com",
        "jobs.ashbyhq.com",
    ],

    "SmartRecruiters": [
        "smartrecruiters.com",
    ],

    "iCIMS": [
        "icims.com",
    ],

    "Jobvite": [
        "jobvite.com",
    ],

    "Recruitee": [
        "recruitee.com",
    ],

    "Workable": [
        "workable.com",
    ],

    "Paycom": [
        "paycomonline.net",
    ],

    "Jibe": [
        "jibeapply.com",
        "jobs.jibe",
    ],

    "TalentBrew/Radancy": [
        "talentbrew.com",
        "radancy.com",
        "tbcdn.com",
    ],

    "Oracle Recruiting": [
        "oraclecloud.com",
        "fa.ocs.oraclecloud.com",
        "recruitingcejobrequisition",
        "candidateexperience",
    ],

    "Eightfold": [
        "eightfold.ai",
    ],

    "Avature": [
        "avature.net",
        "avature.com",
    ],

    "SAP SuccessFactors": [
        "successfactors.com",
    ],

    "Phenom": [
        "phenompeople.com",
        "phenom.com",
    ],
}


# ------------------------------------------------
# HELPERS
# ------------------------------------------------

def load_json(filename, default=None):
    try:

        with open(
            filename,
            "r"
        ) as file:

            return json.load(
                file
            )

    except FileNotFoundError:

        if default is not None:
            return default

        return {}


def save_json(
    filename,
    data
):

    with open(
        filename,
        "w"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )


def hostname(url):
    try:

        return (
            urlparse(
                url
            )
            .hostname
            or ""
        ).lower()

    except Exception:
        return ""


def detect_platform(
    text_values
):
    """
    Detect ATS/platform using only strong signatures.

    Returns all platform matches with evidence.
    """

    combined = "\n".join(
        str(value)
        for value in text_values
        if value
    ).lower()

    matches = []

    for (
        platform,
        signatures
    ) in PLATFORM_SIGNATURES.items():

        evidence = []

        for signature in signatures:

            if (
                signature.lower()
                in combined
            ):

                evidence.append(
                    signature
                )

        if evidence:

            matches.append(
                {
                    "platform": platform,
                    "evidence": evidence,
                }
            )

    return matches


def inspect_company(
    company
):

    name = company[
        "name"
    ]

    careers_url = company[
        "careers_url"
    ]

    original_host = hostname(
        careers_url
    )

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
        }
    )

    result = {
        "name": name,
        "careers_url": careers_url,
        "categories": company.get(
            "categories",
            []
        ),
        "status_code": None,
        "final_url": None,
        "original_host": original_host,
        "final_host": None,
        "redirected": False,
        "platform": None,
        "platform_matches": [],
        "evidence": [],
        "external_links": [],
    }

    try:

        response = session.get(
            careers_url,
            timeout=30,
            allow_redirects=True
        )

        result[
            "status_code"
        ] = response.status_code

        result[
            "final_url"
        ] = response.url

        final_host = hostname(
            response.url
        )

        result[
            "final_host"
        ] = final_host

        result[
            "redirected"
        ] = (
            original_host
            != final_host
        )

        html = (
            response.text
            or ""
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        discovered_urls = []

        for tag in soup.find_all(
            [
                "a",
                "script",
                "iframe",
                "form",
                "link",
            ]
        ):

            value = (
                tag.get(
                    "href"
                )
                or tag.get(
                    "src"
                )
                or tag.get(
                    "action"
                )
            )

            if not value:
                continue

            absolute = urljoin(
                response.url,
                value
            )

            discovered_urls.append(
                absolute
            )

        discovered_urls = list(
            dict.fromkeys(
                discovered_urls
            )
        )

        result[
            "external_links"
        ] = discovered_urls[
            :150
        ]

        inspection_values = [
            careers_url,
            response.url,
            html,
        ]

        inspection_values.extend(
            discovered_urls
        )

        matches = detect_platform(
            inspection_values
        )

        result[
            "platform_matches"
        ] = matches

        # Do not trust a platform classification
        # from an HTTP 404 page.
        if (
            response.status_code
            == 404
        ):

            result[
                "reason"
            ] = "careers_page_404"

            return result

        if matches:

            result[
                "platform"
            ] = matches[
                0
            ][
                "platform"
            ]

            result[
                "evidence"
            ] = matches[
                0
            ][
                "evidence"
            ]

        return result

    except Exception as error:

        result[
            "error"
        ] = repr(
            error
        )

        return result


# ------------------------------------------------
# LOAD REVIEW COMPANIES
# ------------------------------------------------

data = load_json(
    INPUT_FILE,
    {}
)

companies = data.get(
    "companies",
    []
)


print(
    "\n💌 JOB PING PLATFORM DISCOVERY V2"
)

print(
    "=" * 72
)

print(
    f"Companies to inspect: "
    f"{len(companies)}"
)


results = []


# ------------------------------------------------
# DISCOVER
# ------------------------------------------------

for (
    index,
    company
) in enumerate(
    companies,
    start=1
):

    print(
        "\n"
        + "-" * 72
    )

    print(
        f"[{index}/{len(companies)}] "
        f"{company['name']}"
    )

    result = inspect_company(
        company
    )

    results.append(
        result
    )

    print(
        "STATUS:",
        result.get(
            "status_code"
        )
    )

    print(
        "FINAL URL:",
        result.get(
            "final_url"
        )
    )

    if result.get(
        "redirected"
    ):

        print(
            "↪️ REDIRECT:",
            result.get(
                "original_host"
            ),
            "→",
            result.get(
                "final_host"
            )
        )

    if result.get(
        "platform"
    ):

        print(
            "✅ PLATFORM:",
            result[
                "platform"
            ]
        )

        print(
            "EVIDENCE:",
            result.get(
                "evidence"
            )
        )

    else:

        print(
            "🟡 PLATFORM UNKNOWN"
        )

        if result.get(
            "reason"
        ):

            print(
                "REASON:",
                result[
                    "reason"
                ]
            )

    if result.get(
        "error"
    ):

        print(
            "ERROR:",
            result[
                "error"
            ]
        )

    time.sleep(
        0.4
    )


# ------------------------------------------------
# GROUP RESULTS
# ------------------------------------------------

clusters = {}

unknown = []


for result in results:

    platform = result.get(
        "platform"
    )

    if platform:

        clusters.setdefault(
            platform,
            []
        ).append(
            result
        )

    else:

        unknown.append(
            result
        )


save_json(
    OUTPUT_FILE,
    {
        "platforms": clusters
    }
)

save_json(
    UNKNOWN_FILE,
    {
        "companies": unknown
    }
)


# ------------------------------------------------
# SUMMARY
# ------------------------------------------------

print(
    "\n"
    + "=" * 72
)

print(
    "💌 PLATFORM DISCOVERY V2 COMPLETE"
)

print(
    "=" * 72
)


for (
    platform,
    platform_companies
) in sorted(
    clusters.items()
):

    print(
        f"\n{platform}: "
        f"{len(platform_companies)}"
    )

    for company in platform_companies:

        print(
            f"  ✅ {company['name']}"
        )


print(
    f"\nUNKNOWN: "
    f"{len(unknown)}"
)

for company in unknown:

    redirect_note = ""

    if company.get(
        "redirected"
    ):

        redirect_note = (
            " → "
            + str(
                company.get(
                    "final_host"
                )
            )
        )

    print(
        f"  🟡 {company['name']} "
        f"(HTTP "
        f"{company.get('status_code')})"
        f"{redirect_note}"
    )


print(
    "\nREDIRECTS:"
)

redirect_count = 0

for company in results:

    if company.get(
        "redirected"
    ):

        redirect_count += 1

        print(
            f"  ↪️ {company['name']}: "
            f"{company.get('original_host')} "
            f"→ "
            f"{company.get('final_host')}"
        )


if redirect_count == 0:

    print(
        "  None"
    )


print(
    "\nFiles written:"
)

print(
    f"  {OUTPUT_FILE}"
)

print(
    f"  {UNKNOWN_FILE}"
)