import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import Base, CreatedAt, Timestamps, Versioned, check_in, same_workspace, uuid_pk
from booski_core.vocab import DecisionStatus, values

DECISION_SEARCH_EXPRESSION = (
    "setweight(to_tsvector('english'::regconfig, title), 'A') || "
    "setweight(to_tsvector('english'::regconfig, outcome || ' ' || rationale), 'B') || "
    "setweight(to_tsvector('english'::regconfig, context), 'C')"
)


class Decision(Versioned, Timestamps, Base):
    """A recorded decision. Never deleted: a changed mind is a new decision that supersedes this one."""

    __tablename__ = "decisions"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        same_workspace(("supersedes_decision_id", "workspace_id"), "decisions"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint(
            "char_length(context) <= 20000 AND char_length(outcome) <= 5000"
            " AND char_length(rationale) <= 20000",
            name="text_lengths",
        ),
        CheckConstraint("jsonb_typeof(options) = 'array'", name="options_array"),
        CheckConstraint(
            "supersedes_decision_id IS NULL OR supersedes_decision_id <> id", name="not_self_superseding"
        ),
        check_in("status", values(DecisionStatus), "status_valid"),
        Index("ix_decisions_workspace_id_recorded_at", "workspace_id", "recorded_at"),
        Index("ix_decisions_project_id", "project_id"),
        Index("ix_decisions_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, server_default=text("''"))
    # [{"title": "…", "summary": "…"}], validated by the API schema.
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    outcome: Mapped[str] = mapped_column(Text, server_default=text("''"))
    rationale: Mapped[str] = mapped_column(Text, server_default=text("''"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'proposed'"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    supersedes_decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # Full-text search (PR 3.3): title first, then outcome and rationale, then context.
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(DECISION_SEARCH_EXPRESSION, persisted=True), deferred=True
    )


class DecisionDocument(CreatedAt, Base):
    """Supporting documents for a decision."""

    __tablename__ = "decision_documents"
    __table_args__ = (
        PrimaryKeyConstraint("decision_id", "document_id"),
        same_workspace(("decision_id", "workspace_id"), "decisions", ondelete="CASCADE"),
        same_workspace(("document_id", "workspace_id"), "documents", ondelete="CASCADE"),
        Index("ix_decision_documents_document_id", "document_id"),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid)
