"""Generic text normalization: whitespace and case.

These are the low-level utilities other normalizers (and the mapper's
downstream consumers) reach for whenever a value just needs to be made
consistent, not semantically transformed.
"""

import re
import unicodedata
from typing import Optional

_WHITESPACE_RE = re.compile(r"\s+")


def collapse_whitespace(raw: Optional[str]) -> Optional[str]:
    """Trims and collapses any run of internal whitespace to a single space."""
    if raw is None:
        return None
    cleaned = _WHITESPACE_RE.sub(" ", raw).strip()
    return cleaned if cleaned else None


def normalize_unicode(raw: Optional[str]) -> Optional[str]:
    """Applies NFKC normalization so visually-identical strings compare equal."""
    if raw is None:
        return None
    return unicodedata.normalize("NFKC", raw)


def title_case_name(raw: Optional[str]) -> Optional[str]:
    """
    Title-cases a person/company name conservatively: capitalizes each
    whitespace-separated word's first letter while leaving the rest of the
    word untouched, so existing intentional casing (e.g. "McDonald",
    "O'Brien", "iOS") is not clobbered the way str.title() would clobber it.
    """
    cleaned = collapse_whitespace(raw)
    if cleaned is None:
        return None
    words = []
    for word in cleaned.split(" "):
        if word and word[0].isalpha() and word[0].islower():
            word = word[0].upper() + word[1:]
        words.append(word)
    return " ".join(words)


def clean_text(raw: Optional[str]) -> Optional[str]:
    """Applies the standard pipeline: unicode-normalize then collapse whitespace."""
    return collapse_whitespace(normalize_unicode(raw))