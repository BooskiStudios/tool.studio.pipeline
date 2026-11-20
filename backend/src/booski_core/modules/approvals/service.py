"""Approval rules, enforced here rather than in any client:

* Requesting needs ``approvals.request`` where the request lives.
* Deciding (approve, reject, request changes) needs ``approvals.decide`` (owners, admins), or being the
  assigned reviewer with ``approvals.review_assigned`` (developers). Project access applies to both.
* Nobody can decide their own request, whatever their role.
* Reject and request-changes need a comment, so the requester knows why.
* Every action is kept in ``approval_reviews`` (append-only) and in the activity log.
"""

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, get_project, project_capabilities, project_scope
from booski_core.access.roles import SEES_ALL_PROJECTS, Capability, Role, has_capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.core.schemas import attributes
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.approvals.models import Approval, ApprovalReview
from booski_core.modules.approvals.schemas import (
    ApprovalCreate,
    ApprovalOut,
    ApprovalUpdate,
    ResubmitBody,
    ReviewCreate,
    ReviewOut,
)
from booski_core.modules.decisions.service import get_decision
from booski_core.modules.knowledge.service import get_document
from booski_core.modules.milestones.service import get_milestone
from booski_core.modules.projects.models import Project, ProjectMember
from booski_core.modules.tasks.service import get_task
from booski_core.modules.workspaces.models import Membership

APPROVAL_NOT_FOUND = "Approval not found."
OPEN = ("pending", "changes_requested")


def _scoped(ctx: WorkspaceContext) -> Select[Approval]:
    return select(Approval).where(
        Approval.workspace_id == ctx.workspace.id, project_scope(ctx, Approval.project_id)
    )


def get_approval(db: Session, ctx: WorkspaceContext, approval_id: uuid.UUID) -> Approval:
    approval = db.scalars(_scoped(ctx).where(Approval.id == approval_id)).one_or_none()
    if approval is None:
        raise ProblemError(404, APPROVAL_NOT_FOUND)
    return approval


def _project(db: Session, approval: Approval) -> Project | None:
    return db.get(Project, approval.project_id) if approval.project_id else None


def can_decide(db: Session, ctx: WorkspaceContext, approval: Approval) -> bool:
    if approval.status != "pending" or approval.requested_by_user_id == ctx.auth.user.id:
        return False
    caps = project_capabilities(db, ctx, _project(db, approval))
    if Capability.APPROVALS_DECIDE in caps:
        return True
    return approval.reviewer_user_id == ctx.auth.user.id and Capability.APPROVALS_REVIEW_ASSIGNED in caps


def to_out(db: Session, ctx: WorkspaceContext, approvals: list[Approval]) -> list[ApprovalOut]:
    return [
        ApprovalOut.model_validate({**attributes(a, ApprovalOut), "can_decide": can_decide(db, ctx, a)})
        for a in approvals
    ]


def list_approvals(
    db: Session,
    ctx: WorkspaceContext,
    *,
    statuses: list[str] | None,
    kinds: list[str] | None,
    project: Project | None,
    reviewer: Literal["me"] | uuid.UUID | None,
    requested_by: Literal["me"] | uuid.UUID | None,
    subject_type: str | None,
    subject_id: uuid.UUID | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[Approval], str | None]:
    me = ctx.auth.user.id
    filters: list[ColumnElement[bool]] = []
    if statuses:
        filters.append(Approval.status.in_(statuses))
    if kinds:
        filters.append(Approval.kind.in_(kinds))
    if project is not None:
        filters.append(Approval.project_id == project.id)
    if reviewer is not None:
        filters.append(Approval.reviewer_user_id == (me if reviewer == "me" else reviewer))
    if requested_by is not None:
        filters.append(Approval.requested_by_user_id == (me if requested_by == "me" else requested_by))
    if subject_type is not None:
        filters.append(Approval.subject_type == subject_type)
    if subject_id is not None:
        filters.append(Approval.subject_id == subject_id)
    rows, next_cursor = paginate(
        db,
        _scoped(ctx).where(*filters),
        key=SortKey(Approval.created_at, datetime.fromisoformat),
        id_column=Approval.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda a: a.created_at,
        row_id=lambda a: a.id,
    )
    return list(rows), next_cursor


# ---------------------------------------------------------------- validation


