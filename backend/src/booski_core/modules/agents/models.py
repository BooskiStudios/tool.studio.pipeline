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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booski_core.db import (
    SLUG_CHECK,
    Base,
    CreatedAt,
    Timestamps,
    Versioned,
    check_in,
    same_workspace,
    uuid_pk,
)
from booski_core.vocab import AgentRunEventType, AgentRunStatus, AutonomyLevel, values

MAX_GOAL_CHARS = 4_000
MAX_GUIDANCE_CHARS = 8_000


class Agent(Versioned, Timestamps, Base):
    """An agent: a configuration on the shared orchestrator (D-P3-3), owned by one workspace.

    Workspaces start with the built-in starter agents (D47, D48); owners and admins can edit, switch off
    or add agents (``agents.manage``).
    """

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        UniqueConstraint("workspace_id", "key"),
        same_workspace(("department_id", "workspace_id"), "departments"),
        CheckConstraint(f"key {SLUG_CHECK} AND char_length(key) BETWEEN 2 AND 48", name="key_format"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint("char_length(description) <= 500", name="description_length"),
        CheckConstraint(f"char_length(guidance) <= {MAX_GUIDANCE_CHARS}", name="guidance_length"),
        CheckConstraint(
            "cardinality(responsibilities) <= 20 AND cardinality(must_not) <= 20"
            " AND cardinality(delegates_to) <= 10",
            name="list_sizes",
        ),
        CheckConstraint("max_steps BETWEEN 1 AND 20", name="max_steps_range"),
        CheckConstraint("max_cost_usd > 0 AND max_cost_usd <= 100", name="max_cost_range"),
        check_in("autonomy", values(AutonomyLevel), "autonomy_valid"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    guidance: Mapped[str] = mapped_column(Text, server_default=text("''"))  # the agent's role and approach
    responsibilities: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    must_not: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    delegates_to: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    task_key: Mapped[str] = mapped_column(Text, ForeignKey("ai_tasks.task_key"))
    autonomy: Mapped[str] = mapped_column(Text, server_default=text("'execute_with_approval'"))
    max_steps: Mapped[int] = mapped_column(Integer, server_default=text("6"))
    max_cost_usd: Mapped[Decimal] = mapped_column(Numeric(8, 2), server_default=text("1.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class AgentRun(Versioned, Timestamps, Base):
    """One piece of work given to an agent, executed by the agent worker.

    The run acts with the permissions of ``started_by_user_id`` and never more: they are checked again
    before every step (D-P3-3).
    """

    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        same_workspace(("agent_id", "workspace_id"), "agents"),
        same_workspace(("project_id", "workspace_id"), "projects"),
        same_workspace(("task_id", "workspace_id"), "tasks"),
        same_workspace(("approval_id", "workspace_id"), "approvals"),
        check_in("status", values(AgentRunStatus), "status_valid"),
        CheckConstraint(f"char_length(goal) BETWEEN 1 AND {MAX_GOAL_CHARS}", name="goal_length"),
        CheckConstraint("jsonb_typeof(plan) = 'array'", name="plan_array"),
        CheckConstraint("jsonb_typeof(notes) = 'array'", name="notes_array"),
        CheckConstraint("steps_used >= 0 AND attempts >= 0 AND cost_usd >= 0", name="counters_non_negative"),
        Index("ix_agent_runs_workspace_id_created_at", "workspace_id", "created_at"),
        Index(
            "ix_agent_runs_claimable", "created_at", postgresql_where=text("status IN ('queued', 'running')")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id"))
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'queued'"))
    # [{"n": 1, "title": "…", "instruction": "…", "agent": "game-designer", "status": "pending",
    #   "output": "…"}]
    plan: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    planned: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # Redirect instructions from people, oldest first: [{"at": "…", "by": "<user id>", "text": "…"}]
    notes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    output: Mapped[str] = mapped_column(Text, server_default=text("''"))
    error_code: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
    steps_used: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 9), server_default=text("0"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))  # times a worker claimed it
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class AgentRunEvent(CreatedAt, Base):
    """What happened in a run, in order. Append-only (database trigger)."""

    __tablename__ = "agent_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "seq"),
        same_workspace(("run_id", "workspace_id"), "agent_runs"),
        check_in("type", values(AgentRunEventType), "type_valid"),
        CheckConstraint("jsonb_typeof(data) = 'object'", name="data_object"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workspaces.id"))
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    ai_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
