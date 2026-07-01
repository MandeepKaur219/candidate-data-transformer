"""
Projector.

Converts a merged, scored CandidateRecord (the internal canonical truth)
into the JSON shape actually returned to the caller. Two modes:

  - Default mode (no "fields" in config): emits the full default output
    schema from the assignment PDF (candidate_id, full_name, emails,
    phones, location, links, headline, years_experience, skills,
    experience, education, provenance, overall_confidence).

  - Custom-projection mode (config has a "fields" list): emits only the
    requested fields, each resolved from the default profile via a
    dot/bracket "from" path, with per-field or global on_missing policy
    (null | omit | error) and optional output normalization hints.

Keeping a clean separation between the internal canonical record and this
projection layer (per the assignment's explicit instruction) means the
internal model never has to know about any specific requested output
shape -- it is always projected, never directly serialized.
"""

import re
from typing import Any, Dict, List, Optional

from transformer.models.canonical import CandidateRecord, EducationEntry, ExperienceEntry
from transformer.normalize.phone_normalizer import normalize_phone
from transformer.provenance.tracker import ProvenanceTracker

_PATH_SEGMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(\[(\d+)\])?$")


class ProjectionError(Exception):
    """Raised when a field configured as required is missing and the
    effective on_missing policy is 'error'."""


def _resolve_simple(data: Any, path: str) -> Any:
    current = data
    for segment in path.split("."):
        match = _PATH_SEGMENT_RE.match(segment)
        if not match:
            return None
        key, _, idx = match.groups()
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
        if idx is not None:
            if isinstance(current, list) and int(idx) < len(current):
                current = current[int(idx)]
            else:
                return None
    return current


def _resolve_path(data: Dict[str, Any], path: str) -> Any:
    """Resolves a "from" path like "emails[0]" or "skills[].name" against
    the default profile dict."""
    if "[]." in path:
        list_key, sub_path = path.split("[].", 1)
        items = data.get(list_key)
        if not isinstance(items, list):
            return None
        return [_resolve_simple(item, sub_path) for item in items]
    return _resolve_simple(data, path)


def _is_empty(value: Any) -> bool:
    return value is None or value == [] or value == {}


def _prune_empty(data: Any) -> Any:
    """Recursively removes keys whose value is None/[]/{} (used when
    include_empty_fields is False)."""
    if isinstance(data, dict):
        pruned = {k: _prune_empty(v) for k, v in data.items()}
        return {k: v for k, v in pruned.items() if not _is_empty(v)}
    if isinstance(data, list):
        return [_prune_empty(v) for v in data]
    return data


class Projector:
    """Projects a canonical CandidateRecord into the requested output shape."""

    def __init__(self, provenance_tracker: Optional[ProvenanceTracker] = None):
        self._provenance_tracker = provenance_tracker or ProvenanceTracker()

    def project(
        self, record: CandidateRecord, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        config = config or {}
        include_confidence = config.get("include_confidence", True)
        include_provenance = config.get("include_provenance", True)
        include_empty_fields = config.get("include_empty_fields", True)

        if "fields" not in config:
            return self.to_default_profile(
                record, include_confidence, include_provenance, include_empty_fields
            )

        # Build the full internal default profile (everything present) as
        # the resolution source for custom "from" paths, independent of
        # what the final output toggles request.
        full_profile = self.to_default_profile(record, True, True, True)
        default_on_missing = config.get("on_missing", "null")

        output: Dict[str, Any] = {}
        for field_spec in config["fields"]:
            path = field_spec["path"]
            from_path = field_spec.get("from", path)
            value = _resolve_path(full_profile, from_path)
            value = self._apply_output_normalize(value, field_spec.get("normalize"))

            if _is_empty(value):
                required = field_spec.get("required", False)
                policy = "error" if required else field_spec.get("on_missing", default_on_missing)
                if policy == "error":
                    raise ProjectionError(f"Required field '{path}' is missing")
                if policy == "omit":
                    continue
                output[path] = None
            else:
                output[path] = value

        if include_confidence and "overall_confidence" not in output:
            output["overall_confidence"] = full_profile["overall_confidence"]
        if include_provenance and "provenance" not in output:
            output["provenance"] = full_profile["provenance"]

        return _prune_empty(output) if not include_empty_fields else output

    def to_default_profile(
        self,
        record: CandidateRecord,
        include_confidence: bool,
        include_provenance: bool,
        include_empty_fields: bool,
    ) -> Dict[str, Any]:
        """Builds the full default output schema dict for `record`."""
        profile: Dict[str, Any] = {
            "candidate_id": record.candidate_id,
            "full_name": record.full_name.value if record.full_name else None,
            "emails": [fv.value for fv in record.emails],
            "phones": [fv.value for fv in record.phones],
            "location": {
                "city": record.location_city.value if record.location_city else None,
                "region": record.location_region.value if record.location_region else None,
                "country": record.location_country.value if record.location_country else None,
            },
            "links": {
                "linkedin": record.links_linkedin.value if record.links_linkedin else None,
                "github": record.links_github.value if record.links_github else None,
                "portfolio": record.links_portfolio.value if record.links_portfolio else None,
                "other": [fv.value for fv in record.links_other],
            },
            "headline": record.headline.value if record.headline else None,
            "years_experience": record.years_experience.value if record.years_experience else None,
            "skills": self._aggregate_skills(record),
            "experience": [self._experience_to_dict(fv.value) for fv in record.experience],
            "education": [self._education_to_dict(fv.value) for fv in record.education],
        }

        if include_confidence:
            profile["overall_confidence"] = record.overall_confidence
        if include_provenance:
            profile["provenance"] = self._provenance_tracker.collect(record)

        return _prune_empty(profile) if not include_empty_fields else profile

    @staticmethod
    def _aggregate_skills(record: CandidateRecord) -> List[Dict[str, Any]]:
        """Groups skill FieldValues by name into {name, confidence, sources}."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for fv in record.skills:
            entry = grouped.setdefault(
                fv.value, {"name": fv.value, "confidences": [], "sources": set()}
            )
            entry["confidences"].append(fv.provenance.confidence)
            entry["sources"].add(fv.provenance.source)
        result = [
            {
                "name": data["name"],
                "confidence": round(sum(data["confidences"]) / len(data["confidences"]), 4),
                "sources": sorted(data["sources"]),
            }
            for data in grouped.values()
        ]
        return sorted(result, key=lambda s: s["name"])

    @staticmethod
    def _experience_to_dict(entry: ExperienceEntry) -> Dict[str, Any]:
        return {
            "company": entry.company,
            "title": entry.title,
            "start": entry.start,
            "end": entry.end,
            "summary": entry.summary,
        }

    @staticmethod
    def _education_to_dict(entry: EducationEntry) -> Dict[str, Any]:
        return {
            "institution": entry.institution,
            "degree": entry.degree,
            "field": entry.field,
            "end_year": entry.end_year,
        }

    @staticmethod
    def _apply_output_normalize(value: Any, normalize_hint: Optional[str]) -> Any:
        """
        Honors a config "normalize" hint. Values are already normalized to
        canonical form upstream (during the Normalize stage), so this is
        mostly a confirming no-op -- except E164, which is re-applied
        defensively in case a custom "from" path pulled a value that
        bypassed phone normalization.
        """
        if normalize_hint == "E164" and isinstance(value, str):
            return normalize_phone(value) or value
        return value