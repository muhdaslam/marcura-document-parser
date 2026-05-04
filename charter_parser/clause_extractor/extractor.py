import re
from concurrent.futures import ThreadPoolExecutor

import anthropic

from ..models import Clause, ClauseCollection
from .chunking import (
    _INITIAL_CHUNK_SIZE,
    _MIN_CHUNK_SIZE,
    chunk_text,
    split_half,
)
from .json_parse import extract_json
from .logutil import logger
from .postprocess import (
    dedupe_clauses,
    log_clauses,
    merge_adjacent_same_id,
    merge_continuations,
    strip_strikethrough,
)
from .prompt import _SYSTEM_PROMPT


class ClauseExtractor:
    """Drives the Claude API to extract structured clauses from charter party text."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def _call_api(self, text: str) -> list[Clause]:
        with self._client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=16_000,
            temperature=0,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": "Extract all legal clauses from this charter party text:\n\n" + text,
                }
            ],
        ) as stream:
            message = stream.get_final_message()

        usage = message.usage
        logger.debug(
            "API call — input: %d, output: %d, cache_read: %d",
            usage.input_tokens,
            usage.output_tokens,
            getattr(usage, "cache_read_input_tokens", 0),
        )
        text_block = next(b for b in message.content if b.type == "text")
        logger.debug("--- raw API response ---\n%s\n---", text_block.text)
        data = extract_json(text_block.text)
        clauses = []
        for c in data.get("clauses", []):
            clause = Clause.model_validate(c)
            raw_id = clause.id.strip()
            # Normalise legacy "..." placeholders to the __cont__ sentinel
            if re.fullmatch(r'\.+', raw_id):
                clause = clause.model_copy(update={"id": "__cont__", "title": "__cont__"})
            if clause.id == "__cont__":
                clean_text = strip_strikethrough(clause.text)
                if clean_text:
                    clauses.append(clause.model_copy(update={"title": "__cont__", "text": clean_text}))
                    logger.debug("kept __cont__ text_len=%d", len(clean_text))
                continue
            clean_title = strip_strikethrough(clause.title)
            clean_text = strip_strikethrough(clause.text)
            if not clean_text:
                logger.debug("dropped fully struck-through clause id=%r title=%r", clause.id, clause.title)
                continue
            clause = clause.model_copy(update={"title": clean_title, "text": clean_text})
            clauses.append(clause)
        for c in clauses:
            logger.debug("parsed id=%r title=%r text_len=%d\n    %s",
                         c.id, c.title, len(c.text), c.text[:300])
        return clauses

    def _extract_with_fallback(self, text: str, depth: int = 0) -> list[Clause]:
        """Try to extract clauses; on content-filter error, split in half and retry each half."""
        indent = "  " * depth
        if len(text) < _MIN_CHUNK_SIZE or depth > 6:
            logger.warning(
                "%sChunk too small or max depth reached (%d chars, depth=%d) — skipping",
                indent, len(text), depth,
            )
            return []
        logger.info("%sExtracting %d chars (depth=%d) …", indent, len(text), depth)
        logger.debug("%s--- chunk text ---\n%s\n%s---", indent, text, indent)
        try:
            clauses = self._call_api(text)
            logger.info("%s→ %d clause(s) extracted", indent, len(clauses))
            return clauses
        except anthropic.APIStatusError as exc:
            logger.debug("%sAPIStatusError (depth=%d): %s", indent, depth, exc)
            if "content filtering" not in str(exc).lower():
                raise
            logger.warning(
                "%sContent filter triggered on %d-char chunk — splitting in half and retrying",
                indent,
                len(text),
            )
            left, right = split_half(text)
            return self._extract_with_fallback(left, depth + 1) + self._extract_with_fallback(right, depth + 1)

    def extract(self, document_text: str) -> ClauseCollection:
        chunks = chunk_text(document_text, _INITIAL_CHUNK_SIZE)

        def _process(args: tuple[int, str]) -> list[Clause]:
            i, chunk = args
            logger.info("--- Chunk %d/%d (%d chars) ---", i + 1, len(chunks), len(chunk))
            return self._extract_with_fallback(chunk)

        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            results = list(executor.map(_process, enumerate(chunks)))

        all_clauses = [c for chunk_clauses in results for c in chunk_clauses]
        log_clauses("all_clauses", all_clauses)

        cont_merged = merge_continuations(all_clauses)
        log_clauses("after cont merge", cont_merged)

        merged = merge_adjacent_same_id(cont_merged)
        log_clauses("after merge", merged)

        deduped = dedupe_clauses(merged)
        log_clauses("after dedup", deduped)

        logger.info("Total clauses after deduplication and merge: %d", len(deduped))
        return ClauseCollection(clauses=deduped)
