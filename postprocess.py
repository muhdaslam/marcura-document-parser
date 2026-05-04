import re

from ..models import Clause
from .logutil import logger


def dedupe_clauses(clauses: list[Clause]) -> list[Clause]:
    """Keep the longest-text occurrence of each (id, title) pair (overlap may produce duplicates)."""
    seen: dict[tuple[str, str], int] = {}
    for i, clause in enumerate(clauses):
        key = (clause.id, clause.title)
        if key not in seen or len(clause.text) > len(clauses[seen[key]].text):
            seen[key] = i
    return [clauses[i] for i in sorted(seen.values())]


def merge_adjacent_same_id(clauses: list[Clause]) -> list[Clause]:
    """Merge consecutive entries that share the same id into a single clause."""
    if not clauses:
        return clauses
    result = [clauses[0]]
    for clause in clauses[1:]:
        if clause.id == result[-1].id:
            logger.info("Merging adjacent duplicate id=%r (%r + %r)", clause.id, result[-1].title, clause.title)
            merged = result[-1].text + "\n\n" + clause.text
            result[-1] = result[-1].model_copy(update={"text": merged})
        else:
            result.append(clause)
    return result


def merge_continuations(clauses: list[Clause]) -> list[Clause]:
    """Append __cont__ fragments onto the preceding real clause."""
    result: list[Clause] = []
    for clause in clauses:
        if clause.id == "__cont__":
            if result:
                last = result[-1]
                result[-1] = last.model_copy(update={"text": last.text + "\n\n" + clause.text})
                logger.info("Merged %d-char __cont__ into clause id=%r", len(clause.text), last.id)
            else:
                logger.warning("Discarded __cont__ fragment with no preceding clause (text_len=%d)", len(clause.text))
        else:
            result.append(clause)
    return result


def log_clauses(label: str, clauses: list[Clause]) -> None:
    logger.debug("=== %s (%d) ===", label, len(clauses))
    for c in clauses:
        logger.debug("  id=%r title=%r text_len=%d", c.id, c.title, len(c.text))


def strip_strikethrough(text: str) -> str:
    """Remove ~~...~~ tagged struck-through portions from clause text."""
    logger.debug("strip_strikethrough input:  %r", text[:200])
    # Collapse adjacent struck-through boundaries (e.g. ~~~~ or ~~ ~~) into one span
    text = re.sub(r"~~\s*~~", "", text)
    text = re.sub(r"~~[^~]+~~", "", text)
    text = text.replace("~~", "")  # remove any remaining orphan markers
    result = text.strip()
    logger.debug("strip_strikethrough output: %r", result[:200])
    return result
