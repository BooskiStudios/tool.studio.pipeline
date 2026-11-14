import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, delete, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, project_capabilities, project_scope
from booski_core.access.roles import Capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.core.schemas import attributes
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.decisions.models import Decision, DecisionDocument
from booski_core.modules.decisions.schemas import DecisionCreate, DecisionOut, DecisionUpdate
from booski_core.modules.departments.service import get_optional_department
from booski_core.modules.knowledge.service import get_document
from booski_core.modules.projects.models import Project

DECISION_NOT_FOUND = "Decision not found."
DECIDED = ("accepted", "rejected")


def _scoped(ctx: WorkspaceContext) -> Select[Decision]:
    return select(Decision).where(
        Decision.workspace_id == ctx.workspace.id, project_scope(ctx, Decision.project_id)
    )


def get_decision(db: Session, ctx: WorkspaceContext, decision_id: uuid.UUID) -> Decision:
    decision = db.scalars(_scoped(ctx).where(Decision.id == decision_id)).one_or_none()
    if decision is None:
        raise ProblemError(404, DECISION_NOT_FOUND)
    return decision


def to_out(db: Session, decisions: list[Decision]) -> list[DecisionOut]:
    ids = [d.id for d in decisions]
    documents: dict[uuid.UUID, list[uuid.UUID]] = {i: [] for i in ids}
    for decision_id, document_id in db.execute(
        select(DecisionDocument.decision_id, DecisionDocument.document_id).where(
            DecisionDocument.decision_id.in_(ids)
        )
    ):
        documents[decision_id].append(document_id)
    superseded_by = {
        old: new
        for old, new in db.execute(
            select(Decision.supersedes_decision_id, Decision.id).where(
                Decision.supersedes_decision_id.in_(ids), Decision.status == "accepted"
            )
        )
    }
    return [
        DecisionOut.model_validate(
            {
                **attributes(d, DecisionOut),
                "document_ids": documents[d.id],
                "superseded_by_decision_id": superseded_by.get(d.id),
            }
        )
        for d in decisions
    ]


def list_decisions(
    db: Session,
    ctx: WorkspaceContext,
    *,
    project: Project | None,
    department_id: uuid.UUID | None,
    statuses: list[str] | None,
    q: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[Decision], str | None]:
    filters: list[ColumnElement[bool]] = []
    if project is not None:
        filters.append(Decision.project_id == project.id)
    if department_id is not None:
        filters.append(Decision.department_id == department_id)
    if statuses:
        filters.append(Decision.status.in_(statuses))
    if q:
        filters.append(Decision.title.icontains(q, autoescape=True))
    rows, next_cursor = paginate(
        db,
        _scoped(ctx).where(*filters),
        key=SortKey(Decision.recorded_at, datetime.fromisoformat),
        id_column=Decision.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda d: d.recorded_at,
        row_id=lambda d: d.id,
    )
    return list(rows), next_cursor


def _require_write(db: Session, ctx: WorkspaceContext, project: Project | None) -> None:
    if Capability.DECISIONS_WRITE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Your role doesn't allow recording decisions here.")


def _set_documents(
    db: Session, ctx: WorkspaceContext, decision: Decision, document_ids: list[uuid.UUID]
) -> None:
    unique_ids = list(dict.fromkeys(document_ids))
    for document_id in unique_ids:
        try:
            get_document(db, ctx, document_id)  # same workspace, and visible to the caller
        except ProblemError:
            raise ProblemError(
                422, f"Supporting document {document_id} doesn't exist in this workspace."
            ) from None
    db.execute(delete(DecisionDocument).where(DecisionDocument.decision_id == decision.id))
    for document_id in unique_ids:
        db.add(
            DecisionDocument(decision_id=decision.id, document_id=document_id, workspace_id=ctx.workspace.id)
        )


def _supersede(db: Session, ctx: WorkspaceContext, decision: Decision, meta: RequestMeta) -> None:
    """When a decision that replaces another is accepted, the older one is marked superseded."""
    if decision.status != "accepted" or decision.supersedes_decision_id is None:
        return
    older = db.get_one(Decision, decision.supersedes_decision_id)
    if older.status != "superseded":
        older.status = "superseded"
        bump_version(older)
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="decision.superseded",
            entity_type="decision",
            entity_id=older.id,
            project_id=older.project_id,
            summary=f"{older.title} was superseded by {decision.title}",
            changes={"superseded_by_decision_id": decision.id},
        )


def create_decision(db: Session, ctx: WorkspaceContext, body: DecisionCreate, meta: RequestMeta) -> Decision:
    project = get_optional_project(db, ctx, body.project_id)
    _require_write(db, ctx, project)
    get_optional_department(db, ctx, body.department_id)
    if body.supersedes_decision_id is not None:
        older = get_decision(db, ctx, body.supersedes_decision_id)
        # Superseding changes the older decision too, so you must be allowed to write where it lives.
        _require_write(db, ctx, db.get(Project, older.project_id) if older.project_id else None)
    decision = Decision(
        workspace_id=ctx.workspace.id,
        author_user_id=ctx.auth.user.id,
        decided_at=utcnow() if body.status in DECIDED else None,
        **body.model_dump(exclude={"document_ids", "options"}),
        options=[o.model_dump() for o in body.options],
    )
    db.add(decision)
    db.flush()
    _set_documents(db, ctx, decision, body.document_ids)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="decision.recorded",
        entity_type="decision",
        entity_id=decision.id,
        project_id=decision.project_id,
        summary=f"Recorded decision {decision.title}",
        changes={"status": decision.status},
    )
    _supersede(db, ctx, decision, meta)
    db.flush()
    return decision


def update_decision(
    db: Session, ctx: WorkspaceContext, decision: Decision, body: DecisionUpdate, meta: RequestMeta
) -> Decision:
    project = db.get(Project, decision.project_id) if decision.project_id else None
    _require_write(db, ctx, project)
    check_version(decision, body.version)
    sent = body.model_dump(exclude_unset=True, exclude={"version", "document_ids", "options"})
    if body.options is not None:
        sent["options"] = [o.model_dump() for o in body.options]
    if sent.get("department_id") is not None:
        get_optional_department(db, ctx, sent["department_id"])
    diff: dict[str, Any] = {
        k: {"from": getattr(decision, k), "to": v} for k, v in sent.items() if getattr(decision, k) != v
    }
    for key in diff:
        setattr(decision, key, sent[key])
    if "status" in diff:
        decision.decided_at = utcnow() if decision.status in DECIDED else decision.decided_at
    if body.document_ids is not None:
        _set_documents(db, ctx, decision, body.document_ids)
        diff["document_ids"] = {"to": body.document_ids}
    if not diff:
        return decision
    bump_version(decision)
    verb = "decision.status_changed" if set(diff) == {"status"} else "decision.updated"
    record_workspace_event(
        db,
        ctx,
        meta,
        verb=verb,
        entity_type="decision",
        entity_id=decision.id,
        project_id=decision.project_id,
        summary=f"Updated decision {decision.title}",
        changes=diff,
    )
    _supersede(db, ctx, decision, meta)
    db.flush()
    return decision
