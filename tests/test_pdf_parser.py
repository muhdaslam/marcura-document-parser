"""Tests for charter_parser.pdf.parser.CharterPDFParser."""

from pathlib import Path
from types import SimpleNamespace

import fitz

from charter_parser.pdf.parser import CharterPDFParser


def test_char_is_struck_through_horizontal_overlap() -> None:
    # Character box y0=10, y1=20; strike line crosses upper/mid region
    h_lines = [(0.0, 14.0, 100.0, 14.0)]
    bbox = (10.0, 10.0, 30.0, 20.0)
    assert CharterPDFParser._char_is_struck_through(bbox, h_lines) is True


def test_char_is_struck_through_underline_at_bottom_ignored() -> None:
    # Line at bottom of glyph (underline), below strike_y_max
    h_lines = [(0.0, 19.5, 100.0, 19.5)]
    bbox = (10.0, 10.0, 30.0, 20.0)
    assert CharterPDFParser._char_is_struck_through(bbox, h_lines) is False


def test_horizontal_lines_from_drawings_vector_line() -> None:
    p1 = SimpleNamespace(x=0.0, y=10.0)
    p2 = SimpleNamespace(x=50.0, y=10.5)
    drawings = [{"items": [("l", p1, p2)]}]
    lines = CharterPDFParser._horizontal_lines_from_drawings(drawings)
    assert lines


def test_normalize_text_collapses_whitespace_and_strips_margin_numbers() -> None:
    raw = "Hello   world\n\n\n42\n\nNext line"
    out = CharterPDFParser._normalize_text(raw)
    assert "Hello world" in out
    assert "42" not in out.split()


def test_join_multiline_headings_merges_short_margin_lines() -> None:
    raw = "Short\nAnother\n\n1. Clause text here"
    out = CharterPDFParser._join_multiline_headings(raw)
    assert "Short Another" in out.replace("\n", " ") or "Short Another" in out
    assert "1. Clause text" in out


def test_extract_pages_minimal_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "one.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "9. Test clause body")
    doc.save(str(pdf_path))
    doc.close()

    with CharterPDFParser(pdf_path) as parser:
        text = parser.extract_pages(first_page=1, last_page=1)
    assert "9." in text
    assert "Test clause" in text
