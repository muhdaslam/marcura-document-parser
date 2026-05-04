"""
Alternate Part II text extraction (dict-based spans, strikethrough removed).

Not used by the CLI; the default pipeline is `CharterPDFParser`, which tags
struck-through text with ~~ markers for the clause extractor.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


PART_II_START_PAGE = 5   # 0-based index (page 6)
PART_II_END_PAGE = 38  # 0-based index (page 39, inclusive)


def _strike_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Return bounding rects of all strikethrough marks on a page."""
    return [
        d["rect"]
        for d in page.get_drawings()
        if d["rect"].height < 2  # thin horizontal bar = strikethrough glyph
    ]


def _is_struck(bbox: fitz.Rect, strike_rects: list[fitz.Rect]) -> bool:
    return any(
        sr.x0 < bbox.x1 and sr.x1 > bbox.x0 and
        sr.y0 < bbox.y1 and sr.y1 > bbox.y0
        for sr in strike_rects
    )


def _extract_page_text(page: fitz.Page) -> str:
    """
    Return the visible (non-struck-through) text of a single page.

    Lines are reconstructed from PyMuPDF dict spans; line numbers that appear
    as isolated integers in the document margin are retained because they help
    the LLM understand document flow and are harmless to the clause extraction
    prompt.
    """
    strikes = _strike_rects(page)
    blocks = page.get_text("dict")["blocks"]

    lines: list[str] = []
    for block in blocks:
        for line in block.get("lines", []):
            parts: list[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                if not _is_struck(fitz.Rect(span["bbox"]), strikes):
                    parts.append(text)
            combined = "".join(parts).strip()
            if combined:
                lines.append(combined)

    return "\n".join(lines)


def extract_part_ii(pdf_path: str | Path) -> str:
    """
    Open *pdf_path* and return the clean (no strikethrough) text of Part II
    (pages 6–39 of the document, i.e. 0-based indices 5–38).
    """
    doc = fitz.open(str(pdf_path))
    pages = [
        _extract_page_text(doc[i])
        for i in range(PART_II_START_PAGE, PART_II_END_PAGE + 1)
    ]
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)
