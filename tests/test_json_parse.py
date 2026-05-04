"""Tests for charter_parser.clause_extractor.json_parse."""

from charter_parser.clause_extractor.json_parse import extract_json


def test_extract_json_empty_returns_empty_clauses() -> None:
    assert extract_json("") == {"clauses": []}
    assert extract_json("   ") == {"clauses": []}


def test_extract_json_fenced_block() -> None:
    raw = 'Here you go:\n```json\n{"clauses": [{"id": "1", "title": "T", "text": "x"}]}\n```'
    obj = extract_json(raw)
    assert obj["clauses"][0]["id"] == "1"


def test_extract_json_fenced_without_lang() -> None:
    raw = '```\n{"clauses": []}\n```'
    assert extract_json(raw) == {"clauses": []}


def test_extract_json_strips_leading_preamble_before_brace() -> None:
    raw = 'Sure:\n{"clauses": [{"id": "2", "title": "Hi", "text": "Body"}]}'
    obj = extract_json(raw)
    assert obj["clauses"][0]["id"] == "2"


def test_extract_json_invalid_returns_empty_clauses() -> None:
    assert extract_json("{not json") == {"clauses": []}


def test_extract_json_non_object_returns_empty_clauses() -> None:
    assert extract_json('["clauses"]') == {"clauses": []}
