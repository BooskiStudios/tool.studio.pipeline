import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from booski_core.core.fields import Text2000, Text5000, Text20000, Title
from booski_core.vocab import DecisionStatus


class DecisionOption(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    summary: Text2000 = ""


Options = Annotated[list[DecisionOption], Field(max_length=20)]
DocumentIds = Annotated[list[uuid.UUID], Field(max_length=20)]


class DecisionCreate(BaseModel):
    title: Title
    context: Text20000 = ""
    options: Options = Field(default_factory=list, description="Options considered.")
    outcome: Text5000 = Field(default="", description="The option chosen, or what was decided.")
    rationale: Text20000 = ""
    status: DecisionStatus = "proposed"
    project_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    supersedes_decision_id: uuid.UUID | None = Field(
        default=None,
        description="An earlier decision this replaces. It is marked superseded once this is accepted.",
    )
    document_ids: DocumentIds = Field(default_factory=list, description="Supporting documents.")


class DecisionUpdate(BaseModel):
    """Decisions are never deleted; every edit is kept in the activity history. Send ``version`` to detect
    conflicting edits."""

    title: Title | None = None
    context: Text20000 | None = None
    options: Options | None = None
    outcome: Text5000 | None = None
    rationale: Text20000 | None = None
    status: DecisionStatus | None = None
    department_id: uuid.UUID | None = None
    document_ids: DocumentIds | None = None
    version: int | None = None


class DecisionOut(BaseModel):
    id: uuid.UUID
    title: str
    context: str
    options: list[DecisionOption]
    outcome: str
    rationale: str
    status: DecisionStatus
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    author_user_id: uuid.UUID | None
    recorded_at: datetime
    decided_at: datetime | None
    supersedes_decision_id: uuid.UUID | None
    superseded_by_decision_id: uuid.UUID | None
    document_ids: list[uuid.UUID]
    updated_at: datetime
    version: int
