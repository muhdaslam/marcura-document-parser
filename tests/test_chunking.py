"""Tests for charter_parser.clause_extractor.chunking."""

import re

from charter_parser.clause_extractor.chunking import (
    chunk_text,
    clause_starts,
    heading_start,
    split_half,
)


def test_heading_start_before_numbered_clause() -> None:
    """heading_start returns an index at the clause block (after margin / blank lines)."""
    text = "SHORT LINE\n\n1. Clause body here"
    # Regex match for ``\\n[ \\t]*\\d+.[ \\t]`` starts at the newline before ``1.``
    m_pos = next(m.start() for m in re.finditer(r"\n[ \t]*\d+\.[ \t]", text))
    start = heading_start(text, m_pos)
    assert 0 <= start < len(text)
    assert text[start:].lstrip().startswith("1.")


def test_clause_starts_includes_zero_and_clause_boundaries() -> None:
    text = "preamble\n\n5. First\n\n6. Second"
    starts = clause_starts(text)
    assert starts[0] == 0
    assert "5. First" in text[starts[1] :]


def test_chunk_text_respects_clause_boundaries() -> None:
    text = (
        "intro\n\n"
        "1. Alpha " + ("x" * 500) + "\n\n"
        "2. Beta " + ("y" * 500) + "\n\n"
        "3. Gamma"
    )
    chunks = chunk_text(text, size=800)
    joined = "".join(chunks)
    assert "1. Alpha" in joined and "3. Gamma" in joined
    for ch in chunks:
        assert "\n1." in ch or ch.strip().startswith("intro")


def test_split_half_prefers_clause_boundary_near_midpoint() -> None:
    left_part = "0. " + "a" * 100
    right_part = "\n\n10. " + "b" * 100
    text = left_part + right_part
    left, right = split_half(text)
    assert "10." in right
    assert left.endswith("a") or "0." in left
