# Marcura Document Parser

Extract numbered legal clauses from voyage charter party PDFs using PyMuPDF + Anthropic.

## Requirements

- Python 3.10+
- Anthropic API key in environment (`ANTHROPIC_API_KEY`)

## Install

### Option 1: editable install (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then run:

```bash
charter-extract --help
```

### Option 2: requirements file

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Export ANTHROPIC_API_KEY

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
```

## Run the app

From project root:

```bash
python main.py
```

Example:

```bash
python main.py --output output/clauses.json --first-page 6 --last-page 39
```

Useful CLI options:

- `--pdf`: local PDF path (defaults to `voyage-charter-example.pdf`)
- `--url`: download URL if `--pdf` does not exist
- `--output`: clauses JSON path (default: `output/clauses.json` under the project root; a bare filename such as `my.json` is written to `output/my.json`)
- `--first-page`, `--last-page`: 1-based page range

## Output

- Structured clauses JSON: path from `--output` (default folder: project `output/`, default file `clauses.json`)
- Debug log: same directory as the JSON file, named `debug_extraction.log`

### Running tests

Install optional dev dependencies (includes pytest), then run the suite from the project root:

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

PyMuPDF-related `DeprecationWarning` noise from the extension on some Python versions is filtered in `pyproject.toml` so test output stays readable.

## Tests

Automated tests live under `tests/` (34 cases). They do not call the live Anthropic API except where the client is mocked.


| File                  | Scope                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `test_models.py`      | Pydantic `Clause` and `ClauseCollection`: valid payloads, `extra="forbid"` rejection                                           |
| `test_cli.py`         | `resolve_output_path` (absolute, relative with parent, bare filename → `output/`), `parse_args` defaults and overrides         |
| `test_chunking.py`    | Clause-boundary chunking: `heading_start`, `clause_starts`, `chunk_text`, `split_half`                                         |
| `test_json_parse.py`  | `extract_json`: empty input, fenced markdown JSON, preamble before `{`, invalid JSON, non-object top-level                     |
| `test_postprocess.py` | `dedupe_clauses`, `merge_adjacent_same_id`, `merge_continuations`, `strip_strikethrough`                                       |
| `test_pdf_parser.py`  | `CharterPDFParser` strike-through geometry helpers, `_normalize_text`, `_join_multiline_headings`, minimal PDF `extract_pages` |
| `test_extractor.py`   | `ClauseExtractor` with mocked `messages.stream`: JSON → clauses, `...` id → `__cont__`, full `extract` merge path              |


## Project structure

```text
charter_parser/
  __init__.py
  __main__.py
  cli.py
  models.py
  pdf/
    __init__.py
    parser.py
  clause_extractor/
    __init__.py
    extractor.py
    chunking.py
    json_parse.py
    postprocess.py
    prompt.py
    logutil.py
main.py
tests/
pyproject.toml
requirements.txt
```

## Notes

- Extracts and normalizes Part II text from charter party PDFs
- Remove struck-through text from clauses
- Uses Claude to produce structured JSON clauses (`id`, `title`, `text`)
- Omit the entry if `text` is empty
- Handles content-filter retries by recursively splitting text chunks
- Writes a detailed debug log for extraction troubleshooting

