"""Tests for charter_parser.cli helpers and argument parsing."""

from pathlib import Path

from charter_parser.cli import DEFAULT_OUTPUT_DIR, parse_args, resolve_output_path


def test_resolve_output_path_absolute_unchanged() -> None:
    p = Path("/tmp/out.json")
    assert resolve_output_path(p) == p


def test_resolve_output_path_relative_with_parent_unchanged() -> None:
    p = Path("subdir/clauses.json")
    assert resolve_output_path(p) == p


def test_resolve_output_path_bare_filename_goes_under_output_dir() -> None:
    p = Path("clauses.json")
    assert resolve_output_path(p) == DEFAULT_OUTPUT_DIR / "clauses.json"


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.first_page == 6
    assert args.last_page == 39
    assert args.url.startswith("https://")


def test_parse_args_overrides() -> None:
    args = parse_args(
        [
            "--pdf",
            "/tmp/x.pdf",
            "--output",
            "/out/clauses.json",
            "--first-page",
            "10",
            "--last-page",
            "20",
        ]
    )
    assert args.pdf == Path("/tmp/x.pdf")
    assert args.output == Path("/out/clauses.json")
    assert args.first_page == 10
    assert args.last_page == 20
