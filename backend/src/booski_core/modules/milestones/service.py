import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_project, require_capability
from booski_core.access.roles import Capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.core.schemas import attributes
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.milestones.models import Milestone
from booski_core.modules.milestones.schemas import MilestoneCreate, MilestoneOut, MilestoneUpdate
from booski_core.modules.projects.models import Project
from booski_core.modules.tasks.progress import milestone_progress

NOT_ALLOWED = "Your role doesn't allow changing milestones in this project."


def to_out(db: Session, milestones: list[Milestone]) -> list[MilestoneOut]:
    progress = milestone_progress(db, [m.id for m in milestones])
    return [
        MilestoneOut.model_validate({**attributes(m, MilestoneOut), "progress": progress[m.id]})
        for m in milestones
    ]


def list_milestones(db: Session, project: Project, *, include_archived: bool) -> list[Milestone]:
    query = select(Milestone).where(Milestone.project_id == project.id)
    if not include_archived:
        query = query.where(Milestone.archived_at.is_(None))
    return list(db.scalars(query.order_by(Milestone.position, Milestone.target_date, Milestone.created_at)))


def get_milestone(db: Session, ctx: WorkspaceContext, milestone_id: uuid.UUID) -> tuple[Milestone, Project]:
    """Loads a milestone in this workspace whose project the caller can see; 404 otherwise."""
    milestone = db.scalars(
        select(Milestone).where(Milestone.id == milestone_id, Milestone.workspace_id == ctx.workspace.id)
    ).one_or_none()
    if milestone is None:
        raise ProblemError(404, "Milestone not found.")
    try:
        project = get_project(db, ctx, project_id=milestone.project_id)
    except ProblemError:
        raise ProblemError(404, "Milestone not found.") from None
    return milestone, project


def _apply_status(milestone: Milestone, status: str) -> None:
    milestone.status = status
    milestone.completed_at = (milestone.completed_at or utcnow()) if status == "completed" else None


def create_milestone(
    db: Session, ctx: WorkspaceContext, project: Project, body: MilestoneCreate, meta: RequestMeta
) -> Milestone:
    require_capability(db, ctx, project, Capability.MILESTONES_WRITE, NOT_ALLOWED)
    position = body.position
    if position is None:
        highest = db.scalar(select(func.max(Milestone.position)).where(Milestone.project_id == project.id))
        position = float(highest) + 1 if highest is not None else 0.0
    milestone = Milestone(
        workspace_id=ctx.workspace.id,
        project_id=project.id,
        created_by_user_id=ctx.auth.user.id,
        **body.model_dump(exclude={"status", "position"}),
        position=position,
    )
    _apply_status(milestone, body.status)
    db.add(milestone)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="milestone.created",
        entity_type="milestone",
        entity_id=milestone.id,
        project_id=project.id,
        summary=f"Created milestone {milestone.name}",
    )
    return milestone


def update_milestone(
    db: Session,
    ctx: WorkspaceContext,
    milestone: Milestone,
    project: Project,
    body: MilestoneUpdate,
    meta: RequestMeta,
) -> Milestone:
    require_capability(db, ctx, project, Capability.MILESTONES_WRITE, NOT_ALLOWED)
    check_version(milestone, body.version)
    fields = body.model_dump(exclude_unset=True, exclude={"archived", "version", "status"})
    diff: dict[str, Any] = {
        k: {"from": getattr(milestone, k), "to": v} for k, v in fields.items() if getattr(milestone, k) != v
    }
    for key, value in fields.items():
        setattr(milestone, key, value)
    completed_now = False
    if body.status is not None and body.status != milestone.status:
        diff["status"] = {"from": milestone.status, "to": body.status}
        completed_now = body.status == "completed"
        _apply_status(milestone, body.status)
    if body.archived is not None and body.archived != (milestone.archived_at is not None):
        milestone.archived_at = utcnow() if body.archived else None
        diff["archived"] = {"from": not body.archived, "to": body.archived}
    if not diff:
        return milestone
    bump_version(milestone)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="milestone.completed" if completed_now else "milestone.updated",
        entity_type="milestone",
        entity_id=milestone.id,
        project_id=project.id,
        summary=f"{'Completed' if completed_now else 'Updated'} milestone {milestone.name}",
        changes=diff,
    )
    db.flush()
    return milestone
