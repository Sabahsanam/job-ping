import re


def normalize(text):
    return (text or "").lower().strip()


def get_all_job_keywords(config):
    keywords = []

    for category_keywords in config.get(
        "job_categories",
        {}
    ).values():

        keywords.extend(
            category_keywords
        )

    return keywords


def contains_excluded_keyword(
    title,
    excluded_keywords
):
    title = normalize(title)

    for excluded in excluded_keywords:

        excluded = normalize(
            excluded
        )

        if excluded and excluded in title:
            return True

    return False


def has_excluded_seniority(title):
    """
    Catch seniority patterns that companies express
    in different ways.

    We allow Level I and II for now.

    We reject:
    III, IV, V, VI, etc.
    Engineer 3, Engineer 4, etc.
    Level 3+, L3+, Advanced, and similar signals.
    """

    title = normalize(title)


    # --------------------------------------------
    # ROMAN NUMERAL LEVELS
    # --------------------------------------------
    #
    # Examples:
    # Software Engineer III
    # Developer IV
    # Analyst V

    roman_level_pattern = (
        r"\b(?:engineer|developer|analyst|scientist|"
        r"architect|designer|programmer|specialist)"
        r"\s+(?:iii|iv|v|vi|vii|viii|ix|x)\b"
    )

    if re.search(
        roman_level_pattern,
        title,
        re.IGNORECASE
    ):
        return True


    # --------------------------------------------
    # NUMERIC LEVELS AFTER ROLE
    # --------------------------------------------
    #
    # Examples:
    # Software Engineer 3
    # Engineer 4
    # Developer 5

    numeric_role_level_pattern = (
        r"\b(?:engineer|developer|analyst|scientist|"
        r"architect|designer|programmer|specialist)"
        r"\s+([3-9]|[1-9][0-9])\b"
    )

    if re.search(
        numeric_role_level_pattern,
        title,
        re.IGNORECASE
    ):
        return True


    # --------------------------------------------
    # EXPLICIT LEVEL
    # --------------------------------------------
    #
    # Examples:
    # Level 3 Software Engineer
    # Level 4 Developer

    explicit_level_pattern = (
        r"\blevel\s*([3-9]|[1-9][0-9])\b"
    )

    if re.search(
        explicit_level_pattern,
        title,
        re.IGNORECASE
    ):
        return True


    # --------------------------------------------
    # L-LEVELS
    # --------------------------------------------
    #
    # Examples:
    # L3
    # L4 Software Engineer
    # L5 Engineer

    l_level_pattern = (
        r"\bl\s*([3-9]|[1-9][0-9])\b"
    )

    if re.search(
        l_level_pattern,
        title,
        re.IGNORECASE
    ):
        return True


    # --------------------------------------------
    # ADVANCED
    # --------------------------------------------

    if re.search(
        r"\badvanced\b",
        title,
        re.IGNORECASE
    ):
        return True


    return False


def is_test_or_qa_role(title):
    """
    Reject dedicated QA / software testing jobs.

    Avoid rejecting normal engineering jobs merely
    because their descriptions mention testing.
    This only examines the JOB TITLE.
    """

    title = normalize(title)

    patterns = [
        r"\bdeveloper\s+in\s+test\b",
        r"\bsoftware\s+development\s+engineer\s+in\s+test\b",
        r"\bsdet\b",
        r"\bqa\b",
        r"\bquality\s+assurance\b",
        r"\bquality\s+engineer\b",
        r"\btest\s+engineer\b",
        r"\btesting\s+engineer\b",
        r"\btest\s+automation\b",
        r"\bautomation\s+test\b"
    ]

    for pattern in patterns:

        if re.search(
            pattern,
            title,
            re.IGNORECASE
        ):
            return True

    return False


def matches_job(job, config):

    title = normalize(
        job.get(
            "title",
            ""
        )
    )

    if not title:
        return False


    # --------------------------------------------
    # USER CONFIG EXCLUSIONS
    # --------------------------------------------

    excluded_keywords = config.get(
        "excluded_keywords",
        []
    )

    if contains_excluded_keyword(
        title,
        excluded_keywords
    ):
        return False


    # --------------------------------------------
    # GENERAL SENIORITY PROTECTION
    # --------------------------------------------

    if has_excluded_seniority(
        title
    ):
        return False


    # --------------------------------------------
    # QA / TEST ROLE PROTECTION
    # --------------------------------------------

    if is_test_or_qa_role(
        title
    ):
        return False


    # --------------------------------------------
    # DESIRED JOB CATEGORIES
    # --------------------------------------------

    job_keywords = get_all_job_keywords(
        config
    )

    for keyword in job_keywords:

        keyword = normalize(
            keyword
        )

        if keyword and keyword in title:
            return True


    return False