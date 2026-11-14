import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import project_capabilities, require_capability, visible_project_ids
from booski_core.access.roles import SEES_ALL_PROJECTS, Capability, Role
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.models import User
from booski_core.modules.projects.models import Project, ProjectMember, Workstream
from booski_core.modules.projects.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectSort,
    ProjectUpdate,
    WorkstreamCreate,
    WorkstreamUpdate,
)
from booski_core.modules.tasks.progress import project_progress
from booski_core.modules.workspaces.models import Membership

MANAGE_ONLY = "Only owners and admins can create or change projects."


def to_out(db: Session, ctx: WorkspaceContext, projects: list[Project]) -> list[ProjectOut]:
    progress = project_progress(db, [p.id for p in projects])
    return [
        ProjectOut.model_validate(
            {
                **{column: getattr(p, column) for column in ProjectOut.model_fields if hasattr(p, column)},
                "progress": progress[p.id],
                "capabilities": sorted(project_capabilities(db, ctx, p)),
            }
        )
        for p in projects
    ]


def _sort_key(sort: ProjectSort) -> SortKey:
    if sort == "name":
        return SortKey(Project.name, str, "asc")
    column = Project.created_at if sort == "created_at" else Project.updated_at
    return SortKey(column, datetime.fromisoformat, "desc")


def list_projects(
    db: Session,
    ctx: WorkspaceContext,
    *,
    status: list[str] | None,
    archived: bool,
    q: str | None,
    sort: ProjectSort,
    limit: int,
    cursor: str | None,
) -> tuple[list[Project], str | None]:
    query: Select[Project] = select(Project).where(Project.id.in_(visible_project_ids(ctx)))
    query = query.where(Project.archived_at.is_not(None) if archived else Project.archived_at.is_(None))
    if status:
        query = query.where(Project.status.in_(status))
    if q:
        query = query.where(Project.name.icontains(q, autoescape=True))
    key = _sort_key(sort)
    rows, next_cursor = paginate(
        db,
        query,
        key=key,
        id_column=Project.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda p: getattr(p, sort),
        row_id=lambda p: p.id,
    )
    return list(rows), next_cursor


def create_project(db: Session, ctx: WorkspaceContext, body: ProjectCreate, meta: RequestMeta) -> Project:
    require_capability(db, ctx, None, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    project = Project(workspace_id=ctx.workspace.id, created_by_user_id=ctx.auth.user.id, **body.model_dump())
    try:
        with db.begin_nested():
            db.add(project)
            db.flush()
    except IntegrityError:
        raise ProblemError(409, "A project with that address already exists in this workspace.") from None
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="project.created",
        entity_type="project",
        entity_id=project.id,
        project_id=project.id,
        summary=f"Created project {project.name}",
        changes={"visibility": project.visibility},
    )
    return project


def update_project(
    db: Session, ctx: WorkspaceContext, project: Project, body: ProjectUpdate, meta: RequestMeta
) -> Project:
    require_capability(db, ctx, project, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    check_version(project, body.version)
    fields = body.model_dump(exclude_unset=True, exclude={"archived", "version"})
    diff: dict[str, Any] = {}
    for key, value in fields.items():
        if getattr(project, key) != value:
            diff[key] = {"from": getattr(project, key), "to": value}
            setattr(project, key, value)
    archive_verb = None
    if body.archived is not None and body.archived != (project.archived_at is not None):
        project.archived_at = utcnow() if body.archived else None
        archive_verb = "project.archived" if body.archived else "project.restored"
    if not diff and archive_verb is None:
        return project
    bump_version(project)
    if diff:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="project.updated",
            entity_type="project",
            entity_id=project.id,
            project_id=project.id,
            summary=f"Updated project {project.name}",
            changes=diff,
        )
    if archive_verb:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb=archive_verb,
            entity_type="project",
            entity_id=project.id,
            project_id=project.id,
            summary=f"{'Archived' if body.archived else 'Restored'} project {project.name}",
        )
    db.flush()
    return project


# ---------------------------------------------------------------- project access list


def list_project_members(db: Session, project: Project) -> list[tuple[ProjectMember, User]]:
    rows = db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project.id)
        .order_by(User.display_name)
    ).all()
    return [(m, u) for m, u in rows]


