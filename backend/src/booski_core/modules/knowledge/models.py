import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import (
    Archivable,
    Base,
    CreatedAt,
    Timestamps,
    Versioned,
    check_in,
    same_workspace,
    uuid_pk,
)
from booski_core.vocab import DocumentKind, values

MAX_BODY_BYTES = 1_000_000  # Markdown text. Binary files will go to file storage, never PostgreSQL.

# Full-text search (PR 3.3, D-P3-5): English stemming, title weighted above body and summary.
DOCUMENT_SEARCH_EXPRESSION = "setweight(to_tsvector('english'::regconfig, summary), 'C')"
REVISION_SEARCH_EXPRESSION = (
    "setweight(to_tsvector('english'::regconfig, title), 'A') || "
    "setweight(to_tsvector('english'::regconfig, body), 'B')"
)


class Document(Versioned, Archivable, Timestamps, Base):
    """A knowledge-base entry. Studio-wide when ``project_id`` is NULL, otherwise project knowledge."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint("char_length(summary) <= 1000", name="summary_length"),
        CheckConstraint("cardinality(tags) <= 20", name="tag_count"),
        check_in("kind", values(DocumentKind), "kind_valid"),
        Index("ix_documents_workspace_id_kind_updated_at", "workspace_id", "kind", "updated_at"),
        Index("ix_documents_project_id", "project_id"),
        Index("ix_documents_tags", "tags", postgresql_using="gin"),
        Index("ix_documents_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, server_default=text("''"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    current_revision: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    # Full-text search over the summary (PR 3.3); the title and body are indexed on each revision.
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(DOCUMENT_SEARCH_EXPRESSION, persisted=True), deferred=True
    )


class DocumentRevision(CreatedAt, Base):
    """The title and body as they were at one point. Immutable (database trigger); never deleted."""

    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision_no"),
        same_workspace(("document_id", "workspace_id"), "documents"),
        CheckConstraint("revision_no >= 1", name="revision_positive"),
        CheckConstraint(f"octet_length(body) <= {MAX_BODY_BYTES}", name="body_size"),
        Index("ix_document_revisions_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    revision_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    change_note: Mapped[str] = mapped_column(Text, server_default=text("''"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(REVISION_SEARCH_EXPRESSION, persisted=True), deferred=True
    )
