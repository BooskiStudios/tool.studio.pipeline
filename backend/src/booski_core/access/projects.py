"""Project-level access: which projects a member can see, and what they may do inside each.

Rules (never widening the workspace role):

* Owners and admins see and act on every project, including restricted ones.
* A ``restricted`` project is invisible (404) to anyone else without a ``project_members`` row.
* A ``project_members`` row with ``viewer`` access makes the project read-only for that person, even if
  their workspace role could write.
* Records without a project (studio-wide tasks, documents, …) follow the workspace role alone.
"""

import uuid

from sqlalchemy import ColumnElement, Select, SQLColumnExpression, or_, select, true
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.roles import (
    READ_ONLY_CAPABILITIES,
    ROLE_CAPABILITIES,
    SEES_ALL_PROJECTS,
    Capability,
)
from booski_core.core.errors import ProblemError
from booski_core.modules.projects.models import Project, ProjectMember

PROJECT_NOT_FOUND = "Project not found."
NOT_ALLOWED = "Your role doesn't allow this."


def visible_project_ids(ctx: WorkspaceContext) -> Select[uuid.UUID]:
    query = select(Project.id).where(Project.workspace_id == ctx.workspace.id)
    if ctx.role in SEES_ALL_PROJECTS:
        return query
    member_of = select(ProjectMember.project_id).where(ProjectMember.user_id == ctx.auth.user.id)
    return query.where(or_(Project.visibility == "workspace", Project.id.in_(member_of)))


def project_scope(
    ctx: WorkspaceContext, project_column: SQLColumnExpression[uuid.UUID | None]
) -> ColumnElement[bool]:
    """Filter for any table with an optional ``project_id``: rows the caller is allowed to see."""
    if ctx.role in SEES_ALL_PROJECTS:
        return true()
    return or_(project_column.is_(None), project_column.in_(visible_project_ids(ctx)))


def project_capabilities(
    db: Session, ctx: WorkspaceContext, project: Project | None
) -> frozenset[Capability]:
    """The caller's capabilities for records in ``project`` (or studio-wide records when ``None``).

    Raises 404 if the caller can't see the project at all.
    """
    role_caps = ROLE_CAPABILITIES[ctx.role]
    if project is None or ctx.role in SEES_ALL_PROJECTS:
        return role_caps
    access = db.scalar(
        select(ProjectMember.access).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == ctx.auth.user.id
        )
    )
    if access is None:
        if project.visibility == "restricted":
            raise ProblemError(404, PROJECT_NOT_FOUND)
        return role_caps
    if access == "viewer":
        return role_caps & READ_ONLY_CAPABILITIES
    return role_caps


def require_capability(
    db: Session,
    ctx: WorkspaceContext,
    project: Project | None,
    capability: Capability,
    detail: str = NOT_ALLOWED,
) -> None:
    if capability not in project_capabilities(db, ctx, project):
        raise ProblemError(403, detail)


def get_project(
    db: Session, ctx: WorkspaceContext, *, slug: str | None = None, project_id: uuid.UUID | None = None
) -> Project:
    """A project in this workspace that the caller can see; 404 otherwise (including other workspaces)."""
    query = select(Project).where(Project.workspace_id == ctx.workspace.id)
    query = query.where(Project.slug == slug) if slug is not None else query.where(Project.id == project_id)
    project = db.scalars(query).one_or_none()
    if project is None:
        raise ProblemError(404, PROJECT_NOT_FOUND)
    project_capabilities(db, ctx, project)  # raises 404 if restricted and not a member
    return project


def get_optional_project(db: Session, ctx: WorkspaceContext, project_id: uuid.UUID | None) -> Project | None:
    return None if project_id is None else get_project(db, ctx, project_id=project_id)
