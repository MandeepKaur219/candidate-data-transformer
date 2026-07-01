"""CSV extractor for recruiter export files."""

import csv
import os
from typing import Any, Optional

from transformer.extract.base import Extractor


class CsvExtractor(Extractor):
    """Reads a recruiter CSV export into a list of row dicts."""

    source_name = "recruiter_csv"

    def extract(self, path: str) -> Optional[Any]:
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = [row for row in reader if any(v.strip() for v in row.values() if v)]
            return rows if rows else None
        except (OSError, csv.Error):
            return None