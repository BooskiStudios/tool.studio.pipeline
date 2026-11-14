import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.approvals import service
from booski_core.modules.approvals.schemas import (
    ApprovalCreate,
    ApprovalOut,
    ApprovalUpdate,
    CancelBody,
    ResubmitBody,
    ReviewCreate,
    ReviewOut,
)
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.vocab import ApprovalKind, ApprovalStatus, ApprovalSubjectType

router = APIRouter(prefix="/w/{workspace_slug}/approvals", tags=["approvals"])

MeOrUser = Annotated[Literal["me"] | uuid.UUID | None, Query(description="`me` or a user id.")]


@router.get("", response_model=Page[ApprovalOut])
def list_approvals(
    ctx: MemberContext,
    db: DbSession,
    status: Annotated[list[ApprovalStatus] | None, Query()] = None,
    kind: Annotated[list[ApprovalKind] | None, Query()] = None,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    reviewer: MeOrUser = None,
    requested_by: MeOrUser = None,
    subject_type: ApprovalSubjectType | None = None,
    subject_id: uuid.UUID | None = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[ApprovalOut]:
    """Approval requests you can see, newest first. ``can_decide`` says whether you may decide each one."""
    rows, next_cursor = service.list_approvals(
        db,
        ctx,
        statuses=list(status) if status else None,
        kinds=list(kind) if kind else None,
        project=get_project(db, ctx, slug=project) if project else None,
        reviewer=reviewer,
        requested_by=requested_by,
        subject_type=subject_type,
        subject_id=subject_id,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=service.to_out(db, ctx, rows), next_cursor=next_cursor)


@router.post("", response_model=ApprovalOut, status_code=201)
def request_approval(body: ApprovalCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> ApprovalOut:
    approval = service.request_approval(db, ctx, body, meta)
    db.commit()
    db.refresh(approval)
    return service.to_out(db, ctx, [approval])[0]


@router.get("/{approval_id}", response_model=ApprovalOut)
def get_approval(approval_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> ApprovalOut:
    return service.to_out(db, ctx, [service.get_approval(db, ctx, approval_id)])[0]


@router.patch("/{approval_id}", response_model=ApprovalOut)
def update_approval(
    approval_id: uuid.UUID, body: ApprovalUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> ApprovalOut:
    """Reassigns or reschedules an open request."""
    approval = service.update_approval(db, ctx, service.get_approval(db, ctx, approval_id), body, meta)
    db.commit()
    db.refresh(approval)
    return service.to_out(db, ctx, [approval])[0]


@router.get("/{approval_id}/reviews", response_model=list[ReviewOut])
def list_reviews(approval_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> list[ReviewOut]:
    """Every action taken on the request, oldest first."""
    return service.list_reviews(db, service.get_approval(db, ctx, approval_id))


@router.post("/{approval_id}/reviews", response_model=ApprovalOut, status_code=201)
def review(
    approval_id: uuid.UUID, body: ReviewCreate, ctx: MemberContext, db: DbSession, meta: Meta
) -> ApprovalOut:
    """Approve, reject, request changes or comment. Rejecting and requesting changes need a comment."""
    approval = service.review(db, ctx, service.get_approval(db, ctx, approval_id), body, meta)
    db.commit()
    db.refresh(approval)
    return service.to_out(db, ctx, [approval])[0]


@router.post("/{approval_id}/resubmit", response_model=ApprovalOut)
def resubmit(
    approval_id: uuid.UUID, body: ResubmitBody, ctx: MemberContext, db: DbSession, meta: Meta
) -> ApprovalOut:
    """Sends a request back for review after changes were requested (requester only)."""
    approval = service.resubmit(db, ctx, service.get_approval(db, ctx, approval_id), body, meta)
    db.commit()
    db.refresh(approval)
    return service.to_out(db, ctx, [approval])[0]


@router.post("/{approval_id}/cancel", response_model=ApprovalOut)
def cancel(
    approval_id: uuid.UUID, body: CancelBody, ctx: MemberContext, db: DbSession, meta: Meta
) -> ApprovalOut:
    approval = service.cancel(db, ctx, service.get_approval(db, ctx, approval_id), body.comment, meta)
    db.commit()
    db.refresh(approval)
    return service.to_out(db, ctx, [approval])[0]
