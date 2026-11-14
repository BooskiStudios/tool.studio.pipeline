from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.modules.departments import service
from booski_core.modules.departments.schemas import DepartmentCreate, DepartmentOut, DepartmentUpdate
from booski_core.modules.identity.dependencies import DbSession, Meta

router = APIRouter(prefix="/w/{workspace_slug}/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    ctx: MemberContext, db: DbSession, include_archived: Annotated[bool, Query()] = False
) -> list[DepartmentOut]:
    """The workspace's departments, in display order."""
    return [
        DepartmentOut.model_validate(d)
        for d in service.list_departments(db, ctx, include_archived=include_archived)
    ]


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(body: DepartmentCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> DepartmentOut:
    """Adds a department (owners and admins)."""
    department = service.create_department(db, ctx, body, meta)
    db.commit()
    return DepartmentOut.model_validate(department)


@router.get("/{department_slug}", response_model=DepartmentOut)
def get_department(department_slug: str, ctx: MemberContext, db: DbSession) -> DepartmentOut:
    return DepartmentOut.model_validate(service.get_department(db, ctx, slug=department_slug))


@router.patch("/{department_slug}", response_model=DepartmentOut)
def update_department(
    department_slug: str, body: DepartmentUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> DepartmentOut:
    """Renames, recolours, reorders, archives or restores a department (owners and admins)."""
    department = service.update_department(
        db, ctx, service.get_department(db, ctx, slug=department_slug), body, meta
    )
    db.commit()
    db.refresh(department)
    return DepartmentOut.model_validate(department)
