"""
Parser interface.

"Parse" turns a source's raw extracted payload into a list of flat
dict-per-candidate records, where each value is wrapped in a ParsedValue
(value + extraction method + a confidence for *this specific extraction*).
Parsers use source-specific field names (e.g. CSV's "name" or ATS JSON's
"candidate.full_name") -- renaming those into canonical field names is the
Mapper's job, not the Parser's. This keeps Parse responsible for exactly
one thing: turning raw bytes/rows/text into structured-but-source-named
key/value pairs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ParsedValue:
    """A raw parsed value plus how it was obtained and how sure we are."""

    value: Any
    method: str
    confidence: float


class Parser(ABC):
    """Base interface for all source parsers."""

    #: Canonical name for this source, used throughout provenance tracking.
    source_name: str

    @abstractmethod
    def parse(self, raw: Any) -> List[Dict[str, ParsedValue]]:
        """
        Convert a source's raw payload into a list of per-candidate dicts.

        Each dict maps a source-specific field name to a ParsedValue. One
        dict per candidate found in this source (CSV/JSON sources may
        contain several candidates; PDF/TXT sources contain exactly one).
        Returns an empty list if nothing usable was found -- never raises.
        """
        raise NotImplementedError