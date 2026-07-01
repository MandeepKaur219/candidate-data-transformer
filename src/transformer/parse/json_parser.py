"""Parser for ATS JSON blobs.

ATS field names are assumed NOT to match our canonical names (per the
assignment). Rather than hardcode a guess at the ATS's exact schema, this
parser flattens arbitrary nested JSON objects into dot-path keys (e.g.
"contact.email", "candidate.full_name") and leaves lists (skills,
work_history, education, etc.) intact as single values. The Mapper stage
is then responsible for translating whatever dot-paths the real ATS uses
into canonical fields, via a configurable field-name map -- this parser
just makes the structure addressable.
"""

from typing import Any, Dict, List

from transformer.parse.base import ParsedValue, Parser

# Semi-structured: field names are reliable once flattened, but the schema
# itself is foreign, so this sits slightly below CSV's direct-field trust.
_DIRECT_FIELD_CONFIDENCE = 0.90


def _flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """Recursively flattens nested dicts into dot-path keys.

    Lists are NOT recursed into -- they are kept as-is so that list-shaped
    fields (skills, work_history, education) remain available to the
    Mapper as a single structured value rather than being shredded into
    unusable indexed keys.
    """
    flat: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                flat.update(_flatten(value, path))
            else:
                flat[path] = value
    return flat


class JsonParser(Parser):
    """Parses ATS JSON candidate blobs into flattened ParsedValue dicts."""

    source_name = "ats_json"

    def parse(self, raw: Any) -> List[Dict[str, ParsedValue]]:
        if not raw:
            return []

        records: List[Dict[str, ParsedValue]] = []
        for candidate_obj in raw:
            if not isinstance(candidate_obj, dict):
                continue
            flat = _flatten(candidate_obj)
            record: Dict[str, ParsedValue] = {}
            for key, value in flat.items():
                if value is None or value == "" or value == []:
                    continue
                record[key.lower()] = ParsedValue(
                    value=value,
                    method="direct_field",
                    confidence=_DIRECT_FIELD_CONFIDENCE,
                )
            if record:
                records.append(record)
        return records