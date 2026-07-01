"""PDF extractor for resume files."""

import os
from typing import Optional

from transformer.extract.base import Extractor


class PdfExtractor(Extractor):
    """Reads a resume PDF and returns its concatenated page text.

    Uses pdfplumber, which handles most text-based PDFs well. Scanned
    (image-only) PDFs will yield empty/near-empty text — that is treated
    as "no usable content" rather than an error, per the robustness
    constraint (garbage source -> null fields, not a crash).
    """

    source_name = "resume_pdf"

    def extract(self, path: str) -> Optional[str]:
        if not path or not os.path.isfile(path):
            return None
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
        except Exception:
            # Any pdfplumber/parsing failure -> treat as unreadable source,
            # never propagate and crash the pipeline.
            return None

        text = "\n".join(pages_text).strip()
        return text if text else None