"""
Pipeline orchestrator.

Wires every stage together in the exact order the assignment specifies:

    Extract -> Parse -> Map -> Normalize -> Merge -> Confidence
    -> Provenance -> Projector -> Validator -> Writer

This module is intentionally "dumb": it does not itself extract, parse,
normalize, merge, score, or project anything -- it only sequences calls to
the single-responsibility classes that do, using the source-priority and
field-map configuration loaded from config/pipeline_config.json. Adding a
fifth source type means registering one new Extractor/Parser pair here and
adding its field map to the JSON config; no other stage changes.
"""

from typing import Any, Dict, List, Optional, Union

from transformer.confidence.scorer import ConfidenceScorer
from transformer.extract.csv_extractor import CsvExtractor
from transformer.extract.json_extractor import JsonExtractor
from transformer.extract.pdf_extractor import PdfExtractor
from transformer.extract.txt_extractor import TxtExtractor
from transformer.mapping.field_mapper import FieldMapper
from transformer.merge.matcher import Matcher
from transformer.merge.merger import Merger
from transformer.models.canonical import CandidateRecord
from transformer.normalize.record_builder import RecordBuilder
from transformer.normalize.skill_normalizer import SkillNormalizer
from transformer.parse.csv_parser import CsvParser
from transformer.parse.json_parser import JsonParser
from transformer.parse.notes_parser import NotesParser
from transformer.parse.resume_parser import ResumeParser
from transformer.projection.projector import ProjectionError, Projector
from transformer.provenance.tracker import ProvenanceTracker
from transformer.validation.validator import Validator
from transformer.writer.json_writer import JsonWriter

PathOrPaths = Union[str, List[str]]


class Pipeline:
    """Runs the full multi-source candidate transformation pipeline."""

    def __init__(self, pipeline_config: Dict[str, Any], skill_aliases: Dict[str, str]):
        """
        Args:
            pipeline_config: Parsed config/pipeline_config.json, containing
                "source_priority" (merge conflict-resolution order) and
                "field_maps" (per-source raw-field -> canonical-field map).
            skill_aliases: Parsed config/skill_aliases.json alias table.
        """
        self._field_maps: Dict[str, Dict[str, str]] = pipeline_config.get("field_maps", {})

        skill_normalizer = SkillNormalizer(skill_aliases)
        self._record_builder = RecordBuilder(skill_normalizer)

        self._matcher = Matcher()
        self._merger = Merger(pipeline_config.get("source_priority", []))
        self._scorer = ConfidenceScorer()

        provenance_tracker = ProvenanceTracker()
        self._projector = Projector(provenance_tracker)
        self._validator = Validator()
        self._writer = JsonWriter()

        self._extractors = {
            "recruiter_csv": CsvExtractor(),
            "ats_json": JsonExtractor(),
            "resume_pdf": PdfExtractor(),
            "recruiter_notes": TxtExtractor(),
        }
        self._parsers = {
            "recruiter_csv": CsvParser(),
            "ats_json": JsonParser(),
            "resume_pdf": ResumeParser(),
            "recruiter_notes": NotesParser(),
        }

    def run(
        self,
        inputs: Dict[str, PathOrPaths],
        output_config: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs the pipeline end-to-end.

        Args:
            inputs: Maps source name ("recruiter_csv", "ats_json",
                "resume_pdf", "recruiter_notes") to one file path or a
                list of paths for that source. A missing/absent source is
                simply skipped -- the pipeline runs on whatever subset of
                sources is actually provided.
            output_config: Parsed config/output_config.json, or None to
                emit the full default schema.
            output_path: If given, the resulting JSON array is also
                written to this path.

        Returns:
            The list of projected, validated candidate profile dicts, in
            deterministic candidate_id order.
        """
        all_records: List[CandidateRecord] = []
        for source_name, path_or_paths in inputs.items():
            paths = path_or_paths if isinstance(path_or_paths, list) else [path_or_paths]
            for path in paths:
                all_records.extend(self._ingest_source(source_name, path))

        clusters = self._matcher.cluster(all_records)
        merged_records = self._merger.merge_all(clusters)
        self._scorer.score_all(merged_records)

        # Deterministic candidate ordering: candidate_id is itself a
        # stable hash of identity values, so sorting by it makes output
        # order independent of input file row order or dict iteration.
        merged_records.sort(key=lambda r: r.candidate_id)

        profiles: List[Dict[str, Any]] = []
        for record in merged_records:
            try:
                profile = self._projector.project(record, output_config)
            except ProjectionError as exc:
                # A configured-required field truly cannot be produced
                # for this one candidate -- skip just this candidate
                # rather than crash the whole run (robustness constraint).
                print(f"[pipeline] skipped candidate {record.candidate_id}: {exc}")
                continue

            result = self._validator.validate(profile, output_config)
            if not result.is_valid:
                print(f"[validator] candidate {record.candidate_id}: {result.errors}")

            profiles.append(profile)

        if output_path:
            self._writer.write(profiles, output_path)

        return profiles

    def _ingest_source(self, source_name: str, path: Optional[str]) -> List[CandidateRecord]:
        """Runs Extract -> Parse -> Map -> Normalize for one source file."""
        if not path:
            return []

        extractor = self._extractors.get(source_name)
        parser = self._parsers.get(source_name)
        if extractor is None or parser is None:
            print(f"[pipeline] unknown source '{source_name}', skipping")
            return []

        raw = extractor.extract(path)
        if raw is None:
            print(f"[pipeline] source '{source_name}' at '{path}' was empty/unreadable, skipping")
            return []

        field_map = self._field_maps.get(source_name, {})
        mapper = FieldMapper(field_map)

        records: List[CandidateRecord] = []
        for parsed_record in parser.parse(raw):
            mapped = mapper.map_record(parsed_record)
            if not mapped:
                continue
            records.append(self._record_builder.build(source_name, mapped))
        return records