"""Runs one claimed agent run to completion, a step at a time.

Each pass of the loop does one unit of work (plan, one step, or the final deliverable) and commits it, so
a crash loses at most the step in progress: the next worker to claim the run continues from there.

Before every unit the orchestrator re-reads the run and re-checks, from the database:
* the run is still ``running`` and still leased to this worker (people may have paused or cancelled it);
* the person who started it is still an active member with ``ai.use`` for the run's project, so the run
  never has more permission than they do now (D-P3-3);
* the agent is still active, and the run is within its step and cost limits.

AI calls go through the gateway, so the workspace's AI switch, monthly budget, routing and cost log all
apply. Transient provider failures are retried with backoff; anything else fails the run with a reason.
"""

import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from booski_core.access.dependencies import WorkspaceContext, member_context
from booski_core.access.projects import project_capabilities
from booski_core.access.roles import Capability
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_event
from booski_core.modules.agents import prompts
from booski_core.modules.agents.models import Agent, AgentRun, AgentRunEvent
from booski_core.modules.ai import gateway
from booski_core.modules.ai.providers.base import AiProvider, ChatMessage
from booski_core.modules.approvals.models import Approval
from booski_core.modules.projects.models import Project
from booski_core.modules.retrieval.context import assemble_context

RETRYABLE = {"timeout", "rate_limited", "provider_unavailable", "connection_error"}
MAX_CALL_ATTEMPTS = 3
CONTEXT_BUDGET_TOKENS = 3_000
EXTRA_CALLS = 2  # planning and the final deliverable, on top of the plan's steps
LEASE = timedelta(minutes=10)

Sleep = Callable[[float], None]


