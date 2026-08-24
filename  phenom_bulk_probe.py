import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

companies = {
    "HPE": "https://careers.hpe.com/",
    "eBay": "https://jobs.ebayinc.com/",
    "Chewy": "https://careers.chewy.com/",
    "Boston Consulting Group": "https://careers.bcg.com/global/en/search-results",
}

headers = {"User-Agent": "Mozilla/5.0"}

for name, url in companies.items():
    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
        )

        print("STATUS:", r.status_code)
        print("FINAL URL:", r.url)
        print("HTML LENGTH:", len(r.text))

        soup = BeautifulSoup(r.text, "html.parser")

        print("\nPHENOM / API / JOB RELATED URLS:")

        seen = set()

        for tag in soup.find_all(
            ["a", "script", "iframe", "form", "link"]
        ):
            value = (
                tag.get("href")
                or tag.get("src")
                or tag.get("action")
            )

            if not value:
                continue

            full = urljoin(r.url, value)
            lowered = full.lower()

            if any(
                key in lowered
                for key in [
                    "phenom",
                    "/api/",
                    "job",
                    "search",
                    "career",
                ]
            ):
                if full not in seen:
                    seen.add(full)
                    print(full)

        print("\nRAW HTML MATCHES:")

        patterns = [
            r'https?://[^"\'<>\s]*phenompeople[^"\'<>\s]*',
            r'https?://[^"\'<>\s]+/api/[^"\'<>\s]*',
            r'["\']tenant(?:Id|_id)?["\']\s*[:=]\s*["\']([^"\']+)',
            r'["\']site(?:Id|_id)?["\']\s*[:=]\s*["\']([^"\']+)',
        ]

        for pattern in patterns:
            matches = re.findall(
                pattern,
                r.text,
                flags=re.I,
            )

            print("\nPATTERN:", pattern)

            unique = []

            for value in matches:
                if isinstance(value, tuple):
                    value = value[0]

                value = str(value)

                if value not in unique:
                    unique.append(value)

            for value in unique[:20]:
                print(value)

    except Exception as error:
        print("ERROR:", repr(error))