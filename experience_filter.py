import re


QUALITATIVE_SENIOR_EXPERIENCE_PHRASES = [
    "significant professional software development experience",
    "significant professional experience",
    "significant industry experience",
    "extensive professional experience",
    "extensive industry experience",
    "substantial professional experience",
    "substantial industry experience"
]


def normalize(text):
    return (text or "").lower().strip()


def experience_matches(job, early_career_indicators):
    title = normalize(job.get("title", ""))
    description = normalize(job.get("description", ""))

    # ------------------------------------------------
    # 1. TITLE EXPERIENCE IS VERY RELIABLE
    # ------------------------------------------------

    # Examples:
    # Software Developer (3 - 5 Years of Experience)
    # Engineer - 5+ Years Experience

    title_range_patterns = [
        r"\b(\d+)\s*[-–—]\s*(\d+)\s+years?\b",
        r"\b(\d+)\s+to\s+(\d+)\s+years?\b"
    ]

    for pattern in title_range_patterns:
        matches = re.findall(
            pattern,
            title,
            re.IGNORECASE
        )

        for minimum, maximum in matches:
            if int(minimum) >= 3:
                return False


    title_plus_pattern = (
        r"\b(\d+)\s*\+\s*years?"
    )

    for years in re.findall(
        title_plus_pattern,
        title,
        re.IGNORECASE
    ):
        if int(years) >= 3:
            return False


    # ------------------------------------------------
    # 2. STRONG EARLY-CAREER TITLE SIGNALS
    # ------------------------------------------------

    # If the title explicitly says New Grad,
    # Entry Level, Early Career, etc., keep it unless
    # the title itself already contained a conflicting
    # experience requirement above.

    for indicator in early_career_indicators:

        indicator = normalize(
            indicator
        )

        if (
            indicator
            and indicator in title
        ):
            return True


    # ------------------------------------------------
    # 3. DESCRIPTION EXPERIENCE REQUIREMENTS
    # ------------------------------------------------

    # Only reject when experience is clearly presented
    # as an actual requirement.
    #
    # Examples:
    #
    # minimum of 5 years
    # requires 4 years
    # 5+ years required
    # must have 6 years
    # at least 3 years

    requirement_patterns = [
        r"minimum(?: of)?\s+(\d+)\s*\+?\s*years?",
        r"at least\s+(\d+)\s*\+?\s*years?",
        r"requires?\s+(?:at least\s+)?(\d+)\s*\+?\s*years?",
        r"required[:\s]+(?:.*?)(\d+)\s*\+?\s*years?",
        r"must have\s+(?:at least\s+)?(\d+)\s*\+?\s*years?",
        r"must possess\s+(?:at least\s+)?(\d+)\s*\+?\s*years?",
        r"(\d+)\s*\+\s*years?[^.\n]{0,50}\brequired\b",
        r"(\d+)\s+years?[^.\n]{0,50}\brequired\b"
    ]

    for pattern in requirement_patterns:

        matches = re.findall(
            pattern,
            description,
            re.IGNORECASE
        )

        for years in matches:

            if int(years) >= 3:
                return False


    # ------------------------------------------------
    # 4. STRONG QUALITATIVE EXPERIENCE REQUIREMENTS
    # ------------------------------------------------

    # Some companies do not specify a number of years.
    #
    # Valve, for example, may say:
    #
    # "significant professional software development
    # experience"
    #
    # These phrases are strong enough to indicate that
    # the role is not intended to be early career.
    #
    # IMPORTANT:
    # We intentionally do NOT reject generic words like:
    #
    # experience
    # expertise
    # professional
    # industry
    # shipped
    #
    # because those would remove too many valid jobs.

    for phrase in QUALITATIVE_SENIOR_EXPERIENCE_PHRASES:

        if phrase in description:
            return False


    # ------------------------------------------------
    # 5. OTHERWISE KEEP THE JOB
    # ------------------------------------------------

    # If we're uncertain, we'd rather show the role
    # than accidentally hide a good early-career job.

    return True