class RunStoppedError(Exception):
    """The run can't continue; ``code`` and ``detail`` explain why (stored on the run)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class Call:
    text: str
    cost: Decimal
    ai_request_id: uuid.UUID


def add_event(
    db: Session,
    run: AgentRun,
    type_: str,
    *,
    data: dict[str, Any] | None = None,
    actor_user_id: uuid.UUID | None = None,
    ai_request_id: uuid.UUID | None = None,
) -> None:
    """Appends an event. Callers hold the run's row lock, so sequence numbers can't collide."""
    last = db.scalar(select(func.max(AgentRunEvent.seq)).where(AgentRunEvent.run_id == run.id)) or 0
    db.add(
        AgentRunEvent(
            workspace_id=run.workspace_id,
            run_id=run.id,
            seq=last + 1,
            type=type_,
            actor_user_id=actor_user_id,
            ai_request_id=ai_request_id,
            data=data or {},
        )
    )


def _lock(db: Session, run_id: uuid.UUID) -> AgentRun:
    run = db.scalars(select(AgentRun).where(AgentRun.id == run_id).with_for_update()).one()
    return run


def _set_plan(run: AgentRun, plan: list[dict[str, Any]]) -> None:
    run.plan = plan
    run.planned = True


def _still_ours(run: AgentRun, worker: str) -> bool:
    return run.status == "running" and run.lease_owner == worker


class Orchestrator:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        providers: Mapping[str, AiProvider],
        *,
        worker: str,
        sleep: Sleep = time.sleep,
    ) -> None:
        self._sessions = session_factory
        self._providers = providers
        self._worker = worker
        self._sleep = sleep

    # ------------------------------------------------------------------ the loop

    def run(self, run_id: uuid.UUID) -> None:
        while True:
            try:
                if not self._advance(run_id):
                    return
            except RunStoppedError as stop:
                self._fail(run_id, stop.code, stop.detail)
                return

    def _advance(self, run_id: uuid.UUID) -> bool:
        """Does one unit of work. Returns False when there is nothing more for this worker to do."""
        with self._sessions() as db:
            run = db.get(AgentRun, run_id)
            if run is None or not _still_ours(run, self._worker):
                return False  # paused, cancelled or taken over: stop quietly
            ctx, agent, project = self._checks(db, run)
            if not run.planned:
                self._plan(db, run, ctx, agent, project)
                return True
            pending = next((s for s in run.plan if s["status"] != "completed"), None)
            if pending is not None:
                self._step(db, run, ctx, agent, project, pending)
                return True
            self._finish(db, run, ctx, agent)
            return False

    def _checks(self, db: Session, run: AgentRun) -> tuple[WorkspaceContext, Agent, Project | None]:
        ctx = member_context(db, run.workspace_id, run.started_by_user_id)
        if ctx is None:
            raise RunStoppedError(
                "starter_not_allowed", "The person who started this run is no longer an active member."
            )
        project = db.get(Project, run.project_id) if run.project_id else None
        try:
            caps = project_capabilities(db, ctx, project)
        except ProblemError:
            caps = frozenset()
        if Capability.AI_USE not in caps:
            raise RunStoppedError(
                "starter_not_allowed", "The person who started this run may no longer use AI here."
            )
        agent = db.get(Agent, run.agent_id)
        if agent is None or not agent.is_active:
            raise RunStoppedError("agent_inactive", "This agent has been switched off.")
        if run.steps_used >= agent.max_steps + EXTRA_CALLS:
            raise RunStoppedError("step_limit", f"The agent's limit of {agent.max_steps} steps was reached.")
        if run.cost_usd >= agent.max_cost_usd:
            raise RunStoppedError(
                "cost_limit", f"The agent's cost limit of ${agent.max_cost_usd} per run was reached."
            )
        return ctx, agent, project

    # ------------------------------------------------------------------ units of work

    def _colleagues(self, db: Session, run: AgentRun, agent: Agent) -> dict[str, Agent]:
        if not agent.delegates_to:
            return {}
        rows = db.scalars(
            select(Agent).where(
                Agent.workspace_id == run.workspace_id,
                Agent.key.in_(agent.delegates_to),
                Agent.is_active.is_(True),
            )
        )
        return {a.key: a for a in rows}

    def _plan(
        self, db: Session, run: AgentRun, ctx: WorkspaceContext, agent: Agent, project: Project | None
    ) -> None:
        colleagues = self._colleagues(db, run, agent)
        context = self._context(db, ctx, run.goal, project)
        prompt = prompts.planning_prompt(run, agent, colleagues, context)
        call = self._call(db, run, ctx, agent, project, prompt, step=0)
        steps = prompts.parse_plan(
            call.text, own_key=agent.key, allowed={agent.key, *colleagues}, max_steps=agent.max_steps
        )
        plan = [
            {"n": i, "title": s.title, "instruction": s.instruction, "agent": s.agent, "status": "pending"}
            for i, s in enumerate(steps, start=1)
        ]
        self._commit_unit(
            run.id,
            call,
            lambda locked: _set_plan(locked, plan),
            "planned",
            {"steps": [{k: s[k] for k in ("n", "title", "agent")} for s in plan]},
        )

    def _step(
        self,
        db: Session,
        run: AgentRun,
        ctx: WorkspaceContext,
        agent: Agent,
        project: Project | None,
        step: dict[str, Any],
    ) -> None:
        doer = agent
        if step["agent"] != agent.key:
            # Delegation is limited to the agent's allowed, active colleagues (checked again now).
            doer = self._colleagues(db, run, agent).get(step["agent"]) or agent
        context = self._context(db, ctx, f"{step['title']} {step['instruction']}", project)
        with self._sessions() as events_db:
            locked = _lock(events_db, run.id)
            add_event(events_db, locked, "step_started", data={"n": step["n"], "agent": doer.key})
            events_db.commit()
        call = self._call(
            db, run, ctx, doer, project, prompts.step_prompt(run, step, context), step=step["n"]
        )

        def apply(locked: AgentRun) -> None:
            plan = [dict(s) for s in locked.plan]
            for s in plan:
                if s["n"] == step["n"]:
                    s.update(status="completed", output=call.text, agent=doer.key)
            locked.plan = plan
            flag_modified(locked, "plan")

        self._commit_unit(run.id, call, apply, "step_completed", {"n": step["n"], "agent": doer.key})

    def _finish(self, db: Session, run: AgentRun, ctx: WorkspaceContext, agent: Agent) -> None:
        if len(run.plan) == 1:
            output, call = run.plan[0].get("output", ""), None
        else:
            project = db.get(Project, run.project_id) if run.project_id else None
            call = self._call(db, run, ctx, agent, project, prompts.final_prompt(run), step=len(run.plan) + 1)
            output = call.text
        with self._sessions() as write:
            locked = _lock(write, run.id)
            if not _still_ours(locked, self._worker):
                return
            if call is not None:
                locked.steps_used += 1
                locked.cost_usd += call.cost
            locked.output = output
            locked.status = "succeeded"
            locked.finished_at = utcnow()
            locked.lease_owner = None
            locked.lease_expires_at = None
            locked.version += 1
            data = {"cost_usd": str(locked.cost_usd), "steps_used": locked.steps_used}
            add_event(
                write, locked, "completed", data=data, ai_request_id=call.ai_request_id if call else None
            )
            if agent.autonomy == "execute_with_approval":
                self._request_review(write, locked, agent)
            write.commit()

    def _request_review(self, db: Session, run: AgentRun, agent: Agent) -> None:
        """Raises an "AI output" approval, requested by the agent (no user), so anyone allowed to decide
        approvals, including the person who started the run, can review it (D49)."""
        title = f"Review {agent.name}'s work: {run.goal}"
        approval = Approval(
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            kind="ai_output",
            title=title if len(title) <= 200 else title[:199] + "…",
            description=run.output[:20_000],
            payload={
                "agent": agent.key,
                "agent_run_id": str(run.id),
                "started_by_user_id": str(run.started_by_user_id),
            },
        )
        db.add(approval)
        db.flush()
        run.approval_id = approval.id
        add_event(db, run, "review_requested", data={"approval_id": str(approval.id)})
        record_event(
            db,
            verb="approval.requested",
            entity_type="approval",
            entity_id=approval.id,
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            summary=f"{agent.name} asked for its work to be reviewed: {approval.title}",
            changes={"kind": "ai_output", "agent_run_id": str(run.id)},
            meta=RequestMeta(request_id=None, ip=None, user_agent=None),
        )

    # ------------------------------------------------------------------ helpers

    def _context(self, db: Session, ctx: WorkspaceContext, query: str, project: Project | None) -> str:
        try:
            return assemble_context(
                db, ctx, query, project=project, budget_tokens=CONTEXT_BUDGET_TOKENS
            ).render()
        except ProblemError:
            return ""  # e.g. a query with no searchable words

    def _call(
        self,
        db: Session,
        run: AgentRun,
        ctx: WorkspaceContext,
        agent: Agent,
        project: Project | None,
        prompt: str,
        *,
        step: int,
    ) -> Call:
        meta = RequestMeta(request_id=f"agent-run:{run.id}:{step}", ip=None, user_agent=None)
        system = prompts.system_prompt(agent, ctx.workspace.name)
        for attempt in range(1, MAX_CALL_ATTEMPTS + 1):
            try:
                result = gateway.complete(
                    db,
                    ctx,
                    meta,
                    self._providers,
                    task_key=agent.task_key,
                    messages=[ChatMessage(role="user", content=prompt)],
                    system=system,
                    project=project,
                )
            except ProblemError as error:
                code = str(error.extra.get("code") or f"http_{error.status}")
                if code in RETRYABLE and attempt < MAX_CALL_ATTEMPTS:
                    self._event(run.id, "step_retried", {"n": step, "attempt": attempt, "reason": code})
                    self._sleep(2.0**attempt)
                    continue
                raise RunStoppedError(code, error.detail or str(error)) from None
            if result.status == "refused":
                raise RunStoppedError(
                    "refused",
                    f"The model declined this request ({result.refusal_category or 'no category'}).",
                )
            return Call(text=result.text, cost=result.cost_usd, ai_request_id=result.request_id)
        raise AssertionError("unreachable")  # pragma: no cover

    def _event(self, run_id: uuid.UUID, type_: str, data: dict[str, Any]) -> None:
        with self._sessions() as db:
            add_event(db, _lock(db, run_id), type_, data=data)
            db.commit()

    def _commit_unit(
        self,
        run_id: uuid.UUID,
        call: Call,
        apply: Callable[[AgentRun], Any],
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Records a finished unit of work. Its result is kept even if the run was paused meanwhile; the
        lease is renewed only if the run is still ours to continue."""
        with self._sessions() as db:
            locked = _lock(db, run_id)
            apply(locked)
            locked.steps_used += 1
            locked.cost_usd += call.cost
            locked.version += 1
            if _still_ours(locked, self._worker):
                locked.lease_expires_at = utcnow() + LEASE
            add_event(
                db, locked, event, data={**data, "cost_usd": str(call.cost)}, ai_request_id=call.ai_request_id
            )
            db.commit()

    def _fail(self, run_id: uuid.UUID, code: str, detail: str) -> None:
        with self._sessions() as db:
            locked = _lock(db, run_id)
            if locked.status in {"succeeded", "failed", "cancelled"}:
                return
            if locked.status == "paused":
                # Paused by a person while this step was running: record the failure and leave the
                # decision (resume or cancel) to them.
                add_event(db, locked, "step_failed", data={"code": code, "detail": detail[:1_000]})
                db.commit()
                return
            locked.status = "failed"
            locked.error_code = code
            locked.error_detail = detail[:1_000]
            locked.finished_at = utcnow()
            locked.lease_owner = None
            locked.lease_expires_at = None
            locked.version += 1
            add_event(db, locked, "failed", data={"code": code, "detail": detail[:1_000]})
            db.commit()
