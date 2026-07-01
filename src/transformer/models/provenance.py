"""
Provenance metadata.

Every value that flows through the pipeline carries a Provenance record
describing where it came from, how it was derived, and how confident we
are in it. This is the backbone of the "explainable" requirement: nothing
is ever just a bare value, it is always (value, provenance).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    """
    Describes the origin of a single field value.

    Attributes:
        field: Canonical field name this provenance applies to
            (e.g. "emails", "full_name", "experience").
        source: Name of the originating source, e.g. "recruiter_csv",
            "ats_json", "resume_pdf", "recruiter_notes".
        method: How the value was derived, e.g. "direct_field",
            "regex_extraction", "heuristic_parse", "merge:priority".
        confidence: Confidence in this specific value, in [0.0, 1.0].
    """

    field: str
    source: str
    method: str
    confidence: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )