"""
Confidence scorer.

Computes one explainable overall_confidence score per merged candidate.

Formula
-------
Each canonical field has a fixed importance weight (identity fields like
full_name/emails matter more than e.g. a portfolio link). A field's own
confidence is its FieldValue's provenance confidence (for list fields, the
average confidence across its items); a field that is entirely missing
contributes a confidence of 0 for its weight, rather than being excluded,
so completeness is baked into the same score as correctness-confidence:

    overall_confidence = sum(weight_f * confidence_f for f in FIELDS)
                          / sum(weight_f for f in FIELDS)

    where confidence_f = 0.0 if the field is missing entirely.

This is a single weighted average, every term of which is independently
inspectable (field -> weight, field -> confidence), which is what makes it
explainable rather than an opaque blended score. The exact weights below
are documented here and in README.md/DESIGN.md.
"""

from typing import Dict, List, Optional

from transformer.models.canonical import CandidateRecord

#: Canonical field -> importance weight. Identity and core professional
#: fields are weighted highest; supplementary fields lowest. Sums to an
#: arbitrary total -- only relative weight matters, since the formula
#: divides by the total.
FIELD_WEIGHTS: Dict[str, float] = {
    "full_name": 1.0,
    "emails": 1.0,
    "phones": 0.8,
    "skills": 0.7,
    "experience": 0.8,
    "education": 0.5,
    "headline": 0.5,
    "years_experience": 0.5,
    "location_city": 0.3,
    "location_region": 0.3,
    "location_country": 0.3,
    "links_linkedin": 0.3,
    "links_github": 0.3,
    "links_portfolio": 0.2,
}


def _field_confidence(record: CandidateRecord, field_name: str) -> Optional[float]:
    """Returns a field's own confidence, or None if the field is unset."""
    attr = getattr(record, field_name)
    if attr is None:
        return None
    if isinstance(attr, list):
        if not attr:
            return None
        return sum(fv.provenance.confidence for fv in attr) / len(attr)
    return attr.provenance.confidence


class ConfidenceScorer:
    """Computes overall_confidence for merged candidate records."""

    def __init__(self, field_weights: Optional[Dict[str, float]] = None):
        self._weights = field_weights or FIELD_WEIGHTS

    def score(self, record: CandidateRecord) -> float:
        """Returns the overall confidence for `record`, in [0.0, 1.0]."""
        total_weight = sum(self._weights.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for field_name, weight in self._weights.items():
            confidence = _field_confidence(record, field_name) or 0.0
            weighted_sum += weight * confidence

        return round(weighted_sum / total_weight, 4)

    def score_all(self, records: List[CandidateRecord]) -> List[CandidateRecord]:
        """Scores every record in place and returns the same list."""
        for record in records:
            record.overall_confidence = self.score(record)
        return records