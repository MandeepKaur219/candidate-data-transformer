"""
JSON writer.

The final pipeline stage: serializes the already-projected, already-
validated list of candidate profile dicts to a JSON file on disk. This
stage does no shaping or decision-making of its own -- by design, it is
the one place in the pipeline that is purely I/O, so swapping the output
sink (e.g. to a database writer later) never touches projection or
validation logic.
"""

import json
import os
from typing import Any, Dict, List


class JsonWriter:
    """Writes a list of projected candidate profiles to a JSON file."""

    def write(self, profiles: List[Dict[str, Any]], output_path: str) -> str:
        """
        Writes `profiles` as a pretty-printed JSON array to `output_path`,
        creating parent directories as needed. Key order is preserved as
        produced by the Projector (which is itself deterministic), and
        `ensure_ascii=False` keeps non-ASCII names/text human-readable
        rather than escaped.

        Returns the path written to, for convenience.
        """
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")

        return output_path