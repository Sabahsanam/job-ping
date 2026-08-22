import re


US_STATE_ABBREVIATIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE",
    "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC"
}


US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia"
}


US_CITY_MARKERS = {
    "atlanta",
    "austin",
    "boston",
    "chicago",
    "dallas",
    "denver",
    "houston",
    "los angeles",
    "miami",
    "new york",
    "raleigh",
    "san diego",
    "san francisco",
    "san jose",
    "santa monica",
    "seattle",
    "washington dc",
    "washington, dc"
}


NON_US_COUNTRY_MARKERS = {
    "canada",
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "france",
    "germany",
    "spain",
    "italy",
    "sweden",
    "norway",
    "denmark",
    "finland",
    "poland",
    "romania",
    "india",
    "china",
    "japan",
    "south korea",
    "australia",
    "new zealand",
    "mexico",
    "brazil",
    "argentina",
    "ireland",
    "netherlands",
    "belgium",
    "switzerland",
    "austria",
    "portugal",
    "singapore"
}


def normalize(text):
    return (text or "").lower().strip()


def contains_us_country_marker(location):
    """
    Detect explicit United States wording.

    This check should take priority over interpreting
    state abbreviations such as CA as country codes.
    """

    markers = [
        "united states",
        "united states of america",
        "usa",
        "u.s.",
        "u.s.a.",
        "us remote",
        "remote us",
        "remote / us",
        "remote - us",
        "remote, us"
    ]

    location = normalize(
        location
    )

    for marker in markers:

        if marker in location:
            return True

    return False


def contains_non_us_country_marker(location):

    location = normalize(
        location
    )

    for marker in NON_US_COUNTRY_MARKERS:

        if marker in location:
            return True

    return False


def get_explicit_country_code(location):
    """
    Detect ATS-style country codes without confusing
    U.S. state abbreviations with country codes.

    Examples:

        Atlanta, GA, us
        -> us

        Montreal, QC, ca
        -> ca

        Saint-Mandé, fr
        -> fr

        San Francisco, CA
        -> None

        Redmond, WA
        -> None

        United States, San Diego, CA
        -> None
    """

    original_location = (
        location or ""
    ).strip()


    # -----------------------------------------
    # EXPLICIT UNITED STATES TEXT WINS
    # -----------------------------------------
    #
    # Example:
    #
    # United States, San Diego, CA
    #
    # The final CA is California, NOT Canada.

    if contains_us_country_marker(
        original_location
    ):
        return "us"


    parts = [
        part.strip()
        for part in original_location.split(",")
        if part.strip()
    ]

    if not parts:
        return None


    last_part = parts[-1]

    if not re.fullmatch(
        r"[A-Za-z]{2}",
        last_part
    ):
        return None


    code = last_part.lower()
    upper_code = last_part.upper()


    # -----------------------------------------
    # EXPLICIT US COUNTRY CODE
    # -----------------------------------------

    if code == "us":
        return "us"


    # -----------------------------------------
    # TWO-PART US CITY + STATE
    # -----------------------------------------
    #
    # San Francisco, CA
    # Redmond, WA
    #
    # These should not be interpreted as
    # country codes.

    if (
        len(parts) == 2
        and upper_code in US_STATE_ABBREVIATIONS
    ):
        return None


    # -----------------------------------------
    # THREE-PART ATS LOCATION
    # -----------------------------------------
    #
    # Montreal, QC, ca
    # Atlanta, GA, us
    #
    # By this point explicit "United States"
    # wording has already been handled above.

    if len(parts) >= 3:
        return code


    # -----------------------------------------
    # OTHER TWO-LETTER COUNTRY CODES
    # -----------------------------------------
    #
    # Saint-Mandé, fr
    # London, uk

    return code


def contains_us_state_name(location):

    location = normalize(
        location
    )

    for state in US_STATE_NAMES:

        if state in location:
            return True

    return False


def contains_us_state_abbreviation(location):
    """
    Examples:

        San Francisco, CA
        Redmond, WA
        Raleigh, NC
        United States, San Diego, CA
        US-CA

    But NOT:

        Montreal, QC, ca
    """

    original_location = (
        location or ""
    ).strip()


    # -----------------------------------------
    # EXPLICIT UNITED STATES TEXT
    # -----------------------------------------

    if contains_us_country_marker(
        original_location
    ):
        return True


    # -----------------------------------------
    # COUNTRY CODE SAFETY CHECK
    # -----------------------------------------

    country_code = get_explicit_country_code(
        original_location
    )

    if (
        country_code
        and country_code != "us"
    ):
        return False


    upper_location = (
        original_location.upper()
    )


    # -----------------------------------------
    # CITY, STATE
    # -----------------------------------------

    comma_pattern = re.compile(
        r",\s*("
        + "|".join(US_STATE_ABBREVIATIONS)
        + r")"
        r"(?:\s*$|\s*,\s*US\s*$|\s*,\s*USA\s*$)"
    )

    if comma_pattern.search(
        upper_location
    ):
        return True


    # -----------------------------------------
    # WORKDAY-STYLE STATE FORMAT
    # -----------------------------------------
    #
    # US-CA
    # US_CA
    # US/CA
    # US CA

    workday_pattern = re.compile(
        r"\bUS[-_/ ]("
        + "|".join(US_STATE_ABBREVIATIONS)
        + r")\b"
    )

    if workday_pattern.search(
        upper_location
    ):
        return True


    return False


def contains_us_city_marker(location):

    location = normalize(
        location
    )

    for city in US_CITY_MARKERS:

        if city in location:
            return True

    return False


def location_matches(
    job,
    allowed_locations=None
):

    original_location = (
        job.get(
            "location",
            ""
        )
        or ""
    ).strip()

    if not original_location:
        return False

    location = normalize(
        original_location
    )


    # -----------------------------------------
    # EXPLICIT UNITED STATES MARKERS
    # -----------------------------------------
    #
    # Check this FIRST.
    #
    # This prevents:
    #
    # United States, San Diego, CA
    #
    # from being interpreted as Canada because
    # the final token happens to be "CA".

    if contains_us_country_marker(
        original_location
    ):
        return True


    # -----------------------------------------
    # EXPLICIT NON-US COUNTRY
    # -----------------------------------------

    if contains_non_us_country_marker(
        original_location
    ):
        return False


    # -----------------------------------------
    # EXPLICIT ATS COUNTRY CODE
    # -----------------------------------------

    country_code = get_explicit_country_code(
        original_location
    )

    if country_code == "us":
        return True

    if (
        country_code
        and country_code != "us"
    ):
        return False


    # -----------------------------------------
    # FULL US STATE NAMES
    # -----------------------------------------

    if contains_us_state_name(
        original_location
    ):
        return True


    # -----------------------------------------
    # US STATE ABBREVIATIONS
    # -----------------------------------------

    if contains_us_state_abbreviation(
        original_location
    ):
        return True


    # -----------------------------------------
    # KNOWN US CITY / METRO NAMES
    # -----------------------------------------

    if contains_us_city_marker(
        original_location
    ):
        return True


    # -----------------------------------------
    # USER-CONFIGURED LOCATIONS
    # -----------------------------------------

    allowed_locations = (
        allowed_locations
        or []
    )

    for allowed in allowed_locations:

        allowed = normalize(
            allowed
        )

        if (
            allowed
            and allowed in location
        ):
            return True


    return False