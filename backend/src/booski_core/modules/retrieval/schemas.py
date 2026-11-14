import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from booski_core.modules.retrieval.context import DEFAULT_BUDGET_TOKENS, MAX_BUDGET_TOKENS, MIN_BUDGET_TOKENS
from booski_core.vocab import SourceType

Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class SourceOut(BaseModel):
    """Where a result came from: enough to open, cite and check it."""

    type: SourceType
    id: uuid.UUID
    title: str
    path: str = Field(description="API path of the source record (documents: the exact revision).")
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    updated_at: datetime
    version: int
    revision: int | None = None
    kind: str | None = None
    status: str | None = None


class SearchResultOut(BaseModel):
    source: SourceOut
    snippet: str = Field(description="A short extract; matches are marked « like this ».")
    rank: float


class SearchOut(BaseModel):
    query: str
    results: list[SearchResultOut]


class ContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Query
    project: str | None = Field(default=None, description="Project slug: its records plus studio-wide ones.")
    department: str | None = Field(default=None, description="Department slug.")
    budget_tokens: int = Field(default=DEFAULT_BUDGET_TOKENS, ge=MIN_BUDGET_TOKENS, le=MAX_BUDGET_TOKENS)


class ContextItemOut(BaseModel):
    source: SourceOut
    text: str
    tokens: int
    truncated: bool


class ContextOut(BaseModel):
    query: str
    budget_tokens: int
    total_tokens: int = Field(description="Estimated (conservatively); never above budget_tokens.")
    omitted: int = Field(description="Matching items left out because they didn't fit.")
    items: list[ContextItemOut]
    rendered: str = Field(description="The context exactly as it would be given to an AI model.")
