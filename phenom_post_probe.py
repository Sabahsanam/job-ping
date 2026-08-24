import json
import requests

COMPANIES = {
    "HPE": "https://careers.hpe.com/api/jobs/search",
    "eBay": "https://jobs.ebayinc.com/api/jobs/search",
    "Chewy": "https://careers.chewy.com/api/jobs/search",
    "Boston Consulting Group": "https://careers.bcg.com/api/jobs/search",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}

PAYLOADS = [
    {
        "keywords": "",
        "from": 0,
        "size": 10,
    },
    {
        "keywords": "",
        "from": 0,
        "size": 10,
        "locationData": {
            "location": "",
            "latlong": "",
            "radius": 0,
            "radiusUnit": "mi",
        },
    },
    {
        "keywords": "*",
        "from": 0,
        "size": 10,
    },
]

def show_response(response):
    print("STATUS:", response.status_code)
    print("CONTENT-TYPE:", response.headers.get("content-type"))

    text = response.text.strip()

    try:
        data = response.json()
        print("TOP-LEVEL TYPE:", type(data).__name__)

        if isinstance(data, dict):
            print("TOP-LEVEL KEYS:", list(data.keys()))
            print(json.dumps(data, indent=2)[:3000])
        else:
            print(json.dumps(data, indent=2)[:3000])

    except Exception:
        print("BODY:", text[:1500].replace("\n", " "))


for company, url in COMPANIES.items():
    print("\n" + "=" * 100)
    print(company)
    print("=" * 100)

    for i, payload in enumerate(PAYLOADS, start=1):
        print(f"\n--- PAYLOAD {i} ---")
        print(json.dumps(payload, indent=2))

        try:
            r = requests.post(
                url,
                headers=HEADERS,
                json=payload,
                timeout=30,
                allow_redirects=True,
            )
            show_response(r)

        except Exception as exc:
            print("ERROR:", repr(exc))