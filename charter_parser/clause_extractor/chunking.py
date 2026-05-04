import re

_INITIAL_CHUNK_SIZE = 10_000
_MIN_CHUNK_SIZE = 100

_CLAUSE_NUM_RE = re.compile(r'\n[ \t]*\d+\.[ \t]')


def heading_start(text: str, clause_match_pos: int) -> int:
    """Return the position of the first line of the clause heading block."""
    search_limit = max(0, clause_match_pos - 1200)
    pos = clause_match_pos
    candidate = None

    while True:
        blank = text.rfind("\n\n", search_limit, pos)
        if blank == -1:
            break
        prev_line_start = text.rfind("\n", search_limit, blank) + 1
        prev_line = text[prev_line_start:blank].strip()
        candidate = blank + 2
        if len(prev_line) > 40:
            break
        pos = blank

    if candidate is not None:
        return candidate
    prev_nl = text.rfind("\n", max(0, clause_match_pos - 300), clause_match_pos)
    return (prev_nl + 1) if prev_nl != -1 else clause_match_pos + 1


def clause_starts(text: str) -> list[int]:
    """Return a sorted list of positions where each clause heading block begins."""
    positions: list[int] = [0]
    for m in _CLAUSE_NUM_RE.finditer(text):
        pos = heading_start(text, m.start())
        if pos > positions[-1]:
            positions.append(pos)
    return positions


def split_half(text: str) -> tuple[str, str]:
    """Split roughly in half at the clause-number boundary closest to the midpoint."""
    mid = len(text) // 2
    search_start = max(0, mid - 2000)
    search_end = min(len(text), mid + 500)

    best = min(
        _CLAUSE_NUM_RE.finditer(text, search_start, search_end),
        key=lambda m: abs(m.start() - mid),
        default=None,
    )
    if best is not None:
        split = heading_start(text, best.start())
        return text[:split], text[split:]

    nl = text.rfind("\n", mid - 200, mid + 200)
    split = nl + 1 if nl != -1 else mid
    return text[:split], text[split:]


def chunk_text(text: str, size: int) -> list[str]:
    """Split text into chunks at clause boundaries, targeting ~size chars each.

    Each chunk contains one or more complete clauses so no clause is ever cut
    across a boundary.  If a single clause exceeds *size*, it becomes its own
    chunk and the content-filter fallback handles it.
    """
    starts = clause_starts(text)
    chunks: list[str] = []
    i = 0
    while i < len(starts):
        chunk_start = starts[i]
        j = i
        while j + 1 < len(starts) and starts[j + 1] - chunk_start <= size:
            j += 1
        chunk_end = starts[j + 1] if j + 1 < len(starts) else len(text)
        chunks.append(text[chunk_start:chunk_end])
        i = j + 1
    return chunks or [text]
