import re
import html
from typing import Iterable, Optional


# Preserve key tech symbols commonly found in resumes.
# We intentionally keep: + # . - / & ( )
_PRESERVE_SYMBOLS_RE = r"\+\#\.\-/&\(\)"


def normalize_text_preserve_tech(text: Optional[str]) -> str:
    """
    Normalize text for matching while preserving important tech symbols.

    Examples preserved:
    - C++ -> c++
    - C#  -> c#
    - .NET -> .net
    """
    if text is None:
        return ""

    text = html.unescape(str(text))
    text = text.lower()

    # Replace most punctuation with spaces, but preserve tech symbols.
    text = re.sub(rf"[^a-z0-9\s{_PRESERVE_SYMBOLS_RE}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _escape_headers(headers: Iterable[str]) -> list[str]:
    return [re.escape(h.strip()) for h in headers if h and str(h).strip()]


def extract_section(text: Optional[str], headers: Iterable[str]) -> str:
    """
    Extract a section (case-insensitive) from resume-like text by header markers.

    Heuristic:
    - Find a header line, then return content until the next header-looking line
      or end of text.
    """
    if text is None:
        return ""

    raw = str(text)
    escaped_headers = _escape_headers(headers)
    if not escaped_headers:
        return ""

    header_alt = "|".join(escaped_headers)

    # Stop when we reach another "header-like" line (CAPS-ish + 3+ chars) followed by ":" or whitespace.
    # Works for many resume formats: "EXPERIENCE:", "Work History", "TECHNICAL SKILLS"
    pattern = rf"(?is)(?:^|\n)\s*(?:{header_alt})\s*:?\s*(.*?)\s*(?=\n\s*[A-Z][A-Z\s]{{3,}}\s*:|\Z)"
    m = re.search(pattern, raw)
    if not m:
        return ""
    return m.group(1) or ""


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

