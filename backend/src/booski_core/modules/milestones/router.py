import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.milestones import service
from booski_core.modules.milestones.schemas import MilestoneCreate, MilestoneOut, MilestoneUpdate

router = APIRouter(prefix="/w/{workspace_slug}", tags=["milestones"])


@router.get("/projects/{project_slug}/milestones", response_model=list[MilestoneOut])
def list_milestones(
    project_slug: str, ctx: MemberContext, db: DbSession, include_archived: Annotated[bool, Query()] = False
) -> list[MilestoneOut]:
    """A project's milestones in order, each with progress computed from its tasks."""
    project = get_project(db, ctx, slug=project_slug)
    return service.to_out(db, service.list_milestones(db, project, include_archived=include_archived))


@router.post("/projects/{project_slug}/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(
    project_slug: str, body: MilestoneCreate, ctx: MemberContext, db: DbSession, meta: Meta
) -> MilestoneOut:
    milestone = service.create_milestone(db, ctx, get_project(db, ctx, slug=project_slug), body, meta)
    db.commit()
    db.refresh(milestone)
    return service.to_out(db, [milestone])[0]


@router.get("/milestones/{milestone_id}", response_model=MilestoneOut)
def get_milestone(milestone_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> MilestoneOut:
    milestone, _ = service.get_milestone(db, ctx, milestone_id)
    return service.to_out(db, [milestone])[0]


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: uuid.UUID, body: MilestoneUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> MilestoneOut:
    """Edits, completes, archives or restores a milestone. Send ``version`` to detect conflicting edits."""
    milestone, project = service.get_milestone(db, ctx, milestone_id)
    service.update_milestone(db, ctx, milestone, project, body, meta)
    db.commit()
    db.refresh(milestone)
    return service.to_out(db, [milestone])[0]
