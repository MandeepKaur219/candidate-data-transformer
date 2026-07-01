"""
Provenance tracker.

"Provenance" is its own pipeline stage per the assignment, separate from
Confidence, even though both read from the same FieldValue.provenance data
that has been carried along since Extract/Parse. Its one job is to flatten
a merged CandidateRecord's per-value provenance into the flat
[{field, source, method}] list the output schema calls for -- it does not
compute anything, it only collects and shapes what is already there,
keeping it a pure read of data other stages produced (no duplicated
extraction/confidence logic).
"""

from typing import Dict, List

from transformer.models.canonical import CandidateRecord


class ProvenanceTracker:
    """Collects a flat, deterministically-ordered provenance list."""

    def collect(self, record: CandidateRecord) -> List[Dict[str, str]]:
        """
        Returns one {"field", "source", "method"} entry per FieldValue held
        by `record` (scalar and list fields alike). Multiple entries can
        share the same "field" when a list field (e.g. skills) has several
        items, each with its own provenance.
        """
        entries = [
            {
                "field": fv.provenance.field,
                "source": fv.provenance.source,
                "method": fv.provenance.method,
            }
            for fv in record.all_field_values()
        ]
        entries.sort(key=lambda e: (e["field"], e["source"], e["method"]))
        return entries