import re
from pathlib import Path

import fitz  # PyMuPDF


class CharterPDFParser:
    """Extracts clean text from a charter party PDF, stripping struck-through characters."""

    PART_II_FIRST_PAGE = 6
    PART_II_LAST_PAGE = 39

    def __init__(self, pdf_path: Path) -> None:
        self._doc = fitz.open(str(pdf_path))

    def __enter__(self) -> "CharterPDFParser":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._doc.close()

    # ------------------------------------------------------------------
    # Strike-through detection
    # ------------------------------------------------------------------

    @staticmethod
    def _horizontal_lines_from_drawings(drawings: list) -> list[tuple[float, float, float, float]]:
        """Return (x0, y0, x1, y1) tuples for every roughly-horizontal line on the page."""
        lines: list[tuple[float, float, float, float]] = []
        for drawing in drawings:
            for item in drawing["items"]:
                op = item[0]
                if op == "l":  # vector line
                    p1, p2 = item[1], item[2]
                    if abs(p1.y - p2.y) < 2.0:
                        x0, x1 = min(p1.x, p2.x), max(p1.x, p2.x)
                        y_mid = (p1.y + p2.y) / 2
                        lines.append((x0, y_mid, x1, y_mid))
                elif op == "re":  # filled rectangle — thin ones are strikethroughs
                    rect = item[1]
                    if rect.height < 3.0:
                        lines.append((rect.x0, rect.y0, rect.x1, rect.y1))
        return lines

    @staticmethod
    def _char_is_struck_through(
        char_bbox: tuple[float, float, float, float],
        h_lines: list[tuple[float, float, float, float]],
    ) -> bool:
        x0, y0, x1, y1 = char_bbox
        # Strikethrough lines cross the character body; underlines sit at or below
        # the baseline (y1). Exclude the bottom 20% of the character height so
        # underlines are not misidentified as strikethroughs.
        char_height = y1 - y0
        strike_y_max = y1 - max(1.5, char_height * 0.2)
        char_width = x1 - x0
        for lx0, ly0, lx1, ly1 in h_lines:
            line_y = (ly0 + ly1) / 2
            if not (y0 - 1 <= line_y <= strike_y_max):
                continue
            # Calculate horizontal overlap
            overlap_start = max(x0, lx0)
            overlap_end = min(x1, lx1)
            overlap = max(0, overlap_end - overlap_start)
            if overlap >= 0.5 * char_width:
                return True
        return False

    # ------------------------------------------------------------------
    # Per-page extraction
    # ------------------------------------------------------------------

    def _extract_page_text(self, page: fitz.Page) -> str:
        h_lines = self._horizontal_lines_from_drawings(page.get_drawings())
        blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        output_lines: list[str] = []
        for block in blocks:
            if block.get("type") != 0:  # skip image blocks
                continue
            for line in block["lines"]:
                parts: list[str] = []
                struck_buf: list[str] = []
                for span in line["spans"]:
                    for char in span["chars"]:
                        if self._char_is_struck_through(char["bbox"], h_lines):
                            struck_buf.append(char["c"])
                        else:
                            if struck_buf:
                                parts.append("~~" + "".join(struck_buf) + "~~")
                                struck_buf = []
                            parts.append(char["c"])
                if struck_buf:
                    parts.append("~~" + "".join(struck_buf) + "~~")
                combined = "".join(parts).rstrip()
                if combined:
                    output_lines.append(combined)
        return "\n".join(output_lines)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @staticmethod
    def _join_multiline_headings(text: str) -> str:
        """Collapse multi-line clause headings into single lines."""
        clause_re = re.compile(r'^\s*\d+\.\s')
        lines = text.split('\n')
        result: list[str] = []

        for line in lines:
            if clause_re.match(line):
                heading_parts: list[str] = []
                while result:
                    prev = result[-1]
                    stripped = prev.strip()
                    if not stripped:
                        result.pop()
                        continue
                    if (len(stripped) <= 30
                            and not clause_re.match(stripped)
                            and not re.search(r'[.!?,;:]$', stripped)):
                        heading_parts.insert(0, stripped)
                        result.pop()
                    else:
                        break
                if heading_parts:
                    result.append(' '.join(heading_parts))
                result.append(line)
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Collapse runs of internal whitespace and limit consecutive blank lines."""
        lines = [re.sub(r"[ \t]+", " ", line) for line in text.splitlines()]
        lines = [l for l in lines if not re.fullmatch(r"\s*\d{1,3}\s*", l)]
        result: list[str] = []
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        normalized = "\n".join(result)
        return CharterPDFParser._join_multiline_headings(normalized)

    def extract_pages(
        self,
        first_page: int = PART_II_FIRST_PAGE,
        last_page: int = PART_II_LAST_PAGE,
    ) -> str:
        """Return the concatenated, cleaned text for the given 1-based page range."""
        page_texts: list[str] = []
        for page_num in range(first_page, last_page + 1):
            idx = page_num - 1
            if idx >= len(self._doc):
                break
            text = self._extract_page_text(self._doc[idx])
            if text.strip():
                page_texts.append(text)
        return self._normalize_text("\n\n".join(page_texts))
