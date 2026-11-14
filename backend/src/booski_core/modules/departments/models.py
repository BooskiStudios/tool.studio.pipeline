import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import SLUG_CHECK, Archivable, Base, Timestamps, check_in, uuid_pk
from booski_core.vocab import AccentColor, values


class Department(Archivable, Timestamps, Base):
    """An operational area of the studio. Each workspace has its own, editable set (seeded with defaults)."""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug"),
        UniqueConstraint("id", "workspace_id"),  # target for same-workspace foreign keys
        CheckConstraint(f"slug {SLUG_CHECK} AND char_length(slug) BETWEEN 2 AND 48", name="slug_format"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint("char_length(description) <= 500", name="description_length"),
        CheckConstraint("char_length(icon_key) BETWEEN 1 AND 40", name="icon_key_length"),
        check_in("accent_color", values(AccentColor), "accent_color_valid"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    icon_key: Mapped[str] = mapped_column(Text, server_default=text("'layers'"))
    accent_color: Mapped[str] = mapped_column(Text, server_default=text("'cyan'"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
