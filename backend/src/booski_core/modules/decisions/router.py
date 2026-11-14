import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.activity.schemas import ActivityOut
from booski_core.modules.activity.service import entity_history
from booski_core.modules.decisions import service
from booski_core.modules.decisions.schemas import DecisionCreate, DecisionOut, DecisionUpdate
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.vocab import DecisionStatus

router = APIRouter(prefix="/w/{workspace_slug}/decisions", tags=["decisions"])


@router.get("", response_model=Page[DecisionOut])
def list_decisions(
    ctx: MemberContext,
    db: DbSession,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    department: Annotated[str | None, Query(description="Department slug.")] = None,
    status: Annotated[list[DecisionStatus] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[DecisionOut]:
    """The Decision Log, most recently recorded first."""
    rows, next_cursor = service.list_decisions(
        db,
        ctx,
        project=get_project(db, ctx, slug=project) if project else None,
        department_id=get_department(db, ctx, slug=department).id if department else None,
        statuses=list(status) if status else None,
        q=q,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=service.to_out(db, rows), next_cursor=next_cursor)


@router.post("", response_model=DecisionOut, status_code=201)
def record_decision(body: DecisionCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> DecisionOut:
    decision = service.create_decision(db, ctx, body, meta)
    db.commit()
    db.refresh(decision)
    return service.to_out(db, [decision])[0]


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> DecisionOut:
    return service.to_out(db, [service.get_decision(db, ctx, decision_id)])[0]


@router.patch("/{decision_id}", response_model=DecisionOut)
def update_decision(
    decision_id: uuid.UUID, body: DecisionUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> DecisionOut:
    decision = service.update_decision(db, ctx, service.get_decision(db, ctx, decision_id), body, meta)
    db.commit()
    db.refresh(decision)
    return service.to_out(db, [decision])[0]


@router.get("/{decision_id}/history", response_model=Page[ActivityOut])
def decision_history(
    decision_id: uuid.UUID, ctx: MemberContext, db: DbSession, limit: Limit = 50, cursor: Cursor = None
) -> Page[ActivityOut]:
    """Every change to this decision, newest first."""
    decision = service.get_decision(db, ctx, decision_id)
    items, next_cursor = entity_history(db, ctx, "decision", decision.id, limit=limit, cursor=cursor)
    return Page(items=items, next_cursor=next_cursor)
