import json
import re

from .logutil import logger

_JSON_DECODER = json.JSONDecoder()


def extract_json(raw: str) -> dict:
    text = raw.strip()
    if not text:
        return {"clauses": []}
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fenced:
        text = fenced.group(1).strip()
    else:
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
    if not text:
        return {"clauses": []}
    try:
        obj, _ = _JSON_DECODER.raw_decode(text)
        if not isinstance(obj, dict):
            raise json.JSONDecodeError("expected object", text, 0)
        return obj
    except json.JSONDecodeError:
        logger.warning("Could not parse Claude response as JSON: %r", text[:200])
        return {"clauses": []}
