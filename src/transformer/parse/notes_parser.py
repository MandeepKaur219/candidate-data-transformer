"""Parser for free-form recruiter notes (.txt).

Recruiter notes are unstructured prose written by a human about a specific
candidate, e.g. "Spoke with Jane Doe (jane@example.com, 555-123-4567)
about the Senior Backend role. Strong in Python and distributed systems,
~6 yrs experience. Currently at Globex." There is no schema to key off of,
so extraction here is regex/heuristic and gets a correspondingly lower
confidence than a structured direct-field read.
"""

import re
from typing import Any, Dict, List

from transformer.parse.base import ParsedValue, Parser

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d().\s-]{7,}\d)")
_NAME_RE = re.compile(
    r"(?:Candidate|Spoke with|Re|Regarding)\s*[:\-]?\s*([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+)+)"
)
_COMPANY_RE = re.compile(
    r"(?:currently at|works at|employed at)\s+([A-Z][\w&.,'\- ]+?)(?:[.,;\n]|$)",
    re.IGNORECASE,
)
_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs?)\b", re.IGNORECASE)

_REGEX_EXTRACTION_CONFIDENCE = 0.65
_HEURISTIC_CONFIDENCE = 0.50


class NotesParser(Parser):
    """Parses recruiter notes text into heuristically extracted fields."""

    source_name = "recruiter_notes"

    def parse(self, raw: Any) -> List[Dict[str, ParsedValue]]:
        if not raw or not isinstance(raw, str):
            return []

        text = raw
        record: Dict[str, ParsedValue] = {}

        email_match = _EMAIL_RE.search(text)
        if email_match:
            record["email"] = ParsedValue(
                value=email_match.group(0),
                method="regex_extraction",
                confidence=_REGEX_EXTRACTION_CONFIDENCE,
            )

        phone_match = _PHONE_RE.search(text)
        if phone_match:
            record["phone"] = ParsedValue(
                value=phone_match.group(0),
                method="regex_extraction",
                confidence=_REGEX_EXTRACTION_CONFIDENCE,
            )

        name_match = _NAME_RE.search(text)
        if name_match:
            record["full_name"] = ParsedValue(
                value=name_match.group(1).strip(),
                method="heuristic_parse",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        company_match = _COMPANY_RE.search(text)
        if company_match:
            record["current_company"] = ParsedValue(
                value=company_match.group(1).strip(),
                method="heuristic_parse",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        years_match = _YEARS_RE.search(text)
        if years_match:
            record["years_experience"] = ParsedValue(
                value=years_match.group(1),
                method="regex_extraction",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        # The full note text is kept as a low-confidence summary/headline
        # candidate -- useful context even when nothing else matched.
        record["notes_summary"] = ParsedValue(
            value=text.strip(),
            method="raw_text",
            confidence=_HEURISTIC_CONFIDENCE,
        )

        return [record] if record else []