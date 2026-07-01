"""
Merger.

Combines a cluster of per-source CandidateRecords (all believed to be the
same real-world candidate, per the Matcher) into a single canonical
CandidateRecord. Two distinct strategies are applied, per field shape:

  - Scalar fields (full_name, headline, ...): exactly one winner is picked,
    using the source priority order from config/pipeline_config.json
    ("source_priority"). Priority is never hardcoded here -- the Merger
    only knows how to rank a source name using whatever list it was given.
  - List fields (emails, phones, skills, experience, education, ...): all
    values survive, deduplicated by value so the same fact reported by two
    sources collapses into one entry rather than appearing twice.

Output ordering for list fields is sorted by value, not by which source or
cluster-traversal order produced it, which is what makes the pipeline
deterministic regardless of dict/set iteration order.
"""

import hashlib
from typing import Dict, Hashable, List, Optional

from transformer.models.canonical import CandidateRecord, FieldValue

_SCALAR_FIELDS = (
    "full_name",
    "headline",
    "years_experience",
    "location_city",
    "location_region",
    "location_country",
    "links_linkedin",
    "links_github",
    "links_portfolio",
)

_LIST_FIELDS = ("emails", "phones", "links_other", "skills", "experience", "education")


def _identity_key(value) -> Hashable:
    """Default dedupe key: lowercase strings compare case-insensitively,
    everything else (already-normalized phones, frozen dataclass entries)
    compares by direct equality/hash."""
    return value.lower() if isinstance(value, str) else value


class Merger:
    """Merges duplicate-candidate clusters into one canonical record each."""

    def __init__(self, source_priority: List[str]):
        """
        Args:
            source_priority: Ordered highest-to-lowest list of source
                names, loaded from config/pipeline_config.json. A source
                not present in this list is treated as lowest priority,
                so an unconfigured source degrades gracefully instead of
                raising.
        """
        self._rank: Dict[str, int] = {
            name: idx for idx, name in enumerate(source_priority)
        }
        self._unranked = len(source_priority)

    def _priority_rank(self, source: Optional[str]) -> int:
        if source is None:
            return self._unranked
        return self._rank.get(source, self._unranked)

    def merge_all(
        self, clusters: List[List[CandidateRecord]]
    ) -> List[CandidateRecord]:
        return [self.merge_cluster(cluster) for cluster in clusters]

    def merge_cluster(self, records: List[CandidateRecord]) -> CandidateRecord:
        merged = CandidateRecord(candidate_id=self._generate_candidate_id(records))

        for attr in _SCALAR_FIELDS:
            values: List[FieldValue] = [
                getattr(r, attr) for r in records if getattr(r, attr) is not None
            ]
            if values:
                winner = min(
                    values, key=lambda fv: self._priority_rank(fv.provenance.source)
                )
                setattr(merged, attr, winner)

        for attr in _LIST_FIELDS:
            all_values: List[FieldValue] = []
            for r in records:
                all_values.extend(getattr(r, attr))
            setattr(merged, attr, self._dedupe_unique(all_values))

        return merged

    def _dedupe_unique(self, values: List[FieldValue]) -> List[FieldValue]:
        """
        Deduplicates by value, preferring the highest-priority source's
        FieldValue (and therefore its provenance) when the same value was
        reported by more than one source. Result is sorted by value for
        deterministic output ordering.
        """
        best_by_key: Dict[Hashable, FieldValue] = {}
        for fv in values:
            key = _identity_key(fv.value)
            current_best = best_by_key.get(key)
            if current_best is None or self._priority_rank(
                fv.provenance.source
            ) < self._priority_rank(current_best.provenance.source):
                best_by_key[key] = fv
        return sorted(
            best_by_key.values(), key=lambda fv: str(_identity_key(fv.value))
        )

    @staticmethod
    def _generate_candidate_id(records: List[CandidateRecord]) -> str:
        """
        Builds a stable id from every identifying value seen in the
        cluster, independent of source order, so the same set of inputs
        always yields the same candidate_id across runs.
        """
        identities = set()
        for r in records:
            if r.full_name:
                identities.add(f"name:{r.full_name.value.strip().lower()}")
            for fv in r.emails:
                identities.add(f"email:{fv.value.strip().lower()}")
            for fv in r.phones:
                identities.add(f"phone:{fv.value.strip()}")
        digest_input = "|".join(sorted(identities)).encode("utf-8")
        digest = hashlib.sha1(digest_input).hexdigest()[:12]
        return f"cand_{digest}"