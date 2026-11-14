import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import Archivable, Base, Timestamps, Versioned, check_in, same_workspace, uuid_pk
from booski_core.vocab import TaskPriority, TaskStatus, values


class Task(Versioned, Archivable, Timestamps, Base):
    """A unit of work. Humans and (later) AI agents use the same API and the same permission checks."""

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        same_workspace(("parent_task_id", "workspace_id"), "tasks"),
        # Workstream and milestone must belong to the task's own project.
        ForeignKeyConstraint(["workstream_id", "project_id"], ["workstreams.id", "workstreams.project_id"]),
        ForeignKeyConstraint(["milestone_id", "project_id"], ["milestones.id", "milestones.project_id"]),
        # The assignee must be a member of this workspace. If they leave, the task becomes unassigned.
        ForeignKeyConstraint(
            ["workspace_id", "assignee_user_id"],
            ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
            ondelete="SET NULL (assignee_user_id)",
            name="fk_tasks_assignee_membership",
        ),
        CheckConstraint("char_length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint("char_length(description) <= 20000", name="description_length"),
        CheckConstraint("parent_task_id IS NULL OR parent_task_id <> id", name="not_own_parent"),
        CheckConstraint(
            "due_date IS NULL OR start_date IS NULL OR due_date >= start_date", name="dates_ordered"
        ),
        CheckConstraint("(status = 'done') = (completed_at IS NOT NULL)", name="completed_at_matches_status"),
        CheckConstraint("workstream_id IS NULL OR project_id IS NOT NULL", name="workstream_needs_project"),
        CheckConstraint("milestone_id IS NULL OR project_id IS NOT NULL", name="milestone_needs_project"),
        check_in("status", values(TaskStatus), "status_valid"),
        check_in("priority", values(TaskPriority), "priority_valid"),
        Index("ix_tasks_workspace_id_status", "workspace_id", "status"),
        Index("ix_tasks_project_id_status", "project_id", "status"),
        Index("ix_tasks_department_id", "department_id"),
        Index("ix_tasks_milestone_id", "milestone_id"),
        Index("ix_tasks_parent_task_id", "parent_task_id"),
        Index("ix_tasks_assignee_open", "assignee_user_id", postgresql_where=text("archived_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    workstream_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'todo'"))
    priority: Mapped[str] = mapped_column(Text, server_default=text("'medium'"))
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # NULL only for records created by the system. AI agents will get their own actor column when they exist.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[float] = mapped_column(Double, server_default=text("0"))


class TaskComment(Timestamps, Base):
    __tablename__ = "task_comments"
    __table_args__ = (
        same_workspace(("task_id", "workspace_id"), "tasks"),
        CheckConstraint("char_length(body) BETWEEN 1 AND 10000", name="body_length"),
        Index("ix_task_comments_task_id_created_at", "task_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
