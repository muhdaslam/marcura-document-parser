"""Tests for charter_parser.models."""

import pytest
from pydantic import ValidationError

from charter_parser.models import Clause, ClauseCollection


def test_clause_round_trip() -> None:
    c = Clause(id="1", title="Ship", text="The vessel shall be …")
    assert c.id == "1"
    assert c.title == "Ship"
    assert "vessel" in c.text


def test_clause_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Clause(id="1", title="T", text="x", unknown="nope")  # type: ignore[call-arg]


def test_clause_collection_ordered() -> None:
    col = ClauseCollection(
        clauses=[
            Clause(id="1", title="A", text="a"),
            Clause(id="2", title="B", text="b"),
        ]
    )
    assert [c.id for c in col.clauses] == ["1", "2"]


def test_clause_collection_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ClauseCollection(clauses=[], extra="no")  # type: ignore[call-arg]
