import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, Uuid, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.core.request_meta import IpAddress
from booski_core.db import Base, CreatedAt, uuid_pk


class ActivityEvent(CreatedAt, Base):
    """One thing that happened. Append-only: a database trigger rejects UPDATE and DELETE.

    Never put secrets (passwords, tokens) in ``summary`` or ``changes``.
    """

    __tablename__ = "activity_events"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system')", name="actor_type_valid"),
        CheckConstraint("actor_type = 'system' OR actor_user_id IS NOT NULL", name="user_actor_present"),
        Index("ix_activity_events_workspace_id_created_at", "workspace_id", "created_at"),
        Index("ix_activity_events_entity", "entity_type", "entity_id", "created_at"),
        Index("ix_activity_events_actor_user_id_created_at", "actor_user_id", "created_at"),
        Index("ix_activity_events_project_id_created_at", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # NULL for events outside any workspace (e.g. signing in). No cascade: history outlives what it describes.
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("workspaces.id"))
    # Set for events about a project or anything inside one, so restricted-project history stays private.
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("projects.id"))
    actor_type: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    verb: Mapped[str] = mapped_column(Text)  # e.g. "membership.role_changed"
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    summary: Mapped[str] = mapped_column(Text)
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    request_id: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[IpAddress | None] = mapped_column(INET)
