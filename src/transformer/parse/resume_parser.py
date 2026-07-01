"""Parser for resume text extracted from PDF.

Resumes are semi-structured prose: there is usually a name near the top, a
contact line with email/phone, and loosely-labeled sections like "Skills"
and "Experience". This parser uses line-based heuristics rather than a
full NLP pipeline -- good enough to be useful, honest about being
approximate via its confidence scores.
"""

import re
from typing import Any, Dict, List

from transformer.parse.base import ParsedValue, Parser

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d().\s-]{7,}\d)")
_SECTION_HEADERS = {"skills", "experience", "work experience", "education"}
_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs?)\b", re.IGNORECASE)

_REGEX_EXTRACTION_CONFIDENCE = 0.70
_HEURISTIC_CONFIDENCE = 0.55


def _find_section(lines: List[str], header: str) -> List[str]:
    """Returns the lines belonging to a labeled section, e.g. 'Skills'."""
    collected: List[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower().rstrip(":")
        if lowered == header:
            in_section = True
            continue
        if in_section:
            if lowered in _SECTION_HEADERS:
                break
            if stripped:
                collected.append(stripped)
    return collected


class ResumeParser(Parser):
    """Parses resume PDF text into heuristically extracted fields."""

    source_name = "resume_pdf"

    def parse(self, raw: Any) -> List[Dict[str, ParsedValue]]:
        if not raw or not isinstance(raw, str):
            return []

        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if not lines:
            return []

        record: Dict[str, ParsedValue] = {}

        # Heuristic: the first non-empty line of a resume is almost always
        # the candidate's name (no labeled "Name:" field to key off of).
        first_line = lines[0].strip()
        if first_line and len(first_line.split()) <= 5 and "@" not in first_line:
            record["full_name"] = ParsedValue(
                value=first_line,
                method="heuristic_parse",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        email_match = _EMAIL_RE.search(raw)
        if email_match:
            record["email"] = ParsedValue(
                value=email_match.group(0),
                method="regex_extraction",
                confidence=_REGEX_EXTRACTION_CONFIDENCE,
            )

        phone_match = _PHONE_RE.search(raw)
        if phone_match:
            record["phone"] = ParsedValue(
                value=phone_match.group(0),
                method="regex_extraction",
                confidence=_REGEX_EXTRACTION_CONFIDENCE,
            )

        years_match = _YEARS_RE.search(raw)
        if years_match:
            record["years_experience"] = ParsedValue(
                value=years_match.group(1),
                method="regex_extraction",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        skills_lines = _find_section(lines, "skills")
        if skills_lines:
            # Skills are typically comma/pipe/bullet separated; split on
            # common delimiters and let the skill normalizer canonicalize.
            raw_skills = re.split(r"[,|•\u2022]", " ".join(skills_lines))
            skill_names = [s.strip() for s in raw_skills if s.strip()]
            if skill_names:
                record["skills"] = ParsedValue(
                    value=skill_names,
                    method="heuristic_parse",
                    confidence=_HEURISTIC_CONFIDENCE,
                )

        experience_lines = _find_section(lines, "experience") or _find_section(
            lines, "work experience"
        )
        if experience_lines:
            record["experience_text"] = ParsedValue(
                value="\n".join(experience_lines),
                method="heuristic_parse",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        education_lines = _find_section(lines, "education")
        if education_lines:
            record["education_text"] = ParsedValue(
                value="\n".join(education_lines),
                method="heuristic_parse",
                confidence=_HEURISTIC_CONFIDENCE,
            )

        return [record] if record else []