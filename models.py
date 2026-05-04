from pydantic import BaseModel, Field, ConfigDict


class Clause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Clause number exactly as printed (e.g. '1', '2', '3')")
    title: str = Field(description="Clause title / heading as it appears in the document margin")
    text: str = Field(description="Full clause body text, excluding the clause number and title")


class ClauseCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clauses: list[Clause] = Field(description="All clauses from Part II in document order")

