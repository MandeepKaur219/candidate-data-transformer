"""Skill alias normalization.

Maps raw skill mentions ("JS", "py", "node.js") to one canonical name
("JavaScript", "Python", "Node.js") using a lookup table loaded entirely
from config/skill_aliases.json -- no alias is hardcoded in this module, so
extending coverage is a config change, not a code change. Skills with no
known alias are not dropped; they fall back to a cleaned, title-cased
version of the raw text so unrecognized-but-real skills still surface.
"""

from typing import Dict, Optional

from transformer.normalize.text_normalizer import collapse_whitespace, title_case_name


class SkillNormalizer:
    """Canonicalizes skill name strings using a configurable alias map."""

    def __init__(self, alias_map: Dict[str, str]):
        """
        Args:
            alias_map: Maps lowercase alias -> canonical skill name, as
                loaded from config/skill_aliases.json.
        """
        self._alias_map = {k.lower(): v for k, v in alias_map.items()}

    def normalize(self, raw: Optional[str]) -> Optional[str]:
        """Returns the canonical skill name, or None if `raw` is empty."""
        cleaned = collapse_whitespace(raw)
        if cleaned is None:
            return None
        alias_hit = self._alias_map.get(cleaned.lower())
        if alias_hit is not None:
            return alias_hit
        return title_case_name(cleaned)