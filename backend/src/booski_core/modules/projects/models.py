import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import (
    SLUG_CHECK,
    Archivable,
    Base,
    Timestamps,
    Versioned,
    check_in,
    same_workspace,
    uuid_pk,
)
from booski_core.vocab import AccentColor, ProjectAccess, ProjectStatus, ProjectVisibility, values


class Project(Versioned, Archivable, Timestamps, Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug"),
        UniqueConstraint("id", "workspace_id"),
        CheckConstraint(f"slug {SLUG_CHECK} AND char_length(slug) BETWEEN 2 AND 64", name="slug_format"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="name_length"),
        CheckConstraint("char_length(description) <= 5000", name="description_length"),
        CheckConstraint(
            "char_length(project_type) <= 80 AND char_length(engine) <= 40", name="labels_length"
        ),
        CheckConstraint("cover_image_url IS NULL OR cover_image_url ~ '^https://'", name="cover_image_https"),
        CheckConstraint("jsonb_typeof(properties) = 'object'", name="properties_object"),
        check_in("status", values(ProjectStatus), "status_valid"),
        check_in("visibility", values(ProjectVisibility), "visibility_valid"),
        check_in("accent_color", values(AccentColor), "accent_color_valid"),
        Index("ix_projects_workspace_id_updated_at", "workspace_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(Text)  # stable: used in URLs, never changes
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    project_type: Mapped[str] = mapped_column(Text, server_default=text("''"))  # e.g. "Open World Survival"
    engine: Mapped[str] = mapped_column(Text, server_default=text("''"))  # e.g. "Unity"
    status: Mapped[str] = mapped_column(Text, server_default=text("'concept'"))
    visibility: Mapped[str] = mapped_column(Text, server_default=text("'workspace'"))
    accent_color: Mapped[str] = mapped_column(Text, server_default=text("'cyan'"))
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    # Free-form metadata (string keys); not used for permissions or business rules.
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class ProjectMember(Base):
    """Per-project access. For restricted projects it is the access list; for any project it can narrow a
    member's rights to read-only ("viewer"). It can never grant more than the workspace role allows."""

    __tablename__ = "project_members"
    __table_args__ = (
        PrimaryKeyConstraint("project_id", "user_id"),
        same_workspace(("project_id", "workspace_id"), "projects", ondelete="CASCADE"),
        # Must be a member of the workspace; leaving the workspace removes project access too.
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
            ondelete="CASCADE",
            name="fk_project_members_membership",
        ),
        check_in("access", values(ProjectAccess), "access_valid"),
        Index("ix_project_members_user_id", "user_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    access: Mapped[str] = mapped_column(Text)
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workstream(Archivable, Timestamps, Base):
    """A project's stream of work within one department (e.g. Project Horizon in Game Development)."""

    __tablename__ = "workstreams"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        UniqueConstraint("id", "project_id"),  # lets tasks require "workstream belongs to my project"
        UniqueConstraint("project_id", "name"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint("char_length(description) <= 2000", name="description_length"),
        Index("ix_workstreams_department_id", "department_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    department_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
