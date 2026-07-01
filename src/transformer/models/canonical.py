"""
Canonical internal candidate model.

This is the ONE shape every source gets mapped into (per the assignment's
"one canonical candidate schema" requirement). It is intentionally richer
than the final output schema: every value is wrapped in a FieldValue so its
Provenance travels with it from Extract all the way to the Projector, where
it is flattened down to the requested output shape.

CandidateRecord is used both as:
  - a single source's normalized view of one candidate (pre-merge), where
    `source` is set and `candidate_id` is None, and
  - the merged canonical truth for one candidate (post-merge), where
    `candidate_id` is set and `source` is None.

Reusing one shape for both avoids duplicating the same set of fields in two
near-identical classes (DRY) while keeping the two states distinguishable
via the `source` / `candidate_id` attributes.
"""

from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar

from transformer.models.provenance import Provenance

T = TypeVar("T")

#: Canonical field names that are multi-valued (lists) rather than scalar.
#: This is fixed schema shape (per the assignment's "one fixed set of
#: fields"), not a configurable value -- only source->canonical *naming*
#: and merge *priority* are configurable, the shape itself is not.
LIST_FIELDS = frozenset(
    {"emails", "phones", "links_other", "skills", "experience", "education"}
)


@dataclass(frozen=True)
class FieldValue(Generic[T]):
    """A single value paired with the provenance that produced it."""

    value: T
    provenance: Provenance


@dataclass(frozen=True)
class ExperienceEntry:
    """One work-experience entry. Dates are normalized to YYYY-MM or None."""

    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None


@dataclass(frozen=True)
class EducationEntry:
    """One education entry."""

    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None


@dataclass
class CandidateRecord:
    """
    Canonical candidate representation, used pre-merge (one per source) and
    post-merge (one per real-world candidate).

    All scalar fields are Optional[FieldValue[...]] so "we don't know this"
    (None) is distinguishable from "we know it's empty". All multi-valued
    fields are lists of FieldValue so duplicates can be merged uniquely
    while each individual item keeps its own provenance.
    """

    # Identity / bookkeeping
    source: Optional[str] = None
    candidate_id: Optional[str] = None

    # Core identity fields
    full_name: Optional[FieldValue[str]] = None
    emails: List[FieldValue[str]] = field(default_factory=list)
    phones: List[FieldValue[str]] = field(default_factory=list)

    # Location, split into subfields for per-field provenance/confidence
    location_city: Optional[FieldValue[str]] = None
    location_region: Optional[FieldValue[str]] = None
    location_country: Optional[FieldValue[str]] = None

    # Links
    links_linkedin: Optional[FieldValue[str]] = None
    links_github: Optional[FieldValue[str]] = None
    links_portfolio: Optional[FieldValue[str]] = None
    links_other: List[FieldValue[str]] = field(default_factory=list)

    headline: Optional[FieldValue[str]] = None
    years_experience: Optional[FieldValue[float]] = None

    # Skill names, already alias-normalized to canonical form by this point.
    # Multiple FieldValues with the same .value are expected (one per
    # source/mention) and are exactly what the confidence stage aggregates.
    skills: List[FieldValue[str]] = field(default_factory=list)

    experience: List[FieldValue[ExperienceEntry]] = field(default_factory=list)
    education: List[FieldValue[EducationEntry]] = field(default_factory=list)

    overall_confidence: float = 0.0

    def all_field_values(self) -> List[FieldValue]:
        """
        Return every FieldValue held by this record, scalar and list-valued
        alike. Used by the provenance tracker and the confidence scorer so
        neither has to know about each individual attribute name.
        """
        scalars = [
            self.full_name,
            self.location_city,
            self.location_region,
            self.location_country,
            self.links_linkedin,
            self.links_github,
            self.links_portfolio,
            self.headline,
            self.years_experience,
        ]
        lists: List[FieldValue] = [
            *self.emails,
            *self.phones,
            *self.links_other,
            *self.skills,
            *self.experience,
            *self.education,
        ]
        return [fv for fv in scalars if fv is not None] + lists