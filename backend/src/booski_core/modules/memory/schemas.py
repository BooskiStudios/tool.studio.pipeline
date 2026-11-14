import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from booski_core.modules.memory.models import MAX_MEMORY_CHARS
from booski_core.vocab import MemoryKind

Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MEMORY_CHARS)]


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    content: Content
    project_id: uuid.UUID | None = None  # None = studio-wide (or department-wide)
    department_id: uuid.UUID | None = None
    source_document_id: uuid.UUID | None = None
    source_decision_id: uuid.UUID | None = None


class MemoryUpdate(BaseModel):
    """Send ``version`` to detect conflicting edits.

    ``archived`` hides an entry from search and AI context."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind | None = None
    content: Content | None = None
    project_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    source_document_id: uuid.UUID | None = None
    source_decision_id: uuid.UUID | None = None
    archived: bool | None = None
    version: int | None = None


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: MemoryKind
    content: str
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    source_document_id: uuid.UUID | None
    source_decision_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    updated_by_user_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    can_edit: bool = False
