"""Unit tests for transformer.confidence.scorer -- behaviour, not just imports."""

from transformer.confidence.scorer import ConfidenceScorer
from transformer.models.canonical import CandidateRecord, FieldValue
from transformer.models.provenance import Provenance


def _fv(field, value, source, confidence=0.9, method="direct_field"):
    return FieldValue(
        value=value,
        provenance=Provenance(
            field=field, source=source, method=method, confidence=confidence
        ),
    )


def _minimal_record(sources=("resume_pdf",)):
    """Returns the smallest CandidateRecord that passes a real scoring run."""
    rec = CandidateRecord(source=sources[0])
    rec.full_name = _fv("full_name", "Jane Doe", sources[0])
    rec.emails = [_fv("emails", "jane@example.com", sources[0])]
    return rec


class TestConfidenceScorer:
    def test_overall_confidence_is_a_float_between_0_and_1(self):
        scorer = ConfidenceScorer()
        rec = _minimal_record()
        result = scorer.score(rec)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_more_populated_fields_yields_higher_confidence(self):
        scorer = ConfidenceScorer()

        sparse = _minimal_record()

        rich = _minimal_record()
        rich.phones = [_fv("phones", "+14155552671", "resume_pdf")]
        rich.headline = _fv("headline", "Senior Engineer", "resume_pdf")
        rich.years_experience = _fv("years_experience", 6, "resume_pdf")
        rich.skills = [
            _fv("skills", "Python", "resume_pdf", confidence=0.95),
            _fv("skills", "Go", "resume_pdf", confidence=0.90),
        ]

        assert scorer.score(rich) > scorer.score(sparse)

    def test_multi_source_record_scores_higher_than_single_source(self):
        scorer = ConfidenceScorer()

        single = _minimal_record(sources=("recruiter_csv",))

        multi = _minimal_record(sources=("resume_pdf",))
        multi.emails.append(_fv("emails", "jane@example.com", "recruiter_csv"))

        assert scorer.score(multi) >= scorer.score(single)

    def test_high_confidence_field_values_raise_overall_score(self):
        scorer = ConfidenceScorer()

        low_conf = _minimal_record()
        low_conf.full_name = _fv("full_name", "Jane Doe", "recruiter_notes", confidence=0.4)

        high_conf = _minimal_record()
        high_conf.full_name = _fv("full_name", "Jane Doe", "resume_pdf", confidence=0.95)

        assert scorer.score(high_conf) > scorer.score(low_conf)

    def test_scoring_is_deterministic(self):
        scorer = ConfidenceScorer()
        rec = _minimal_record()
        assert scorer.score(rec) == scorer.score(rec)

    def test_empty_record_does_not_raise(self):
        scorer = ConfidenceScorer()
        rec = CandidateRecord(source="recruiter_csv")
        assert scorer.score(rec) == 0.0

    def test_score_all_sets_overall_confidence_on_record(self):
        """score_all() mutates records in place for the pipeline's use."""
        scorer = ConfidenceScorer()
        rec = _minimal_record()
        scorer.score_all([rec])
        assert isinstance(rec.overall_confidence, float)
        assert 0.0 <= rec.overall_confidence <= 1.0

    def test_score_does_not_mutate_input_field_values(self):
        """Scoring is a read-only operation -- it must not modify the record
        it was given, so that calling score() twice is safe."""
        scorer = ConfidenceScorer()
        rec = _minimal_record()
        original_confidence = rec.full_name.provenance.confidence
        scorer.score(rec)
        assert rec.full_name.provenance.confidence == original_confidence