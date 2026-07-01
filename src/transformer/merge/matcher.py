"""
Duplicate matcher.

Groups per-source CandidateRecords that represent the same real-world
candidate, using the priority specified by the assignment: email first,
then phone, then name. Rather than treating all three as equally strong
signals (which risks false-positive matches off a weak "same name" alone),
each record is matched on the *highest-priority identifier it actually
has*: a record with an email is only ever matched by that email; a record
with no email but a phone is matched by phone; a record with neither falls
back to a normalized name. This keeps weak signals from ever overriding or
competing with a stronger one that was available.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from transformer.models.canonical import CandidateRecord
from transformer.normalize.text_normalizer import collapse_whitespace


def _match_key(record: CandidateRecord) -> Optional[Tuple[str, str]]:
    """
    Returns this record's single highest-priority match key, typed so an
    email key can never collide with a phone or name key that happens to
    share the same raw string.
    """
    if record.emails:
        return ("email", record.emails[0].value.lower())
    if record.phones:
        return ("phone", record.phones[0].value)
    if record.full_name:
        name_key = collapse_whitespace(record.full_name.value)
        if name_key:
            return ("name", name_key.lower())
    return None


class Matcher:
    """Clusters CandidateRecords belonging to the same real-world candidate."""

    def cluster(self, records: List[CandidateRecord]) -> List[List[CandidateRecord]]:
        """
        Returns a list of clusters (each a list of CandidateRecords). A
        record with no usable match key at all (no email, phone, or name)
        forms its own singleton cluster, since it can't be safely matched
        to anything -- per the "robust" constraint, an unmatchable record
        is degraded to "its own candidate", not dropped or guessed at.
        """
        groups: Dict[Tuple[str, str], List[CandidateRecord]] = defaultdict(list)
        unmatched: List[CandidateRecord] = []

        for record in records:
            key = _match_key(record)
            if key is None:
                unmatched.append(record)
            else:
                groups[key].append(record)

        clusters = list(groups.values())
        clusters.extend([record] for record in unmatched)
        return clusters