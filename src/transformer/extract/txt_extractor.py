"""Plain-text extractor for free-form recruiter notes."""

import os
from typing import Optional

from transformer.extract.base import Extractor


class TxtExtractor(Extractor):
    """Reads a recruiter notes .txt file into a single raw string."""

    source_name = "recruiter_notes"

    def extract(self, path: str) -> Optional[str]:
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return None
        text = text.strip()
        return text if text else None