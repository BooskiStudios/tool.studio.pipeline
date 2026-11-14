import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import Base, CreatedAt, Timestamps, Versioned, check_in, same_workspace, uuid_pk
from booski_core.vocab import ApprovalAction, ApprovalKind, ApprovalStatus, ApprovalSubjectType, values


class Approval(Versioned, Timestamps, Base):
    """A request for permission. ``kind`` and ``payload`` let future AI output, code changes, assets,
    spending and publishing use the same flow; ``subject_*`` optionally points at the record concerned."""

    __tablename__ = "approvals"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        # An assigned reviewer must be a workspace member; if they leave, the request becomes unassigned.
        ForeignKeyConstraint(
            ["workspace_id", "reviewer_user_id"],
            ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
            ondelete="SET NULL (reviewer_user_id)",
            name="fk_approvals_reviewer_membership",
        ),
        CheckConstraint("char_length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint("char_length(description) <= 20000", name="description_length"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        CheckConstraint(
            "reviewer_user_id IS NULL OR reviewer_user_id <> requested_by_user_id", name="no_self_review"
        ),
        CheckConstraint("(subject_type IS NULL) = (subject_id IS NULL)", name="subject_complete"),
        CheckConstraint(
            "(status IN ('approved', 'rejected', 'cancelled')) = (resolved_at IS NOT NULL)",
            name="resolved_at_matches",
        ),
        check_in("kind", values(ApprovalKind), "kind_valid"),
        check_in("status", values(ApprovalStatus), "status_valid"),
        check_in("subject_type", values(ApprovalSubjectType), "subject_type_valid"),
        Index("ix_approvals_workspace_id_status", "workspace_id", "status"),
        Index("ix_approvals_reviewer_open", "reviewer_user_id", postgresql_where=text("resolved_at IS NULL")),
        Index("ix_approvals_subject", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    subject_type: Mapped[str | None] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_comment: Mapped[str] = mapped_column(Text, server_default=text("''"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalReview(CreatedAt, Base):
    """Every action taken on an approval, in order. Immutable (database trigger)."""

    __tablename__ = "approval_reviews"
    __table_args__ = (
        same_workspace(("approval_id", "workspace_id"), "approvals"),
        CheckConstraint("char_length(comment) <= 10000", name="comment_length"),
        check_in("action", values(ApprovalAction), "action_valid"),
        Index("ix_approval_reviews_approval_id_created_at", "approval_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    approval_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(Text)
    comment: Mapped[str] = mapped_column(Text, server_default=text("''"))
