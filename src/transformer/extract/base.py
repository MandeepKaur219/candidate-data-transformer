"""
Extractor interface.

"Extract" is the pipeline's only I/O-touching stage on the input side: it
turns a path on disk into a source's raw payload (rows, a JSON structure,
plain text) and nothing more. It does no field-name translation, no
schema-shape decisions, and no validation beyond "is this file readable at
all" -- those are the Parser's, Mapper's, and Normalizer's jobs
respectively. Keeping Extract this narrow is what lets every other stage
stay source-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class Extractor(ABC):
    """Base interface for all source extractors."""

    #: Canonical name for this source, used throughout provenance tracking
    #: and to key the pipeline's source -> extractor/parser registries.
    source_name: str

    @abstractmethod
    def extract(self, path: str) -> Optional[Any]:
        """
        Reads the raw payload at `path` for this source type.

        Returns the source's natural raw shape (e.g. a list of CSV row
        dicts, a parsed JSON list, or a plain text string), or None if the
        path is missing, unreadable, or contains nothing usable. Never
        raises -- a missing or garbage source must not crash the run, per
        the assignment's robustness constraint; it degrades to "no records
        from this source" instead.
        """
        raise NotImplementedError