"""JSON extractor for ATS export blobs."""

import json
import os
from typing import Any, Optional

from transformer.extract.base import Extractor


class JsonExtractor(Extractor):
    """Reads an ATS JSON blob into a list of candidate dicts.

    Accepts either a single JSON object (one candidate) or a JSON array
    (many candidates) and always normalizes to a list, so downstream
    parsing code never has to branch on shape.
    """

    source_name = "ats_json"

    def extract(self, path: str) -> Optional[Any]:
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        if isinstance(data, dict):
            return [data] if data else None
        if isinstance(data, list):
            records = [d for d in data if isinstance(d, dict) and d]
            return records if records else None
        return None