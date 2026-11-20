"""Applying (or rejecting) the changes an agent run proposed, when a person decides the run's review (D57).

Approve: every proposed change is applied in one savepoint, through the same services the API uses, as the
person who started the run, so their **current** permissions are checked again. If any change can't be
applied, none is, and each is marked failed with the reason. Reject: none is applied.
"""

import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext, member_context
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta
from booski_core.modules.agents.models import AgentRun, AgentRunChange
from booski_core.modules.agents.orchestrator import add_event
from booski_core.modules.decisions.schemas import DecisionCreate
from booski_core.modules.decisions.service import create_decision
from booski_core.modules.knowledge.schemas import DocumentCreate
from booski_core.modules.knowledge.service import create_document
from booski_core.modules.tasks.schemas import TaskCreate
from booski_core.modules.tasks.service import create_task


def _apply_one(db: Session, ctx: WorkspaceContext, change: AgentRunChange, meta: RequestMeta) -> list[str]:
    if change.tool == "create_document":
        return [str(create_document(db, ctx, DocumentCreate.model_validate(change.payload), meta).id)]
    if change.tool == "create_tasks":
        tasks = [TaskCreate.model_validate(t) for t in change.payload.get("tasks", [])]
        return [str(create_task(db, ctx, t, meta).id) for t in tasks]
    if change.tool == "propose_decision":
        body = DecisionCreate.model_validate({**change.payload, "status": "proposed"})
        return [str(create_decision(db, ctx, body, meta).id)]
    raise ProblemError(422, f"Unknown change type {change.tool!r}.")  # pragma: no cover


def proposed_changes(db: Session, run_id: uuid.UUID) -> list[AgentRunChange]:
    return list(
        db.scalars(
            select(AgentRunChange)
            .where(AgentRunChange.run_id == run_id, AgentRunChange.status == "proposed")
            .order_by(AgentRunChange.seq)
        )
    )


def decide_run_changes(
    db: Session, run_id: uuid.UUID, *, approved: bool, decided_by: uuid.UUID
) -> dict[str, Any]:
    """Applies or rejects the run's proposed changes. Returns a summary for the run's event log."""
    run = db.scalars(select(AgentRun).where(AgentRun.id == run_id).with_for_update()).one()
    changes = proposed_changes(db, run.id)
    if not changes:
        return {"changes": 0}
    if not approved:
        for change in changes:
            change.status = "rejected"
        add_event(db, run, "changes_rejected", actor_user_id=decided_by, data={"changes": len(changes)})
        return {"changes": len(changes), "status": "rejected"}

    meta = RequestMeta(request_id=f"agent-run:{run.id}:apply", ip=None, user_agent=None)
    ctx = member_context(db, run.workspace_id, run.started_by_user_id)
    error: str | None = None
    if ctx is None:
        error = "The person who started this run is no longer an active member."
    else:
        try:
            with db.begin_nested():
                for change in changes:
                    change.applied_ids = _apply_one(db, ctx, change, meta)
                    change.status = "applied"
                db.flush()
        except (ProblemError, ValidationError) as exc:
            error = exc.detail if isinstance(exc, ProblemError) and exc.detail else str(exc)
    if error is not None:
        for change in changes:  # the savepoint rolled back every write; record why
            change.status = "failed"
            change.applied_ids = []
            change.error = error[:1_000]
        add_event(
            db,
            run,
            "changes_failed",
            actor_user_id=decided_by,
            data={"changes": len(changes), "error": error[:1_000]},
        )
        return {"changes": len(changes), "status": "failed", "error": error}
    add_event(
        db,
        run,
        "changes_applied",
        actor_user_id=decided_by,
        data={"changes": len(changes), "records": sum(len(c.applied_ids) for c in changes)},
    )
    return {"changes": len(changes), "status": "applied"}


def discard_run_changes(db: Session, run_id: uuid.UUID) -> None:
    """Marks a failed or cancelled run's proposals as discarded: they can never be applied."""
    for change in proposed_changes(db, run_id):
        change.status = "discarded"