def _subject_project(
    db: Session, ctx: WorkspaceContext, subject_type: str, subject_id: uuid.UUID
) -> uuid.UUID | None:
    """Checks the subject exists in this workspace and is visible; returns the project it belongs to."""
    try:
        if subject_type == "task":
            return get_task(db, ctx, subject_id).project_id
        if subject_type == "document":
            return get_document(db, ctx, subject_id).project_id
        if subject_type == "decision":
            return get_decision(db, ctx, subject_id).project_id
        if subject_type == "milestone":
            return get_milestone(db, ctx, subject_id)[0].project_id
        return get_project(db, ctx, project_id=subject_id).id
    except ProblemError:
        raise ProblemError(
            422, f"The {subject_type} this approval is about doesn't exist in this workspace."
        ) from None


def _check_reviewer(
    db: Session,
    ctx: WorkspaceContext,
    reviewer_id: uuid.UUID,
    requester_id: uuid.UUID | None,
    project: Project | None,
) -> None:
    if reviewer_id == requester_id:
        raise ProblemError(422, "You can't review your own request. Choose someone else.")
    role_value = db.scalar(
        select(Membership.role).where(
            Membership.workspace_id == ctx.workspace.id, Membership.user_id == reviewer_id
        )
    )
    if role_value is None:
        raise ProblemError(422, "The reviewer isn't a member of this workspace.")
    role = Role(role_value)
    if not (
        has_capability(role, Capability.APPROVALS_DECIDE)
        or has_capability(role, Capability.APPROVALS_REVIEW_ASSIGNED)
    ):
        raise ProblemError(422, "The reviewer's role can't decide approvals.")
    if project is not None and role not in SEES_ALL_PROJECTS:
        access = db.scalar(
            select(ProjectMember.access).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == reviewer_id
            )
        )
        if (project.visibility == "restricted" and access is None) or access == "viewer":
            raise ProblemError(422, "The reviewer can't act in this project.")


def _review(
    db: Session, ctx: WorkspaceContext, approval: Approval, action: str, comment: str, meta: RequestMeta
) -> None:
    db.add(
        ApprovalReview(
            workspace_id=ctx.workspace.id,
            approval_id=approval.id,
            actor_user_id=ctx.auth.user.id,
            action=action,
            comment=comment,
        )
    )
    bump_version(approval)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb=f"approval.{action}",
        entity_type="approval",
        entity_id=approval.id,
        project_id=approval.project_id,
        summary=f"{action.replace('_', ' ').capitalize()}: {approval.title}",
        changes={"status": approval.status, "comment": comment[:500]}
        if comment
        else {"status": approval.status},
    )


# ---------------------------------------------------------------- actions


def request_approval(db: Session, ctx: WorkspaceContext, body: ApprovalCreate, meta: RequestMeta) -> Approval:
    if (body.subject_type is None) != (body.subject_id is None):
        raise ProblemError(422, "Send both subject_type and subject_id, or neither.")
    project_id = body.project_id
    if body.subject_type is not None and body.subject_id is not None:
        subject_project = _subject_project(db, ctx, body.subject_type, body.subject_id)
        if project_id is not None and subject_project is not None and project_id != subject_project:
            raise ProblemError(422, "project_id doesn't match the project of the subject.")
        project_id = project_id or subject_project
    project = get_optional_project(db, ctx, project_id)
    if Capability.APPROVALS_REQUEST not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Your role doesn't allow requesting approvals here.")
    if body.reviewer_user_id is not None:
        _check_reviewer(db, ctx, body.reviewer_user_id, ctx.auth.user.id, project)
    approval = Approval(
        workspace_id=ctx.workspace.id,
        requested_by_user_id=ctx.auth.user.id,
        **body.model_dump(exclude={"project_id"}),
        project_id=project_id,
    )
    db.add(approval)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="approval.requested",
        entity_type="approval",
        entity_id=approval.id,
        project_id=approval.project_id,
        summary=f"Requested approval: {approval.title}",
        changes={"kind": approval.kind, "reviewer_user_id": approval.reviewer_user_id},
    )
    return approval


