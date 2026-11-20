"""Agents and agent runs (PR 3.4). Runs are executed by the ``booski agent-worker`` process."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from booski_core.access.dependencies import MemberContext, WorkspaceContext, require
from booski_core.access.roles import Capability
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.agents import service
from booski_core.modules.agents.schemas import (
    AgentCreate,
    AgentOut,
    AgentUpdate,
    ChangeOut,
    RedirectBody,
    RunCreate,
    RunEventOut,
    RunOut,
    RunSummaryOut,
    ToolCallOut,
    ToolOut,
)
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.tools.registry import TOOLS
from booski_core.vocab import AgentRunStatus

agents_router = APIRouter(prefix="/w/{workspace_slug}/agents", tags=["agents"])
runs_router = APIRouter(prefix="/w/{workspace_slug}/agent-runs", tags=["agents"])
tools_router = APIRouter(prefix="/w/{workspace_slug}/tools", tags=["agents"])

ManageAgents = Annotated[WorkspaceContext, Depends(require(Capability.AGENTS_MANAGE))]
UseAi = Annotated[WorkspaceContext, Depends(require(Capability.AI_USE))]


@tools_router.get("", response_model=list[ToolOut])
def list_tools(ctx: MemberContext) -> list[ToolOut]:
    """Every tool agents can be given. Read tools look things up; propose tools stage a change that is
    applied only when a person approves the run's review."""
    return [
        ToolOut(name=t.name, kind=t.kind, description=t.description, input_schema=t.spec().input_schema)
        for t in TOOLS.values()
    ]


@agents_router.get("", response_model=list[AgentOut])
def list_agents(
    ctx: MemberContext,
    db: DbSession,
    inactive: Annotated[bool, Query(description="Include switched-off agents.")] = False,
) -> list[AgentOut]:
    return [AgentOut.model_validate(a) for a in service.list_agents(db, ctx, include_inactive=inactive)]


@agents_router.post("", response_model=AgentOut, status_code=201)
def create_agent(body: AgentCreate, ctx: ManageAgents, db: DbSession, meta: Meta) -> AgentOut:
    agent = service.create_agent(db, ctx, body, meta)
    db.commit()
    db.refresh(agent)
    return AgentOut.model_validate(agent)


@agents_router.get("/{agent_key}", response_model=AgentOut)
def get_agent(agent_key: str, ctx: MemberContext, db: DbSession) -> AgentOut:
    return AgentOut.model_validate(service.get_agent(db, ctx, agent_key))


@agents_router.patch("/{agent_key}", response_model=AgentOut)
def update_agent(agent_key: str, body: AgentUpdate, ctx: ManageAgents, db: DbSession, meta: Meta) -> AgentOut:
    agent = service.update_agent(db, ctx, service.get_agent(db, ctx, agent_key), body, meta)
    db.commit()
    db.refresh(agent)
    return AgentOut.model_validate(agent)


@runs_router.get("", response_model=Page[RunSummaryOut])
def list_runs(
    ctx: MemberContext,
    db: DbSession,
    status: Annotated[list[AgentRunStatus] | None, Query()] = None,
    agent: Annotated[str | None, Query(description="Agent key.")] = None,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[RunSummaryOut]:
    """Agent runs you can see, newest first."""
    rows, next_cursor = service.list_runs(
        db,
        ctx,
        statuses=list(status) if status else None,
        agent_key=agent,
        project_slug=project,
        limit=limit,
        cursor=cursor,
    )
    keys = service.agent_keys(db, rows)
    items = [
        RunSummaryOut.model_validate(
            {
                **{n: getattr(r, n) for n in RunSummaryOut.model_fields if n != "agent"},
                "agent": keys[r.agent_id],
            }
        )
        for r in rows
    ]
    return Page(items=items, next_cursor=next_cursor)


@runs_router.post("", response_model=RunOut, status_code=201)
def start_run(body: RunCreate, ctx: UseAi, db: DbSession, meta: Meta) -> RunOut:
    """Queues a run. The agent worker picks it up, plans, works through the plan and asks for review."""
    run = service.start_run(db, ctx, body, meta)
    db.commit()
    db.refresh(run)
    return service.to_out(db, ctx, run)


@runs_router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> RunOut:
    return service.to_out(db, ctx, service.get_run(db, ctx, run_id))


@runs_router.get("/{run_id}/tool-calls", response_model=list[ToolCallOut])
def run_tool_calls(run_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> list[ToolCallOut]:
    """Every tool call the run made, with its input, outcome and timing."""
    run = service.get_run(db, ctx, run_id)
    return [ToolCallOut.model_validate(c) for c in service.list_tool_calls(db, run)]


@runs_router.get("/{run_id}/changes", response_model=list[ChangeOut])
def run_changes(run_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> list[ChangeOut]:
    """Changes the run proposed, and whether they were applied (after its review was approved)."""
    run = service.get_run(db, ctx, run_id)
    return [ChangeOut.model_validate(c) for c in service.list_changes(db, run)]


@runs_router.get("/{run_id}/events", response_model=list[RunEventOut])
def run_events(run_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> list[RunEventOut]:
    """Everything that happened in the run, in order."""
    run = service.get_run(db, ctx, run_id)
    return [RunEventOut.model_validate(e) for e in service.list_events(db, run)]


def _respond(db: DbSession, ctx: WorkspaceContext, run_id: uuid.UUID) -> RunOut:
    db.commit()
    return service.to_out(db, ctx, service.get_run(db, ctx, run_id))


@runs_router.post("/{run_id}/pause", response_model=RunOut)
def pause_run(run_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta) -> RunOut:
    """Stops the run after its current step. Its work so far is kept."""
    service.pause_run(db, ctx, run_id, meta)
    return _respond(db, ctx, run_id)


@runs_router.post("/{run_id}/resume", response_model=RunOut)
def resume_run(run_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta) -> RunOut:
    service.resume_run(db, ctx, run_id, meta)
    return _respond(db, ctx, run_id)


@runs_router.post("/{run_id}/cancel", response_model=RunOut)
def cancel_run(run_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta) -> RunOut:
    service.cancel_run(db, ctx, run_id, meta)
    return _respond(db, ctx, run_id)


@runs_router.post("/{run_id}/redirect", response_model=RunOut)
def redirect_run(
    run_id: uuid.UUID, body: RedirectBody, ctx: MemberContext, db: DbSession, meta: Meta
) -> RunOut:
    """Gives the agent a new instruction, followed from its next step on."""
    service.redirect_run(db, ctx, run_id, body.instruction, meta)
    return _respond(db, ctx, run_id)
