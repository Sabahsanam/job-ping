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
    # 1. TITLE EXPERIENCE REQUIREMENTS
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
    # 2. DESCRIPTION EXPERIENCE REQUIREMENTS
    # ------------------------------------------------

    # IMPORTANT:
    #
    # We check the description BEFORE accepting
    # early-career title signals.
    #
    # A title like "Software Engineer II" or even
    # "Early Career Engineer" should not pass if the
    # actual job description clearly requires 4+ years.


    # ------------------------------------------------
    # 2A. Direct numeric experience phrases
    # ------------------------------------------------

    # Examples:
    #
    # 4+ years of experience
    # 4+ years of relevant experience
    # 3+ years professional experience
    # 5 years of software engineering experience
    # 3-5 years of experience
    # 3 to 5 years of relevant experience

    direct_experience_patterns = [
        (
            r"\b(\d+)\s*\+\s*years?"
            r"(?:\s+of)?"
            r"(?:\s+[a-zA-Z/&,\-]+){0,6}"
            r"\s+experience\b"
        ),

        (
            r"\b(\d+)\s+years?"
            r"(?:\s+of)?"
            r"(?:\s+[a-zA-Z/&,\-]+){0,6}"
            r"\s+experience\b"
        ),

        (
            r"\b(\d+)\s*[-–—]\s*(\d+)\s+years?"
            r"(?:\s+of)?"
            r"(?:\s+[a-zA-Z/&,\-]+){0,6}"
            r"\s+experience\b"
        ),

        (
            r"\b(\d+)\s+to\s+(\d+)\s+years?"
            r"(?:\s+of)?"
            r"(?:\s+[a-zA-Z/&,\-]+){0,6}"
            r"\s+experience\b"
        )
    ]


    # Single-number patterns
    for pattern in direct_experience_patterns[:2]:

        matches = re.findall(
            pattern,
            description,
            re.IGNORECASE
        )

        for years in matches:
            if int(years) >= 3:
                return False


    # Range patterns
    for pattern in direct_experience_patterns[2:]:

        matches = re.findall(
            pattern,
            description,
            re.IGNORECASE
        )

        for minimum, maximum in matches:
            if int(minimum) >= 3:
                return False


    # ------------------------------------------------
    # 2B. Explicit requirement wording
    # ------------------------------------------------

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
        r"(\d+)\s*\+\s*years?[^.\n]{0,75}\brequired\b",
        r"(\d+)\s+years?[^.\n]{0,75}\brequired\b"
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
    # 3. STRONG QUALITATIVE EXPERIENCE REQUIREMENTS
    # ------------------------------------------------

    for phrase in QUALITATIVE_SENIOR_EXPERIENCE_PHRASES:

        if phrase in description:
            return False


    # ------------------------------------------------
    # 4. STRONG EARLY-CAREER TITLE SIGNALS
    # ------------------------------------------------

    # Only accept the early-career title AFTER checking
    # that the description doesn't contradict it.

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
    # 5. OTHERWISE KEEP THE JOB
    # ------------------------------------------------

    # If we found no explicit 3+ year requirement,
    # keep the role rather than hiding a potentially
    # useful early-career opportunity.

    return True