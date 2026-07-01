"""
Validator.

The last gate before output leaves the pipeline. Checks the *projected*
JSON-shaped dict (not the internal CandidateRecord) against whatever
schema was actually requested: the fixed default schema, or a custom
config's declared per-field types. This stage never raises on its own --
it reports a list of human-readable errors so the pipeline can decide
whether to fail loudly or degrade gracefully, per the assignment's
"validate output... degrade gracefully on a missing/garbage source"
constraint. The one thing that can still raise before validation even
runs is the Projector itself, for a field explicitly marked `required`
with an effective `error` policy -- that is deliberate fail-fast behavior
the person configuring the output asked for.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "string[]": lambda v: isinstance(v, list) and all(isinstance(i, str) for i in v),
    "number[]": lambda v: isinstance(v, list)
    and all(isinstance(i, (int, float)) for i in v),
}


@dataclass
class ValidationResult:
    """Outcome of validating one projected candidate profile."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)


class Validator:
    """Validates a projected output dict against its requested schema."""

    def validate(
        self, projected: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        if config and "fields" in config:
            errors = self._validate_custom(projected, config["fields"])
        else:
            errors = self._validate_default(projected)
        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)

    def _validate_custom(
        self, projected: Dict[str, Any], field_specs: List[Dict[str, Any]]
    ) -> List[str]:
        errors: List[str] = []
        for spec in field_specs:
            path = spec["path"]
            if path not in projected:
                if spec.get("required"):
                    errors.append(f"Required field '{path}' is missing from output")
                continue

            value = projected[path]
            if value is None:
                # A null is an explicitly accepted outcome of the
                # on_missing policy, not a validation failure.
                continue

            expected_type = spec.get("type")
            checker = _TYPE_CHECKERS.get(expected_type)
            if checker and not checker(value):
                errors.append(
                    f"Field '{path}' expected type '{expected_type}', "
                    f"got {type(value).__name__}"
                )
        return errors

    def _validate_default(self, projected: Dict[str, Any]) -> List[str]:
        errors: List[str] = []

        if not projected.get("candidate_id"):
            errors.append("candidate_id is missing or empty")

        for list_field in ("emails", "phones"):
            if list_field in projected and not isinstance(projected[list_field], list):
                errors.append(f"'{list_field}' must be a list")

        if "skills" in projected:
            for i, skill in enumerate(projected["skills"]):
                if not isinstance(skill, dict) or "name" not in skill:
                    errors.append(f"skills[{i}] is malformed: missing 'name'")
                elif "confidence" in skill and not isinstance(
                    skill["confidence"], (int, float)
                ):
                    errors.append(f"skills[{i}].confidence must be numeric")

        if "overall_confidence" in projected:
            confidence = projected["overall_confidence"]
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                errors.append("overall_confidence must be a number in [0.0, 1.0]")

        return errors