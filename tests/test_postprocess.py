"""Tests for charter_parser.clause_extractor.postprocess."""

from charter_parser.models import Clause
from charter_parser.clause_extractor.postprocess import (
    dedupe_clauses,
    merge_adjacent_same_id,
    merge_continuations,
    strip_strikethrough,
)


def test_dedupe_clauses_keeps_longest_text() -> None:
    clauses = [
        Clause(id="1", title="A", text="short"),
        Clause(id="1", title="A", text="much longer body"),
    ]
    out = dedupe_clauses(clauses)
    assert len(out) == 1
    assert out[0].text == "much longer body"


def test_merge_adjacent_same_id_concatenates_text() -> None:
    clauses = [
        Clause(id="5", title="Cargo", text="part one"),
        Clause(id="5", title="Cargo cont", text="part two"),
    ]
    out = merge_adjacent_same_id(clauses)
    assert len(out) == 1
    assert "part one" in out[0].text and "part two" in out[0].text


def test_merge_continuations_appends_to_previous() -> None:
    clauses = [
        Clause(id="1", title="T", text="start"),
        Clause(id="__cont__", title="__cont__", text="rest"),
    ]
    out = merge_continuations(clauses)
    assert len(out) == 1
    assert "start" in out[0].text and "rest" in out[0].text


def test_merge_continuations_leading_cont_dropped() -> None:
    clauses = [Clause(id="__cont__", title="__cont__", text="orphan")]
    out = merge_continuations(clauses)
    assert out == []


def test_strip_strikethrough_removes_marked_spans() -> None:
    s = "Hello ~~removed~~ world"
    assert strip_strikethrough(s) == "Hello  world"


def test_strip_strikethrough_collapses_adjacent_markers() -> None:
    assert "gone" not in strip_strikethrough("a ~~ ~~ b~~gone~~c")
