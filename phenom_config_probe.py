import re
import requests

COMPANIES = {
    "eBay": "https://jobs.ebayinc.com/us/en/search-results",
    "Chewy": "https://careers.chewy.com/us/en/search-results",
}

TERMS = [
    "pageId",
    "pageName",
    "pageType",
    "refNum",
    "ddoKey",
    "/widgets",
    "EBAEBAUS",
    "CHINUS",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


def print_context(text, term, width=300):
    lower = text.lower()
    needle = term.lower()
    start = 0
    hits = 0

    while True:
        pos = lower.find(needle, start)

        if pos == -1:
            break

        hits += 1
        left = max(0, pos - width)
        right = min(len(text), pos + len(term) + width)

        snippet = text[left:right]
        snippet = re.sub(r"\s+", " ", snippet)

        print(f"\n[{term} hit {hits}]")
        print(snippet)

        start = pos + len(term)

        if hits >= 10:
            print(f"\n...stopped after {hits} hits for {term}")
            break

    if hits == 0:
        print(f"\n[{term}] <no hits>")


for company, url in COMPANIES.items():
    print("\n" + "=" * 110)
    print(company)
    print("=" * 110)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    print("STATUS:", response.status_code)
    print("FINAL URL:", response.url)
    print("HTML LENGTH:", len(response.text))

    for term in TERMS:
        print_context(response.text, term)