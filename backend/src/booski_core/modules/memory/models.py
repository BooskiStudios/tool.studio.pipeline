import uuid
from typing import Any

from sqlalchemy import CheckConstraint, Computed, ForeignKey, Index, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import Archivable, Base, Timestamps, Versioned, check_in, same_workspace, uuid_pk
from booski_core.vocab import MemoryKind, values

MAX_MEMORY_CHARS = 2_000
MEMORY_SEARCH_EXPRESSION = "setweight(to_tsvector('english'::regconfig, content), 'A')"


class Memory(Versioned, Archivable, Timestamps, Base):
    """One memory entry. Studio-wide when ``project_id`` and ``department_id`` are NULL.

    Provenance: who wrote and last changed it, when, and optionally the document or decision it came from.
    Every change is recorded in the activity log (entity type ``memory``).
    """

    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        same_workspace(("source_document_id", "workspace_id"), "documents"),
        same_workspace(("source_decision_id", "workspace_id"), "decisions"),
        check_in("kind", values(MemoryKind), "kind_valid"),
        CheckConstraint(f"char_length(content) BETWEEN 1 AND {MAX_MEMORY_CHARS}", name="content_length"),
        Index("ix_memories_workspace_id_updated_at", "workspace_id", "updated_at"),
        Index("ix_memories_project_id", "project_id"),
        Index("ix_memories_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source_decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(MEMORY_SEARCH_EXPRESSION, persisted=True), deferred=True
    )