def set_project_member(
    db: Session, ctx: WorkspaceContext, project: Project, user_id: uuid.UUID, access: str, meta: RequestMeta
) -> ProjectMember:
    require_capability(db, ctx, project, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    role = db.scalar(
        select(Membership.role).where(
            Membership.workspace_id == ctx.workspace.id, Membership.user_id == user_id
        )
    )
    if role is None:
        raise ProblemError(404, "Member not found.")
    if Role(role) in SEES_ALL_PROJECTS:
        raise ProblemError(409, "Owners and admins always have full access to every project.")
    member = db.get(ProjectMember, (project.id, user_id))
    previous = member.access if member else None
    if member is None:
        member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            workspace_id=ctx.workspace.id,
            access=access,
            added_by_user_id=ctx.auth.user.id,
        )
        db.add(member)
    else:
        member.access = access
    if previous != access:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="project.member_set",
            entity_type="project",
            entity_id=project.id,
            project_id=project.id,
            summary=f"Set project access to {access}",
            changes={"user_id": str(user_id), "access": {"from": previous, "to": access}},
        )
    db.flush()
    return member


def remove_project_member(
    db: Session, ctx: WorkspaceContext, project: Project, user_id: uuid.UUID, meta: RequestMeta
) -> None:
    require_capability(db, ctx, project, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    member = db.get(ProjectMember, (project.id, user_id))
    if member is None or member.workspace_id != ctx.workspace.id:
        raise ProblemError(404, "Member not found.")
    db.delete(member)
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="project.member_removed",
        entity_type="project",
        entity_id=project.id,
        project_id=project.id,
        summary="Removed project access",
        changes={"user_id": str(user_id)},
    )


# ---------------------------------------------------------------- workstreams


def list_workstreams(db: Session, project: Project, *, include_archived: bool) -> list[Workstream]:
    query = select(Workstream).where(Workstream.project_id == project.id)
    if not include_archived:
        query = query.where(Workstream.archived_at.is_(None))
    return list(db.scalars(query.order_by(Workstream.sort_order, Workstream.name)))


def get_workstream(db: Session, ctx: WorkspaceContext, workstream_id: uuid.UUID) -> Workstream:
    workstream = db.scalars(
        select(Workstream).where(Workstream.id == workstream_id, Workstream.workspace_id == ctx.workspace.id)
    ).one_or_none()
    if workstream is None:
        raise ProblemError(404, "Workstream not found.")
    return workstream


def create_workstream(
    db: Session, ctx: WorkspaceContext, project: Project, body: WorkstreamCreate, meta: RequestMeta
) -> Workstream:
    require_capability(db, ctx, project, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    department = get_department(db, ctx, department_id=body.department_id)
    workstream = Workstream(
        workspace_id=ctx.workspace.id,
        project_id=project.id,
        department_id=department.id,
        name=body.name,
        description=body.description,
        sort_order=body.sort_order,
    )
    try:
        with db.begin_nested():
            db.add(workstream)
            db.flush()
    except IntegrityError:
        raise ProblemError(409, "This project already has a workstream with that name.") from None
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="workstream.created",
        entity_type="workstream",
        entity_id=workstream.id,
        project_id=project.id,
        summary=f"Created workstream {workstream.name}",
        changes={"department_id": str(department.id)},
    )
    return workstream


def update_workstream(
    db: Session,
    ctx: WorkspaceContext,
    project: Project,
    workstream: Workstream,
    body: WorkstreamUpdate,
    meta: RequestMeta,
) -> Workstream:
    require_capability(db, ctx, project, Capability.PROJECTS_MANAGE, MANAGE_ONLY)
    if workstream.project_id != project.id:
        raise ProblemError(404, "Workstream not found.")
    fields = body.model_dump(exclude_unset=True, exclude={"archived"})
    diff = {
        k: {"from": getattr(workstream, k), "to": v} for k, v in fields.items() if getattr(workstream, k) != v
    }
    for key, value in fields.items():
        setattr(workstream, key, value)
    if body.archived is not None and body.archived != (workstream.archived_at is not None):
        workstream.archived_at = utcnow() if body.archived else None
        diff["archived"] = {"from": not body.archived, "to": body.archived}
    if diff:
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            raise ProblemError(409, "This project already has a workstream with that name.") from None
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="workstream.updated",
            entity_type="workstream",
            entity_id=workstream.id,
            project_id=project.id,
            summary=f"Updated workstream {workstream.name}",
            changes=diff,
        )
    return workstream