def review(
    db: Session, ctx: WorkspaceContext, approval: Approval, body: ReviewCreate, meta: RequestMeta
) -> Approval:
    if body.action == "comment":
        involved = ctx.auth.user.id in (approval.requested_by_user_id, approval.reviewer_user_id)
        caps = project_capabilities(db, ctx, _project(db, approval))
        if not (involved or Capability.APPROVALS_DECIDE in caps):
            raise ProblemError(403, "Only the requester, the reviewer, owners and admins can comment here.")
        if not body.comment:
            raise ProblemError(422, "Write a comment.")
        _review(db, ctx, approval, "commented", body.comment, meta)
        db.flush()
        return approval

    if approval.status != "pending":
        raise ProblemError(
            409, f"This request is {approval.status.replace('_', ' ')}, so it can't be decided now."
        )
    if approval.requested_by_user_id == ctx.auth.user.id:
        raise ProblemError(403, "You can't decide your own request.")
    if not can_decide(db, ctx, approval):
        raise ProblemError(403, "Only owners, admins or the assigned reviewer can decide this request.")
    if body.action in ("reject", "request_changes") and not body.comment:
        raise ProblemError(422, "Explain why, so the requester knows what to change.")

    if body.action == "request_changes":
        approval.status = "changes_requested"
        _review(db, ctx, approval, "changes_requested", body.comment, meta)
    else:
        approval.status = "approved" if body.action == "approve" else "rejected"
        approval.resolved_at = utcnow()
        approval.resolved_by_user_id = ctx.auth.user.id
        approval.resolution_comment = body.comment
        _review(db, ctx, approval, approval.status, body.comment, meta)
        _decide_agent_changes(db, ctx, approval)
    db.flush()
    return approval


def _decide_agent_changes(db: Session, ctx: WorkspaceContext, approval: Approval) -> None:
    """An agent run's review (PR 3.5, D57): approving applies every change the run proposed, as the person
    who started the run; rejecting applies none. Imported here to keep the approvals module independent."""
    run_id = approval.payload.get("agent_run_id") if approval.kind == "ai_output" else None
    if not run_id:
        return
    from booski_core.modules.tools.apply import decide_run_changes

    decide_run_changes(
        db, uuid.UUID(str(run_id)), approved=approval.status == "approved", decided_by=ctx.auth.user.id
    )


def resubmit(
    db: Session, ctx: WorkspaceContext, approval: Approval, body: ResubmitBody, meta: RequestMeta
) -> Approval:
    if approval.requested_by_user_id != ctx.auth.user.id:
        raise ProblemError(403, "Only the requester can resubmit.")
    if approval.status != "changes_requested":
        raise ProblemError(409, "Only requests with changes requested can be resubmitted.")
    if body.description is not None:
        approval.description = body.description
    if body.payload is not None:
        approval.payload = body.payload
    approval.status = "pending"
    _review(db, ctx, approval, "resubmitted", body.comment, meta)
    db.flush()
    return approval


def cancel(
    db: Session, ctx: WorkspaceContext, approval: Approval, comment: str, meta: RequestMeta
) -> Approval:
    is_requester = approval.requested_by_user_id == ctx.auth.user.id
    if not is_requester and Capability.APPROVALS_DECIDE not in project_capabilities(
        db, ctx, _project(db, approval)
    ):
        raise ProblemError(403, "Only the requester, owners and admins can cancel a request.")
    if approval.status not in OPEN:
        raise ProblemError(409, "This request is already resolved.")
    approval.status = "cancelled"
    approval.resolved_at = utcnow()
    approval.resolved_by_user_id = ctx.auth.user.id
    approval.resolution_comment = comment
    _review(db, ctx, approval, "cancelled", comment, meta)
    _decide_agent_changes(db, ctx, approval)  # a cancelled review applies nothing
    db.flush()
    return approval


def update_approval(
    db: Session, ctx: WorkspaceContext, approval: Approval, body: ApprovalUpdate, meta: RequestMeta
) -> Approval:
    is_requester = approval.requested_by_user_id == ctx.auth.user.id
    project = _project(db, approval)
    if not is_requester and Capability.APPROVALS_DECIDE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Only the requester, owners and admins can reassign a request.")
    if approval.status not in OPEN:
        raise ProblemError(409, "This request is already resolved.")
    check_version(approval, body.version)
    sent = body.model_dump(exclude_unset=True, exclude={"version"})
    if sent.get("reviewer_user_id") is not None:
        _check_reviewer(db, ctx, sent["reviewer_user_id"], approval.requested_by_user_id, project)
    diff = {k: {"from": getattr(approval, k), "to": v} for k, v in sent.items() if getattr(approval, k) != v}
    if not diff:
        return approval
    for key in diff:
        setattr(approval, key, sent[key])
    bump_version(approval)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="approval.reassigned" if "reviewer_user_id" in diff else "approval.updated",
        entity_type="approval",
        entity_id=approval.id,
        project_id=approval.project_id,
        summary=f"Updated approval request {approval.title}",
        changes=diff,
    )
    db.flush()
    return approval


def list_reviews(db: Session, approval: Approval) -> list[ReviewOut]:
    rows = db.scalars(
        select(ApprovalReview)
        .where(ApprovalReview.approval_id == approval.id)
        .order_by(ApprovalReview.created_at, ApprovalReview.id)
    )
    return [ReviewOut.model_validate(attributes(r, ReviewOut)) for r in rows]
