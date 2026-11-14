"""Tables for the AI Core.

The catalogue (``ai_models``, ``ai_tiers``, ``ai_tasks``) is shared by every workspace: it describes which
models exist, what they cost and which model each kind of task uses. Changing it is a data change, not a
code change. ``workspace_ai_settings`` and ``ai_requests`` belong to a workspace.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import SLUG_CHECK, Base, CreatedAt, Timestamps, check_in, same_workspace, uuid_pk
from booski_core.vocab import AiEffort, AiProviderKey, AiRequestStatus, AiTier, values


class AiModel(Timestamps, Base):
    """A model a provider offers, with its prices (``pricing``, validated by ``pricing.Pricing``)."""

    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint("provider", "model_key"),
        check_in("provider", values(AiProviderKey), "provider_valid"),
        CheckConstraint("char_length(model_key) BETWEEN 1 AND 100", name="model_key_length"),
        CheckConstraint("char_length(display_name) BETWEEN 1 AND 100", name="display_name_length"),
        CheckConstraint("jsonb_typeof(pricing) = 'object'", name="pricing_object"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(Text)
    model_key: Mapped[str] = mapped_column(Text)  # the provider's model id, e.g. "claude-haiku-5-5"
    display_name: Mapped[str] = mapped_column(Text)
    pricing: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class AiTierRoute(Timestamps, Base):
    """The default model and effort for a tier. A task names a tier and may override either."""

    __tablename__ = "ai_tiers"
    __table_args__ = (
        check_in("tier", values(AiTier), "tier_valid"),
        check_in("effort", values(AiEffort), "effort_valid"),
        CheckConstraint("max_tokens BETWEEN 1 AND 128000", name="max_tokens_range"),
    )

    tier: Mapped[str] = mapped_column(Text, primary_key=True)
    model_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ai_models.id"))
    effort: Mapped[str] = mapped_column(Text)
    max_tokens: Mapped[int] = mapped_column(Integer)


class AiTask(Timestamps, Base):
    """A kind of AI work (``classify``, ``draft``, …) and how it is routed."""

    __tablename__ = "ai_tasks"
    __table_args__ = (
        CheckConstraint(
            f"task_key {SLUG_CHECK} AND char_length(task_key) BETWEEN 2 AND 60", name="key_format"
        ),
        CheckConstraint("char_length(description) <= 300", name="description_length"),
        CheckConstraint(
            f"effort IS NULL OR effort IN ({', '.join(repr(v) for v in values(AiEffort))})",
            name="effort_valid",
        ),
        CheckConstraint("max_tokens IS NULL OR max_tokens BETWEEN 1 AND 128000", name="max_tokens_range"),
    )

    task_key: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    tier: Mapped[str] = mapped_column(Text, ForeignKey("ai_tiers.tier"))
    # Overrides; NULL means "use the tier's default".
    model_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai_models.id"))
    effort: Mapped[str | None] = mapped_column(Text)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class WorkspaceAiSettings(Base):
    """AI on/off and the monthly spending cap. A workspace without a row has AI switched off."""

    __tablename__ = "workspace_ai_settings"
    __table_args__ = (
        CheckConstraint(
            "monthly_budget_usd >= 0 AND monthly_budget_usd <= 100000", name="monthly_budget_range"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    monthly_budget_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("20"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class AiRequest(CreatedAt, Base):
    """One AI request: who, where, which task and model, tokens, cost, time and outcome.

    Append-only (a database trigger rejects UPDATE and DELETE). Metadata only: prompts and responses are
    never stored here (D35).
    """

    __tablename__ = "ai_requests"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        check_in("status", values(AiRequestStatus), "status_valid"),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cache_write_tokens >= 0 AND cache_read_tokens >= 0",
            name="tokens_non_negative",
        ),
        CheckConstraint("cost_usd >= 0", name="cost_non_negative"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_non_negative"),
        Index("ix_ai_requests_workspace_id_created_at", "workspace_id", "created_at"),
        Index("ix_ai_requests_project_id_created_at", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # No cascade: history outlives what it describes (as for activity_events).
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    task_key: Mapped[str] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    model_key: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    # Why it was blocked or failed, e.g. "ai_disabled", "budget_reached", "timeout", "rate_limited".
    error_code: Mapped[str | None] = mapped_column(Text)
    stop_reason: Mapped[str | None] = mapped_column(Text)
    refusal_category: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_write_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_read_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 9), server_default=text("0"))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    provider_request_id: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(Text)
