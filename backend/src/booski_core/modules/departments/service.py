import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.roles import Capability, has_capability
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.departments.defaults import DEFAULT_DEPARTMENTS
from booski_core.modules.departments.models import Department
from booski_core.modules.departments.schemas import DepartmentCreate, DepartmentUpdate

DEPARTMENT_NOT_FOUND = "Department not found."


def seed_default_departments(db: Session, workspace_id: uuid.UUID) -> None:
    for order, default in enumerate(DEFAULT_DEPARTMENTS):
        db.add(Department(workspace_id=workspace_id, sort_order=order * 10, **default._asdict()))


def list_departments(db: Session, ctx: WorkspaceContext, *, include_archived: bool) -> list[Department]:
    query = select(Department).where(Department.workspace_id == ctx.workspace.id)
    if not include_archived:
        query = query.where(Department.archived_at.is_(None))
    return list(db.scalars(query.order_by(Department.sort_order, Department.name)))


def get_department(
    db: Session, ctx: WorkspaceContext, *, slug: str | None = None, department_id: uuid.UUID | None = None
) -> Department:
    query = select(Department).where(Department.workspace_id == ctx.workspace.id)
    query = (
        query.where(Department.slug == slug)
        if slug is not None
        else query.where(Department.id == department_id)
    )
    department = db.scalars(query).one_or_none()
    if department is None:
        raise ProblemError(404, DEPARTMENT_NOT_FOUND)
    return department


def get_optional_department(
    db: Session, ctx: WorkspaceContext, department_id: uuid.UUID | None
) -> Department | None:
    return None if department_id is None else get_department(db, ctx, department_id=department_id)


def _require_manage(ctx: WorkspaceContext) -> None:
    if not has_capability(ctx.role, Capability.DEPARTMENTS_MANAGE):
        raise ProblemError(403, "Only owners and admins can change departments.")


def create_department(
    db: Session, ctx: WorkspaceContext, body: DepartmentCreate, meta: RequestMeta
) -> Department:
    _require_manage(ctx)
    department = Department(workspace_id=ctx.workspace.id, **body.model_dump())
    try:
        with db.begin_nested():
            db.add(department)
            db.flush()
    except IntegrityError:
        raise ProblemError(409, "A department with that address already exists.") from None
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="department.created",
        entity_type="department",
        entity_id=department.id,
        summary=f"Created department {department.name}",
    )
    return department


def update_department(
    db: Session, ctx: WorkspaceContext, department: Department, body: DepartmentUpdate, meta: RequestMeta
) -> Department:
    _require_manage(ctx)
    changes = body.model_dump(exclude_unset=True, exclude={"archived"})
    before = {key: getattr(department, key) for key in changes}
    for key, value in changes.items():
        setattr(department, key, value)
    if body.archived is not None and body.archived != (department.archived_at is not None):
        department.archived_at = utcnow() if body.archived else None
        verb = "department.archived" if body.archived else "department.restored"
        record_workspace_event(
            db,
            ctx,
            meta,
            verb=verb,
            entity_type="department",
            entity_id=department.id,
            summary=f"{'Archived' if body.archived else 'Restored'} department {department.name}",
        )
    diff = {key: {"from": before[key], "to": value} for key, value in changes.items() if before[key] != value}
    if diff:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="department.updated",
            entity_type="department",
            entity_id=department.id,
            summary=f"Updated department {department.name}",
            changes=diff,
        )
    db.flush()
    return department
