import re
from datetime import datetime
from typing import Optional, Tuple

from dateutil import parser as dateparser

from .preprocessing import extract_section, clamp01


MONTHS = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_TOKEN = rf"({MONTHS}\s*\d{{4}}|\d{{4}}|\d{{1,2}}/\d{{4}})"

EXPLICIT_YEARS_RE = re.compile(
    r"(?<![a-z0-9_])(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

RANGE_RE = re.compile(
    rf"(?P<start>{DATE_TOKEN})\s*(?:to|-)\s*(?P<end>current|present|now|{DATE_TOKEN})",
    re.IGNORECASE,
)


def _parse_date(token: str) -> Optional[datetime]:
    try:
        # Use fuzzy parsing; set a stable default day to reduce variability.
        return dateparser.parse(token.strip(), fuzzy=True, default=datetime(1900, 1, 1))
    except Exception:
        return None


def extract_experience_years(text: Optional[str]) -> Tuple[Optional[float], float]:
    """
    Extract experience years from resume text.

    Returns:
      (years_or_none, confidence_0_to_1)

    Important: returns None when unknown to avoid biasing scores.
    """
    if text is None:
        return None, 0.0

    raw = str(text)

    section = extract_section(
        raw,
        headers=["Experience", "Work Experience", "Work History", "Professional Experience", "EXPERIENCE", "WORK EXPERIENCE"],
    )
    search_text = section if section.strip() else raw

    # Strategy 1: explicit "X+ years"
    m = EXPLICIT_YEARS_RE.search(search_text)
    if m:
        years = float(m.group("years"))
        if 0 < years < 80:
            return years, 1.0

    # Strategy 2: sum date ranges
    ranges = list(RANGE_RE.finditer(search_text))
    if ranges:
        total_years = 0.0
        for r in ranges:
            start_str = r.group("start")
            end_str = r.group("end")

            start_dt = _parse_date(start_str)
            if not start_dt:
                continue

            if re.search(r"(current|present|now)", end_str, re.IGNORECASE):
                end_dt = datetime.now()
            else:
                end_dt = _parse_date(end_str)
            if not end_dt:
                continue

            diff_days = (end_dt - start_dt).days
            if diff_days > 0:
                total_years += diff_days / 365.25

        if total_years > 0:
            # Cap to reasonable range
            total_years = min(total_years, 80.0)
            return round(total_years, 1), 0.7

    # Strategy 3: fallback scan whole resume for any explicit years.
    m2 = EXPLICIT_YEARS_RE.search(raw)
    if m2:
        years = float(m2.group("years"))
        if 0 < years < 80:
            return years, 0.4

    return None, 0.0


def extract_required_experience_years(job_description: Optional[str]) -> Optional[float]:
    """
    Extract required experience from job description.
    Returns None if not found.
    """
    if job_description is None:
        return None

    jd = str(job_description)

    # Common patterns: "5+ years", "at least 4 years", "minimum 3 yrs"
    m = re.search(
        r"(?i)\b(?:at\s+least|min(?:imum)?|required)?\s*(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        jd,
    )
    if m:
        years = float(m.group("years"))
        if 0 < years < 80:
            return years
    return None

