"""
Field mapper.

"Map" is the single stage responsible for translating a source's own field
names (e.g. CSV's "name", ATS JSON's "contact.email") into canonical field
names (e.g. "full_name", "emails"). The rename table comes entirely from
config -- this class contains zero hardcoded source field names, so a new
ATS schema is a config change, never a code change.

Output groups ParsedValues by canonical field name (a list, even for
scalar-typed canonical fields) because more than one source field can
legitimately map to the same canonical field (e.g. both "email" and
"contact.primary_email" -> "emails"). Folding that list down to the right
shape (single scalar vs. deduplicated list) is the Normalizer's job, since
that requires schema-shape knowledge (LIST_FIELDS) the Mapper deliberately
doesn't need.
"""

from typing import Dict, List

from transformer.parse.base import ParsedValue


class FieldMapper:
    """Renames one source's parsed fields into canonical field names."""

    def __init__(self, field_map: Dict[str, str]):
        """
        Args:
            field_map: Maps source-specific field name -> canonical field
                name, loaded from config/pipeline_config.json for this
                source. Lookups are case-insensitive.
        """
        self._field_map = {k.lower(): v for k, v in field_map.items()}

    def map_record(
        self, parsed_record: Dict[str, ParsedValue]
    ) -> Dict[str, List[ParsedValue]]:
        """
        Renames a single parsed record's keys to canonical field names.

        Source fields with no entry in the field map are dropped (we never
        invent a canonical meaning for an unknown field) rather than
        passed through, which keeps unmapped/unexpected source columns
        from silently leaking into the canonical schema.
        """
        mapped: Dict[str, List[ParsedValue]] = {}
        for source_key, parsed_value in parsed_record.items():
            canonical_key = self._field_map.get(source_key.lower())
            if canonical_key is None:
                continue
            mapped.setdefault(canonical_key, []).append(parsed_value)
        return mapped