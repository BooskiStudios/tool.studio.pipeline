import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.activity.schemas import ActivityOut
from booski_core.modules.activity.service import entity_history
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.memory import service
from booski_core.modules.memory.schemas import MemoryCreate, MemoryOut, MemoryUpdate
from booski_core.vocab import MemoryKind

router = APIRouter(prefix="/w/{workspace_slug}/memories", tags=["memory"])


@router.get("", response_model=Page[MemoryOut])
def list_memories(
    ctx: MemberContext,
    db: DbSession,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    department: Annotated[str | None, Query(description="Department slug.")] = None,
    kind: Annotated[list[MemoryKind] | None, Query()] = None,
    archived: Annotated[bool, Query(description="Include archived entries.")] = False,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[MemoryOut]:
    """Memory entries you can see, most recently changed first."""
    rows, next_cursor = service.list_memories(
        db,
        ctx,
        project=get_project(db, ctx, slug=project) if project else None,
        department_id=get_department(db, ctx, slug=department).id if department else None,
        kinds=list(kind) if kind else None,
        include_archived=archived,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=[service.to_out(db, ctx, m) for m in rows], next_cursor=next_cursor)


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(body: MemoryCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> MemoryOut:
    memory = service.create_memory(db, ctx, body, meta)
    db.commit()
    db.refresh(memory)
    return service.to_out(db, ctx, memory)


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> MemoryOut:
    return service.to_out(db, ctx, service.get_memory(db, ctx, memory_id))


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(
    memory_id: uuid.UUID, body: MemoryUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> MemoryOut:
    memory = service.update_memory(db, ctx, service.get_memory(db, ctx, memory_id), body, meta)
    db.commit()
    db.refresh(memory)
    return service.to_out(db, ctx, memory)


@router.get("/{memory_id}/history", response_model=Page[ActivityOut])
def memory_history(
    memory_id: uuid.UUID, ctx: MemberContext, db: DbSession, limit: Limit = 50, cursor: Cursor = None
) -> Page[ActivityOut]:
    """Every change to this memory entry, newest first."""
    memory = service.get_memory(db, ctx, memory_id)
    items, next_cursor = entity_history(db, ctx, "memory", memory.id, limit=limit, cursor=cursor)
    return Page(items=items, next_cursor=next_cursor)
