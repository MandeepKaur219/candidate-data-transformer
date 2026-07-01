"""Parser for recruiter CSV rows."""

from typing import Any, Dict, List

from transformer.parse.base import ParsedValue, Parser

# Structured, direct-field extraction is the most trustworthy method we
# have, so it gets a high base confidence. Actual per-field confidence may
# still be lowered later (e.g. by the normalizer if a value fails to
# normalize cleanly).
_DIRECT_FIELD_CONFIDENCE = 0.95


class CsvParser(Parser):
    """Parses recruiter CSV rows: name, email, phone, current_company, title."""

    source_name = "recruiter_csv"

    def parse(self, raw: Any) -> List[Dict[str, ParsedValue]]:
        if not raw:
            return []

        records: List[Dict[str, ParsedValue]] = []
        for row in raw:
            record: Dict[str, ParsedValue] = {}
            for key, value in row.items():
                if value is None:
                    continue
                cleaned = value.strip()
                if not cleaned:
                    continue
                record[key.strip().lower()] = ParsedValue(
                    value=cleaned,
                    method="direct_field",
                    confidence=_DIRECT_FIELD_CONFIDENCE,
                )
            if record:
                records.append(record)
        return records