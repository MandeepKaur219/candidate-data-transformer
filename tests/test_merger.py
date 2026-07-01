"""Unit tests for transformer.merge.* -- behaviour, not just imports."""

from transformer.merge.matcher import Matcher
from transformer.merge.merger import Merger
from transformer.models.canonical import CandidateRecord, FieldValue
from transformer.models.provenance import Provenance


def _fv(field, value, source, confidence=0.9, method="direct_field"):
    return FieldValue(
        value=value,
        provenance=Provenance(field=field, source=source, method=method, confidence=confidence),
    )


def _record(source, full_name=None, emails=None, phones=None):
    rec = CandidateRecord(source=source)
    if full_name:
        rec.full_name = _fv("full_name", full_name, source)
    rec.emails = [_fv("emails", e, source) for e in (emails or [])]
    rec.phones = [_fv("phones", p, source) for p in (phones or [])]
    return rec


class TestMatcher:
    def test_groups_by_email_first(self):
        a = _record("resume_pdf", "Jane Doe", emails=["jane@example.com"])
        b = _record("recruiter_csv", "J. Doe", emails=["JANE@example.com"])
        clusters = Matcher().cluster([a, b])
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_falls_back_to_phone_when_no_email(self):
        a = _record("resume_pdf", "Jane Doe", phones=["+14155552671"])
        b = _record("recruiter_csv", "Jane D.", phones=["+14155552671"])
        clusters = Matcher().cluster([a, b])
        assert len(clusters) == 1

    def test_falls_back_to_name_when_no_email_or_phone(self):
        a = _record("resume_pdf", "Jane Doe")
        b = _record("recruiter_notes", "jane doe")
        clusters = Matcher().cluster([a, b])
        assert len(clusters) == 1

    def test_email_match_does_not_merge_different_phone_holders(self):
        a = _record("resume_pdf", emails=["jane@example.com"])
        b = _record("recruiter_csv", phones=["+14155552671"])
        clusters = Matcher().cluster([a, b])
        assert len(clusters) == 2

    def test_record_with_no_identifiers_is_its_own_singleton(self):
        a = CandidateRecord(source="recruiter_notes")
        clusters = Matcher().cluster([a])
        assert clusters == [[a]]

    def test_distinct_candidates_stay_separate(self):
        a = _record("resume_pdf", emails=["jane@example.com"])
        b = _record("resume_pdf", emails=["john@example.com"])
        clusters = Matcher().cluster([a, b])
        assert len(clusters) == 2


class TestMerger:
    def test_scalar_conflict_resolved_by_source_priority(self):
        merger = Merger(source_priority=["resume_pdf", "recruiter_csv"])
        a = _record("recruiter_csv", full_name="Jane D.")
        b = _record("resume_pdf", full_name="Jane Doe")
        merged = merger.merge_cluster([a, b])
        assert merged.full_name.value == "Jane Doe"
        assert merged.full_name.provenance.source == "resume_pdf"

    def test_unranked_source_loses_to_ranked_source(self):
        merger = Merger(source_priority=["resume_pdf"])
        a = _record("recruiter_notes", full_name="Jane D.")
        b = _record("resume_pdf", full_name="Jane Doe")
        merged = merger.merge_cluster([a, b])
        assert merged.full_name.value == "Jane Doe"

    def test_list_fields_merge_uniquely(self):
        merger = Merger(source_priority=["resume_pdf", "recruiter_csv"])
        a = _record("recruiter_csv", emails=["jane@example.com", "j.doe@work.com"])
        b = _record("resume_pdf", emails=["jane@example.com"])
        merged = merger.merge_cluster([a, b])
        values = sorted(fv.value for fv in merged.emails)
        assert values == ["j.doe@work.com", "jane@example.com"]

    def test_duplicate_list_value_keeps_higher_priority_provenance(self):
        merger = Merger(source_priority=["resume_pdf", "recruiter_csv"])
        a = _record("recruiter_csv", emails=["jane@example.com"])
        b = _record("resume_pdf", emails=["jane@example.com"])
        merged = merger.merge_cluster([a, b])
        assert len(merged.emails) == 1
        assert merged.emails[0].provenance.source == "resume_pdf"

    def test_candidate_id_is_deterministic_for_same_identities(self):
        merger = Merger(source_priority=["resume_pdf"])
        a = _record("resume_pdf", "Jane Doe", emails=["jane@example.com"])
        id1 = merger.merge_cluster([a]).candidate_id
        id2 = merger.merge_cluster([a]).candidate_id
        assert id1 == id2
        assert id1.startswith("cand_")

    def test_candidate_id_independent_of_record_order(self):
        merger = Merger(source_priority=["resume_pdf", "recruiter_csv"])
        a = _record("recruiter_csv", emails=["jane@example.com"])
        b = _record("resume_pdf", full_name="Jane Doe")
        id_forward = merger.merge_cluster([a, b]).candidate_id
        id_backward = merger.merge_cluster([b, a]).candidate_id
        assert id_forward == id_backward

    def test_merge_all_processes_every_cluster(self):
        merger = Merger(source_priority=["resume_pdf"])
        clusters = [
            [_record("resume_pdf", emails=["a@example.com"])],
            [_record("resume_pdf", emails=["b@example.com"])],
        ]
        merged = merger.merge_all(clusters)
        assert len(merged) == 2