import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from booski_core.core.fields import Tags, Text1000, Title
from booski_core.modules.knowledge.models import MAX_BODY_BYTES
from booski_core.vocab import DocumentKind

Body = Annotated[str, Field(max_length=MAX_BODY_BYTES)]
ChangeNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class DocumentCreate(BaseModel):
    kind: DocumentKind
    title: Title
    summary: Text1000 = ""
    body: Body = ""
    tags: Tags = Field(default_factory=list)
    project_id: uuid.UUID | None = None  # None = studio-wide knowledge
    department_id: uuid.UUID | None = None


class DocumentUpdate(BaseModel):
    """Changing the title or body saves a new revision; earlier revisions are kept unchanged.
    Send ``version`` to detect conflicting edits."""

    kind: DocumentKind | None = None
    title: Title | None = None
    summary: Text1000 | None = None
    body: Body | None = None
    tags: Tags | None = None
    project_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    change_note: ChangeNote = ""
    archived: bool | None = None
    version: int | None = None


class DocumentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: DocumentKind
    title: str
    summary: str
    tags: list[str]
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    current_revision: int
    created_by_user_id: uuid.UUID | None
    updated_by_user_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


class DocumentOut(DocumentSummaryOut):
    body: str
    can_edit: bool


class RevisionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_no: int
    title: str
    change_note: str
    created_by_user_id: uuid.UUID | None
    created_at: datetime


class RevisionOut(RevisionSummaryOut):
    body: str


DocumentSort = Literal["updated_at", "created_at", "title"]
