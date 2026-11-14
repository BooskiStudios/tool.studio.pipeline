import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.projects import service
from booski_core.modules.projects.schemas import (
    ProjectCreate,
    ProjectMemberOut,
    ProjectMemberSet,
    ProjectOut,
    ProjectSort,
    ProjectUpdate,
    WorkstreamCreate,
    WorkstreamOut,
    WorkstreamUpdate,
)
from booski_core.vocab import ProjectAccess, ProjectStatus

router = APIRouter(prefix="/w/{workspace_slug}/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    ctx: MemberContext,
    db: DbSession,
    status: Annotated[list[ProjectStatus] | None, Query()] = None,
    archived: Annotated[bool, Query(description="Show archived projects instead of active ones.")] = False,
    q: Annotated[str | None, Query(max_length=100, description="Search in project names.")] = None,
    sort: ProjectSort = "updated_at",
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[ProjectOut]:
    """Projects you can see (restricted projects only if you're on their access list)."""
    rows, next_cursor = service.list_projects(
        db,
        ctx,
        status=list(status) if status else None,
        archived=archived,
        q=q,
        sort=sort,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=service.to_out(db, ctx, rows), next_cursor=next_cursor)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> ProjectOut:
    project = service.create_project(db, ctx, body, meta)
    db.commit()
    db.refresh(project)
    return service.to_out(db, ctx, [project])[0]


@router.get("/{project_slug}", response_model=ProjectOut)
def get_project_detail(project_slug: str, ctx: MemberContext, db: DbSession) -> ProjectOut:
    """The project, with progress computed from its tasks and what you're allowed to do in it."""
    return service.to_out(db, ctx, [get_project(db, ctx, slug=project_slug)])[0]


@router.patch("/{project_slug}", response_model=ProjectOut)
def update_project(
    project_slug: str, body: ProjectUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> ProjectOut:
    """Edits, archives, restores or restricts a project. Send ``version`` to detect conflicting edits."""
    project = service.update_project(db, ctx, get_project(db, ctx, slug=project_slug), body, meta)
    db.commit()
    db.refresh(project)
    return service.to_out(db, ctx, [project])[0]


# ---------------------------------------------------------------- access list


@router.get("/{project_slug}/members", response_model=list[ProjectMemberOut])
def list_project_members(project_slug: str, ctx: MemberContext, db: DbSession) -> list[ProjectMemberOut]:
    """Per-project access entries. Owners and admins always have full access and aren't listed."""
    project = get_project(db, ctx, slug=project_slug)
    return [
        ProjectMemberOut(
            user_id=u.id,
            email=u.email,
            display_name=u.display_name,
            access=m.access,
            added_at=m.created_at,
        )
        for m, u in service.list_project_members(db, project)
    ]


@router.put("/{project_slug}/members/{user_id}", response_model=ProjectMemberOut)
def set_project_member(
    project_slug: str,
    user_id: uuid.UUID,
    body: ProjectMemberSet,
    ctx: MemberContext,
    db: DbSession,
    meta: Meta,
) -> ProjectMemberOut:
    """Grants or changes a workspace member's access to this project (owners and admins)."""
    project = get_project(db, ctx, slug=project_slug)
    member = service.set_project_member(db, ctx, project, user_id, body.access, meta)
    db.commit()
    access: ProjectAccess = body.access
    user = next(u for m, u in service.list_project_members(db, project) if m.user_id == member.user_id)
    return ProjectMemberOut(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        access=access,
        added_at=member.created_at,
    )


@router.delete("/{project_slug}/members/{user_id}", status_code=204)
def remove_project_member(
    project_slug: str, user_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta
) -> None:
    service.remove_project_member(db, ctx, get_project(db, ctx, slug=project_slug), user_id, meta)
    db.commit()


# ---------------------------------------------------------------- workstreams


@router.get("/{project_slug}/workstreams", response_model=list[WorkstreamOut])
def list_workstreams(
    project_slug: str, ctx: MemberContext, db: DbSession, include_archived: Annotated[bool, Query()] = False
) -> list[WorkstreamOut]:
    project = get_project(db, ctx, slug=project_slug)
    return [
        WorkstreamOut.model_validate(w)
        for w in service.list_workstreams(db, project, include_archived=include_archived)
    ]


@router.post("/{project_slug}/workstreams", response_model=WorkstreamOut, status_code=201)
def create_workstream(
    project_slug: str, body: WorkstreamCreate, ctx: MemberContext, db: DbSession, meta: Meta
) -> WorkstreamOut:
    workstream = service.create_workstream(db, ctx, get_project(db, ctx, slug=project_slug), body, meta)
    db.commit()
    db.refresh(workstream)
    return WorkstreamOut.model_validate(workstream)


@router.patch("/{project_slug}/workstreams/{workstream_id}", response_model=WorkstreamOut)
def update_workstream(
    project_slug: str,
    workstream_id: uuid.UUID,
    body: WorkstreamUpdate,
    ctx: MemberContext,
    db: DbSession,
    meta: Meta,
) -> WorkstreamOut:
    project = get_project(db, ctx, slug=project_slug)
    workstream = service.update_workstream(
        db, ctx, project, service.get_workstream(db, ctx, workstream_id), body, meta
    )
    db.commit()
    db.refresh(workstream)
    return WorkstreamOut.model_validate(workstream)
