"""Tests for charter_parser.clause_extractor.extractor.ClauseExtractor."""

from unittest.mock import MagicMock

import anthropic

from charter_parser.clause_extractor.extractor import ClauseExtractor
from charter_parser.models import Clause


def _make_stream_message(json_text: str) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    usage.cache_read_input_tokens = 0

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json_text

    message = MagicMock()
    message.usage = usage
    message.content = [text_block]

    stream = MagicMock()
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    stream.get_final_message = MagicMock(return_value=message)
    return stream


def test_call_api_parses_json_and_strips_strikethrough() -> None:
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.stream.return_value = _make_stream_message(
        '{"clauses": [{"id": "1", "title": "~~old~~Title", "text": "Body ~~gone~~ ok"}]}'
    )

    extractor = ClauseExtractor(client)
    clauses = extractor._call_api("dummy text")

    assert len(clauses) == 1
    assert clauses[0].id == "1"
    assert clauses[0].title == "Title"
    assert "gone" not in clauses[0].text
    assert "ok" in clauses[0].text


def test_call_api_dot_id_becomes_cont() -> None:
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.stream.return_value = _make_stream_message(
        '{"clauses": [{"id": "...", "title": "...", "text": "continuation"}]}'
    )

    extractor = ClauseExtractor(client)
    clauses = extractor._call_api("x")

    assert len(clauses) == 1
    assert clauses[0].id == "__cont__"


def test_extract_merges_chunks_without_api_split() -> None:
    """Single chunk path: merge/dedupe pipeline runs on combined clause lists."""
    client = MagicMock(spec=anthropic.Anthropic)
    client.messages.stream.return_value = _make_stream_message(
        '{"clauses": ['
        '{"id": "1", "title": "A", "text": "first"},'
        '{"id": "__cont__", "title": "__cont__", "text": "rest"}'
        "]}"
    )

    extractor = ClauseExtractor(client)
    # ``_MIN_CHUNK_SIZE`` (100) skips tiny chunks — pad so one chunk is processed.
    preamble = "Intro paragraph. " * 8  # > 100 chars with clause markers below
    doc = preamble + "\n\n1. Alpha\n\n2. Beta\n\n"
    collection = extractor.extract(doc)

    assert len(collection.clauses) == 1
    assert collection.clauses[0].id == "1"
    assert "first" in collection.clauses[0].text
    assert "rest" in collection.clauses[0].text
