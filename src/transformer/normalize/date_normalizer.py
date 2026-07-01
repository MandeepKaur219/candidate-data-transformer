"""Date normalization.

Normalizes free-form dates ("Jan 2020", "2020-01-15", "March 2019") into
the canonical "YYYY-MM" format the schema requires for experience/education
dates. Uses `python-dateutil`'s fuzzy parser rather than a hand-written set
of format strings, since resumes and recruiter notes write dates in too
many inconsistent ways to enumerate by hand.
"""

import re
from datetime import datetime
from typing import Optional

from dateutil import parser as dateutil_parser

_ONGOING_TERMS = {"present", "current", "currently", "now", "ongoing", "to date"}

# dateutil requires a real, valid default datetime to fill in any date
# components missing from the input (e.g. "March 2019" has no day). A
# fixed anchor -- rather than datetime.now() -- keeps parsing deterministic:
# the result never depends on what day the pipeline happens to be run.
_ANCHOR = datetime(2000, 1, 1)

_YEAR_ONLY_RE = re.compile(r"^\d{4}$")


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """
    Returns a "YYYY-MM" string, or None if `raw` is missing, means an
    ongoing/"present" date, or cannot be parsed.

    An ongoing date (e.g. an experience entry's `end` field reading
    "Present") is deliberately normalized to None rather than today's
    date, so the output stays identical no matter what day this is run.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.lower() in _ONGOING_TERMS:
        return None

    try:
        parsed = dateutil_parser.parse(text, default=_ANCHOR, fuzzy=True)
    except (ValueError, OverflowError):
        return None

    return f"{parsed.year:04d}-{parsed.month:02d}"


def normalize_year(raw: Optional[str]) -> Optional[int]:
    """Parses a bare 4-digit year (used for education end_year)."""
    if raw is None:
        return None
    text = raw.strip()
    if _YEAR_ONLY_RE.match(text):
        return int(text)
    normalized = normalize_date(text)
    if normalized:
        return int(normalized.split("-")[0])
    return None