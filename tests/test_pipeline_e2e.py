"""
End-to-end pipeline integration tests.

These tests exercise the full pipeline stack (Extract -> ... -> Writer)
using in-memory fixture data injected via monkeypatching -- no real files
on disk are required. This makes them fast, hermetic, and deterministic.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from transformer.pipeline import Pipeline


PIPELINE_CONFIG = {
    "source_priority": ["resume_pdf", "ats_json", "recruiter_csv", "recruiter_notes"],
    "field_maps": {
        "recruiter_csv": {
            "name": "full_name",
            "email": "emails",
            "phone": "phones",
            "title": "headline",
        },
        "ats_json": {
            "full_name": "full_name",
            "email": "emails",
            "skills": "skills",
            "years_experience": "years_experience",
        },
        "resume_pdf": {
            "full_name": "full_name",
            "email": "emails",
            "phone": "phones",
            "skills": "skills",
            "years_experience": "years_experience",
        },
        "recruiter_notes": {
            "full_name": "full_name",
            "email": "emails",
            "notes_summary": "headline",
        },
    },
}

SKILL_ALIASES = {"js": "JavaScript", "py": "Python"}


def _make_pipeline() -> Pipeline:
    return Pipeline(PIPELINE_CONFIG, SKILL_ALIASES)


class TestPipelineDefaultSchema:
    def test_returns_list(self):
        pipeline = _make_pipeline()
        with patch.object(pipeline._extractors["recruiter_csv"], "extract") as mock_ex, \
             patch.object(pipeline._parsers["recruiter_csv"], "parse") as mock_pa:
            mock_ex.return_value = [{}]
            mock_pa.return_value = []
            result = pipeline.run({"recruiter_csv": ["dummy.csv"]})
        assert isinstance(result, list)

    def test_empty_sources_return_empty_list(self):
        pipeline = _make_pipeline()
        with patch.object(pipeline._extractors["recruiter_csv"], "extract", return_value=None):
            result = pipeline.run({"recruiter_csv": ["missing.csv"]})
        assert result == []

    def test_unknown_source_is_skipped_gracefully(self):
        """A source the pipeline doesn't know about must not crash the run."""
        pipeline = _make_pipeline()
        result = pipeline.run({"completely_unknown_source": ["some_file.dat"]})
        assert result == []

    def test_single_candidate_round_trips_to_valid_output(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        fv = lambda f, v: FieldValue(
            value=v,
            provenance=Provenance(
                field=f, source="recruiter_csv", method="direct_field", confidence=0.9
            ),
        )
        rec = CandidateRecord(source="recruiter_csv")
        rec.candidate_id = "test-candidate-001"
        rec.full_name = fv("full_name", "Jane Doe")
        rec.emails = [fv("emails", "jane@example.com")]

        with patch.object(pipeline._matcher, "cluster", return_value=[[rec]]), \
             patch.object(pipeline._merger, "merge_all", return_value=[rec]):
            result = pipeline.run({"recruiter_csv": ["dummy.csv"]})

        assert len(result) == 1
        profile = result[0]
        assert profile.get("candidate_id")
        assert profile.get("full_name") == "Jane Doe"
        assert "jane@example.com" in profile.get("emails", [])

    def test_output_is_deterministic_across_two_runs(self):
        """Same inputs -> identical outputs, always."""
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        fv = lambda f, v: FieldValue(
            value=v,
            provenance=Provenance(
                field=f, source="recruiter_csv", method="direct_field", confidence=0.9
            ),
        )
        rec = CandidateRecord(source="recruiter_csv")
        rec.full_name = fv("full_name", "Jane Doe")
        rec.emails = [fv("emails", "jane@example.com")]

        results = []
        for _ in range(2):
            with patch.object(pipeline._matcher, "cluster", return_value=[[rec]]), \
                 patch.object(pipeline._merger, "merge_all", return_value=[rec]):
                results.append(pipeline.run({"recruiter_csv": ["dummy.csv"]}))

        assert json.dumps(results[0], sort_keys=True) == json.dumps(results[1], sort_keys=True)


class TestPipelineMerging:
    def test_two_records_with_same_email_deduplicated(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        def _fv(f, v, src):
            return FieldValue(
                value=v,
                provenance=Provenance(field=f, source=src, method="direct_field", confidence=0.9),
            )

        rec_csv = CandidateRecord(source="recruiter_csv")
        rec_csv.full_name = _fv("full_name", "J. Doe", "recruiter_csv")
        rec_csv.emails = [_fv("emails", "jane@example.com", "recruiter_csv")]

        rec_pdf = CandidateRecord(source="resume_pdf")
        rec_pdf.full_name = _fv("full_name", "Jane Doe", "resume_pdf")
        rec_pdf.emails = [_fv("emails", "jane@example.com", "resume_pdf")]

        clusters = pipeline._matcher.cluster([rec_csv, rec_pdf])
        assert len(clusters) == 1, "same email must cluster into one group"

        merged_list = pipeline._merger.merge_all(clusters)
        assert len(merged_list) == 1
        # resume_pdf wins by priority
        assert merged_list[0].full_name.value == "Jane Doe"

    def test_conflict_resolution_follows_source_priority(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        def _fv(f, v, src):
            return FieldValue(
                value=v,
                provenance=Provenance(field=f, source=src, method="direct_field", confidence=0.9),
            )

        low = CandidateRecord(source="recruiter_notes")
        low.full_name = _fv("full_name", "Jane D.", "recruiter_notes")
        low.emails = [_fv("emails", "jane@example.com", "recruiter_notes")]

        high = CandidateRecord(source="resume_pdf")
        high.full_name = _fv("full_name", "Jane Doe", "resume_pdf")
        high.emails = [_fv("emails", "jane@example.com", "resume_pdf")]

        merged = pipeline._merger.merge_cluster([low, high])
        assert merged.full_name.value == "Jane Doe"
        assert merged.full_name.provenance.source == "resume_pdf"


class TestPipelineCustomOutputConfig:
    def test_custom_config_renames_field(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        fv = lambda f, v: FieldValue(
            value=v,
            provenance=Provenance(
                field=f, source="resume_pdf", method="direct_field", confidence=0.9
            ),
        )
        rec = CandidateRecord(source="resume_pdf")
        rec.full_name = fv("full_name", "Jane Doe")
        rec.emails = [fv("emails", "jane@example.com")]

        custom_cfg = {
            "fields": [
                {"path": "full_name", "type": "string", "required": True},
                {"path": "primary_email", "from": "emails[0]", "type": "string"},
            ],
            "include_confidence": False,
            "on_missing": "null",
        }

        with patch.object(pipeline._matcher, "cluster", return_value=[[rec]]), \
             patch.object(pipeline._merger, "merge_all", return_value=[rec]):
            result = pipeline.run(
                {"resume_pdf": ["dummy.pdf"]}, output_config=custom_cfg
            )

        assert len(result) == 1
        profile = result[0]
        assert "full_name" in profile
        # Renamed field must appear under new name, not original
        assert "primary_email" in profile
        assert "emails" not in profile

    def test_include_confidence_false_omits_overall_confidence(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        fv = lambda f, v: FieldValue(
            value=v,
            provenance=Provenance(
                field=f, source="resume_pdf", method="direct_field", confidence=0.9
            ),
        )
        rec = CandidateRecord(source="resume_pdf")
        rec.full_name = fv("full_name", "Jane Doe")
        rec.emails = [fv("emails", "jane@example.com")]

        custom_cfg = {
            "fields": [{"path": "full_name", "type": "string"}],
            "include_confidence": False,
            "on_missing": "null",
        }

        with patch.object(pipeline._matcher, "cluster", return_value=[[rec]]), \
             patch.object(pipeline._merger, "merge_all", return_value=[rec]):
            result = pipeline.run(
                {"resume_pdf": ["dummy.pdf"]}, output_config=custom_cfg
            )

        assert "overall_confidence" not in result[0]


class TestPipelineWriter:
    def test_output_written_to_disk_when_path_given(self):
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord, FieldValue
        from transformer.models.provenance import Provenance

        fv = lambda f, v: FieldValue(
            value=v,
            provenance=Provenance(
                field=f, source="recruiter_csv", method="direct_field", confidence=0.9
            ),
        )
        rec = CandidateRecord(source="recruiter_csv")
        rec.full_name = fv("full_name", "Jane Doe")
        rec.emails = [fv("emails", "jane@example.com")]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch.object(pipeline._matcher, "cluster", return_value=[[rec]]), \
                 patch.object(pipeline._merger, "merge_all", return_value=[rec]):
                pipeline.run(
                    {"recruiter_csv": ["dummy.csv"]},
                    output_path=tmp_path,
                )

            with open(tmp_path, "r", encoding="utf-8") as f:
                written = json.load(f)

            assert isinstance(written, list)
            assert len(written) == 1
            assert written[0]["full_name"] == "Jane Doe"
        finally:
            os.unlink(tmp_path)

    def test_no_output_path_does_not_write_to_disk(self):
        """When output_path is None the pipeline must not create any file."""
        pipeline = _make_pipeline()
        from transformer.models.canonical import CandidateRecord

        with patch.object(pipeline._matcher, "cluster", return_value=[[]]), \
             patch.object(pipeline._merger, "merge_all", return_value=[]), \
             patch.object(pipeline._writer, "write") as mock_write:
            pipeline.run({"recruiter_csv": ["dummy.csv"]}, output_path=None)

        mock_write.assert_not_called()