"""Command-line entry: PDF → text → Claude → JSON."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import anthropic
import httpx

from charter_parser import CharterPDFParser, ClauseExtractor

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
_LOG_DATEFMT = "%H:%M:%S"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PDF_URL = (
    "https://shippingforum.wordpress.com/wp-content/uploads/"
    "2012/09/voyage-charter-example.pdf"
)
DEFAULT_PDF_PATH = _PROJECT_ROOT / "voyage-charter-example.pdf"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "output"
DEFAULT_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "clauses.json"

logger = logging.getLogger(__name__)


def resolve_output_path(path: Path) -> Path:
    """If *path* is only a filename, write under the project ``output/`` folder."""
    if path.is_absolute() or path.parent != Path("."):
        return path
    return DEFAULT_OUTPUT_DIR / path.name


def download_pdf(url: str, dest: Path) -> None:
    logger.info("Downloading PDF from %s …", url)
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        response = client.get(url)
        response.raise_for_status()
    dest.write_bytes(response.content)
    logger.info("Saved to %s (%d bytes)", dest, len(response.content))


def run(pdf_path: Path, output_path: Path, first_page: int, last_page: int) -> None:
    logger.info("Parsing PDF: %s (pages %d–%d)", pdf_path, first_page, last_page)
    with CharterPDFParser(pdf_path) as parser:
        document_text = parser.extract_pages(first_page=first_page, last_page=last_page)

    char_count = len(document_text)
    logger.info("Extracted %d characters of document text", char_count)

    client = anthropic.Anthropic()
    extractor = ClauseExtractor(client)

    logger.info("Sending text to Claude for clause extraction …")
    collection = extractor.extract(document_text)

    logger.info("Extracted %d clauses", len(collection.clauses))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = collection.model_dump()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Written to %s", output_path)

    print(f"\n{'ID':<8} {'TITLE'}")
    print("-" * 60)
    for clause in collection.clauses:
        print(f"{clause.id:<8} {clause.title[:51]}")
    print(f"\nTotal: {len(collection.clauses)} clauses → {output_path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract legal clauses from a charter party PDF using Claude.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_PDF_PATH,
        help="Path to the local PDF file (default: voyage-charter-example.pdf in project root)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_PDF_URL,
        help="URL to download the PDF from if --pdf does not exist",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Output JSON path (default: <project>/output/clauses.json). "
            "A bare filename is placed under <project>/output/."
        ),
    )
    parser.add_argument(
        "--first-page",
        type=int,
        default=6,
        metavar="N",
        help="First 1-based page number of Part II (default: 6)",
    )
    parser.add_argument(
        "--last-page",
        type=int,
        default=39,
        metavar="N",
        help="Last 1-based page number of Part II (default: 39)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_LOG_DATEFMT)

    args = parse_args(argv)
    args.output = resolve_output_path(args.output)

    debug_log_path = args.output.parent / "debug_extraction.log"
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    debug_handler = logging.FileHandler(debug_log_path, mode="w", encoding="utf-8")
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
    extractor_logger = logging.getLogger("charter_parser.clause_extractor")
    extractor_logger.addHandler(debug_handler)
    extractor_logger.setLevel(logging.DEBUG)

    if not args.pdf.exists():
        try:
            download_pdf(args.url, args.pdf)
        except Exception as exc:
            logger.error("Failed to download PDF: %s", exc)
            return 1

    try:
        run(args.pdf, args.output, args.first_page, args.last_page)
    except Exception:
        logger.exception("Extraction failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
