"""Agent configuration, starting runs, run history and human control of runs."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, get_project, project_capabilities, project_scope
from booski_core.access.roles import Capability, has_capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.agents.models import Agent, AgentRun, AgentRunEvent
from booski_core.modules.agents.orchestrator import add_event
from booski_core.modules.agents.schemas import AgentCreate, AgentUpdate, RunCreate, RunOut
from booski_core.modules.ai.models import AiTask
from booski_core.modules.departments.service import get_optional_department
from booski_core.modules.tasks.models import Task

AGENT_NOT_FOUND = "Agent not found."
RUN_NOT_FOUND = "Agent run not found."
FINISHED = {"succeeded", "failed", "cancelled"}


# ---------------------------------------------------------------- agents


def list_agents(db: Session, ctx: WorkspaceContext, *, include_inactive: bool) -> list[Agent]:
    query = select(Agent).where(Agent.workspace_id == ctx.workspace.id)
    if not include_inactive:
        query = query.where(Agent.is_active.is_(True))
    return list(db.scalars(query.order_by(Agent.name)))


def get_agent(db: Session, ctx: WorkspaceContext, key: str) -> Agent:
    agent = db.scalars(
        select(Agent).where(Agent.workspace_id == ctx.workspace.id, Agent.key == key)
    ).one_or_none()
    if agent is None:
        raise ProblemError(404, AGENT_NOT_FOUND)
    return agent


def _require_manage(ctx: WorkspaceContext) -> None:
    if not has_capability(ctx.role, Capability.AGENTS_MANAGE):
        raise ProblemError(403, "Only owners and admins can configure agents.")


def _check_fields(db: Session, ctx: WorkspaceContext, fields: dict[str, Any], own_key: str) -> None:
    if fields.get("task_key") is not None:
        task = db.get(AiTask, fields["task_key"])
        if task is None or not task.is_active:
            raise ProblemError(422, f"Unknown AI task: {fields['task_key']!r}.")
    if fields.get("department_id") is not None:
        get_optional_department(db, ctx, fields["department_id"])
    if fields.get("delegates_to"):
        keys = list(dict.fromkeys(fields["delegates_to"]))
        if own_key in keys:
            raise ProblemError(422, "An agent can't delegate to itself.")
        found = set(
            db.scalars(select(Agent.key).where(Agent.workspace_id == ctx.workspace.id, Agent.key.in_(keys)))
        )
        missing = [k for k in keys if k not in found]
        if missing:
            raise ProblemError(422, f"Unknown agents to delegate to: {', '.join(missing)}.")
        fields["delegates_to"] = keys


def create_agent(db: Session, ctx: WorkspaceContext, body: AgentCreate, meta: RequestMeta) -> Agent:
    _require_manage(ctx)
    fields = body.model_dump()
    _check_fields(db, ctx, fields, body.key)
    if db.scalar(select(Agent.id).where(Agent.workspace_id == ctx.workspace.id, Agent.key == body.key)):
        raise ProblemError(409, "An agent with that key already exists.")
    agent = Agent(workspace_id=ctx.workspace.id, **fields)
    db.add(agent)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="agent.created",
        entity_type="agent",
        entity_id=agent.id,
        summary=f"Added agent {agent.name}",
    )
    return agent


def update_agent(
    db: Session, ctx: WorkspaceContext, agent: Agent, body: AgentUpdate, meta: RequestMeta
) -> Agent:
    _require_manage(ctx)
    check_version(agent, body.version)
    sent = {k: v for k, v in body.model_dump(exclude_unset=True, exclude={"version"}).items()}
    sent = {k: v for k, v in sent.items() if v is not None or k == "department_id"}
    _check_fields(db, ctx, sent, agent.key)
    diff = {k: {"from": getattr(agent, k), "to": v} for k, v in sent.items() if getattr(agent, k) != v}
    if not diff:
        return agent
    for key in diff:
        setattr(agent, key, sent[key])
    bump_version(agent)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="agent.updated",
        entity_type="agent",
        entity_id=agent.id,
        summary=f"Updated agent {agent.name}",
        changes={k: {"from": str(v["from"]), "to": str(v["to"])} for k, v in diff.items()},
    )
    db.flush()
    return agent


# ---------------------------------------------------------------- runs


def _scoped_runs(ctx: WorkspaceContext) -> Select[AgentRun]:
    return select(AgentRun).where(
        AgentRun.workspace_id == ctx.workspace.id, project_scope(ctx, AgentRun.project_id)
    )


def get_run(db: Session, ctx: WorkspaceContext, run_id: uuid.UUID, *, lock: bool = False) -> AgentRun:
    query = _scoped_runs(ctx).where(AgentRun.id == run_id)
    run = db.scalars(query.with_for_update() if lock else query).one_or_none()
    if run is None:
        raise ProblemError(404, RUN_NOT_FOUND)
    return run


def agent_keys(db: Session, runs: list[AgentRun]) -> dict[uuid.UUID, str]:
    ids = {r.agent_id for r in runs}
    if not ids:
        return {}
    return {
        agent_id: key for agent_id, key in db.execute(select(Agent.id, Agent.key).where(Agent.id.in_(ids)))
    }


def can_control(ctx: WorkspaceContext, run: AgentRun) -> bool:
    return run.started_by_user_id == ctx.auth.user.id or has_capability(ctx.role, Capability.AGENTS_MANAGE)


def to_out(db: Session, ctx: WorkspaceContext, run: AgentRun) -> RunOut:
    data = {
        name: getattr(run, name) for name in RunOut.model_fields if hasattr(run, name) and name != "agent"
    }
    return RunOut.model_validate(
        {**data, "agent": agent_keys(db, [run])[run.agent_id], "can_control": can_control(ctx, run)}
    )


def start_run(db: Session, ctx: WorkspaceContext, body: RunCreate, meta: RequestMeta) -> AgentRun:
    agent = get_agent(db, ctx, body.agent)
    if not agent.is_active:
        raise ProblemError(409, "This agent is switched off.")
    project = get_project(db, ctx, slug=body.project) if body.project else None
    if body.task_id is not None:
        task = db.scalars(
            select(Task).where(Task.id == body.task_id, Task.workspace_id == ctx.workspace.id)
        ).one_or_none()
        if task is None:
            raise ProblemError(404, "Task not found.")
        task_project = get_optional_project(db, ctx, task.project_id)  # 404 if the caller can't see it
        if project is not None and task_project is not None and task_project.id != project.id:
            raise ProblemError(422, "The task belongs to a different project.")
        project = project or task_project
    if Capability.AI_USE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Your role doesn't allow using AI here.")
    run = AgentRun(
        workspace_id=ctx.workspace.id,
        agent_id=agent.id,
        project_id=project.id if project else None,
        task_id=body.task_id,
        started_by_user_id=ctx.auth.user.id,
        goal=body.goal,
    )
    db.add(run)
    db.flush()
    add_event(db, run, "created", actor_user_id=ctx.auth.user.id, data={"agent": agent.key})
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="agent_run.started",
        entity_type="agent_run",
        entity_id=run.id,
        project_id=run.project_id,
        summary=f"Asked {agent.name}: {body.goal[:120]}",
    )
    return run


def list_runs(
    db: Session,
    ctx: WorkspaceContext,
    *,
    statuses: list[str] | None,
    agent_key: str | None,
    project_slug: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[AgentRun], str | None]:
    filters: list[ColumnElement[bool]] = []
    if statuses:
        filters.append(AgentRun.status.in_(statuses))
    if agent_key:
        filters.append(AgentRun.agent_id == get_agent(db, ctx, agent_key).id)
    if project_slug:
        filters.append(AgentRun.project_id == get_project(db, ctx, slug=project_slug).id)
    rows, next_cursor = paginate(
        db,
        _scoped_runs(ctx).where(*filters),
        key=SortKey(AgentRun.created_at, datetime.fromisoformat),
        id_column=AgentRun.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda r: r.created_at,
        row_id=lambda r: r.id,
    )
    return list(rows), next_cursor


def list_events(db: Session, run: AgentRun) -> list[AgentRunEvent]:
    return list(
        db.scalars(select(AgentRunEvent).where(AgentRunEvent.run_id == run.id).order_by(AgentRunEvent.seq))
    )


# ---------------------------------------------------------------- human control


def _control(db: Session, ctx: WorkspaceContext, run_id: uuid.UUID) -> AgentRun:
    run = get_run(db, ctx, run_id, lock=True)
    if not can_control(ctx, run):
        raise ProblemError(403, "Only the person who started this run, or an owner or admin, can control it.")
    return run


def _changed(
    db: Session, ctx: WorkspaceContext, run: AgentRun, meta: RequestMeta, event: str, data: dict[str, Any]
) -> None:
    run.version += 1
    add_event(db, run, event, actor_user_id=ctx.auth.user.id, data=data)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb=f"agent_run.{event}",
        entity_type="agent_run",
        entity_id=run.id,
        project_id=run.project_id,
        summary=f"{event.capitalize()} an agent run: {run.goal[:100]}",
        changes=data,
    )


def pause_run(db: Session, ctx: WorkspaceContext, run_id: uuid.UUID, meta: RequestMeta) -> AgentRun:
    run = _control(db, ctx, run_id)
    if run.status not in {"queued", "running"}:
        raise ProblemError(409, f"A {run.status} run can't be paused.")
    run.status = "paused"
    run.lease_owner = None
    run.lease_expires_at = None
    _changed(db, ctx, run, meta, "paused", {})
    return run


def resume_run(db: Session, ctx: WorkspaceContext, run_id: uuid.UUID, meta: RequestMeta) -> AgentRun:
    run = _control(db, ctx, run_id)
    if run.status != "paused":
        raise ProblemError(409, "Only a paused run can be resumed.")
    run.status = "queued"
    _changed(db, ctx, run, meta, "resumed", {})
    return run


def cancel_run(db: Session, ctx: WorkspaceContext, run_id: uuid.UUID, meta: RequestMeta) -> AgentRun:
    run = _control(db, ctx, run_id)
    if run.status in FINISHED:
        raise ProblemError(409, f"A {run.status} run can't be cancelled.")
    run.status = "cancelled"
    run.finished_at = utcnow()
    run.lease_owner = None
    run.lease_expires_at = None
    _changed(db, ctx, run, meta, "cancelled", {})
    return run


def redirect_run(
    db: Session, ctx: WorkspaceContext, run_id: uuid.UUID, instruction: str, meta: RequestMeta
) -> AgentRun:
    """Adds an instruction the agent follows from its next step on (and in its final deliverable)."""
    run = _control(db, ctx, run_id)
    if run.status in FINISHED:
        raise ProblemError(409, f"A {run.status} run can't be redirected.")
    note = {"at": utcnow().isoformat(), "by": str(ctx.auth.user.id), "text": instruction}
    run.notes = [*run.notes, note]
    _changed(db, ctx, run, meta, "redirected", {"instruction": instruction})
    return run
