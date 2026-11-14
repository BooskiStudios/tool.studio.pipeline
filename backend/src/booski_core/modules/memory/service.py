"""Memory entries: create, read, update and archive, with the same project scoping as documents."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, project_capabilities, project_scope
from booski_core.access.roles import Capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.decisions.service import get_decision
from booski_core.modules.departments.service import get_optional_department
from booski_core.modules.knowledge.service import get_document
from booski_core.modules.memory.models import Memory
from booski_core.modules.memory.schemas import MemoryCreate, MemoryOut, MemoryUpdate
from booski_core.modules.projects.models import Project

MEMORY_NOT_FOUND = "Memory entry not found."
NOT_ALLOWED = "Your role doesn't allow changing memory here."
_PREVIEW = 60


def _scoped(ctx: WorkspaceContext) -> Select[Memory]:
    return select(Memory).where(
        Memory.workspace_id == ctx.workspace.id, project_scope(ctx, Memory.project_id)
    )


def get_memory(db: Session, ctx: WorkspaceContext, memory_id: uuid.UUID) -> Memory:
    memory = db.scalars(_scoped(ctx).where(Memory.id == memory_id)).one_or_none()
    if memory is None:
        raise ProblemError(404, MEMORY_NOT_FOUND)
    return memory


def _project_of(db: Session, memory: Memory) -> Project | None:
    return db.get(Project, memory.project_id) if memory.project_id else None


def _require_write(db: Session, ctx: WorkspaceContext, project: Project | None) -> None:
    if Capability.MEMORY_WRITE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, NOT_ALLOWED)


def _check_links(db: Session, ctx: WorkspaceContext, fields: dict[str, Any]) -> None:
    """Departments and sources must exist in this workspace and be visible to the caller (else 404)."""
    if fields.get("department_id") is not None:
        get_optional_department(db, ctx, fields["department_id"])
    if fields.get("source_document_id") is not None:
        get_document(db, ctx, fields["source_document_id"])
    if fields.get("source_decision_id") is not None:
        get_decision(db, ctx, fields["source_decision_id"])


def _preview(content: str) -> str:
    return content if len(content) <= _PREVIEW else content[: _PREVIEW - 1].rstrip() + "…"


def to_out(db: Session, ctx: WorkspaceContext, memory: Memory) -> MemoryOut:
    can_edit = Capability.MEMORY_WRITE in project_capabilities(db, ctx, _project_of(db, memory))
    return MemoryOut.model_validate(memory).model_copy(update={"can_edit": can_edit})


def list_memories(
    db: Session,
    ctx: WorkspaceContext,
    *,
    project: Project | None,
    department_id: uuid.UUID | None,
    kinds: list[str] | None,
    include_archived: bool,
    limit: int,
    cursor: str | None,
) -> tuple[list[Memory], str | None]:
    filters: list[ColumnElement[bool]] = []
    if project is not None:
        filters.append(Memory.project_id == project.id)
    if department_id is not None:
        filters.append(Memory.department_id == department_id)
    if kinds:
        filters.append(Memory.kind.in_(kinds))
    if not include_archived:
        filters.append(Memory.archived_at.is_(None))
    rows, next_cursor = paginate(
        db,
        _scoped(ctx).where(*filters),
        key=SortKey(Memory.updated_at, datetime.fromisoformat),
        id_column=Memory.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda m: m.updated_at,
        row_id=lambda m: m.id,
    )
    return list(rows), next_cursor


def create_memory(db: Session, ctx: WorkspaceContext, body: MemoryCreate, meta: RequestMeta) -> Memory:
    project = get_optional_project(db, ctx, body.project_id)
    _require_write(db, ctx, project)
    fields = body.model_dump()
    _check_links(db, ctx, fields)
    memory = Memory(
        workspace_id=ctx.workspace.id,
        created_by_user_id=ctx.auth.user.id,
        updated_by_user_id=ctx.auth.user.id,
        **fields,
    )
    db.add(memory)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="memory.created",
        entity_type="memory",
        entity_id=memory.id,
        project_id=memory.project_id,
        summary=f"Added a {memory.kind} to memory: {_preview(memory.content)}",
    )
    return memory


def update_memory(
    db: Session, ctx: WorkspaceContext, memory: Memory, body: MemoryUpdate, meta: RequestMeta
) -> Memory:
    _require_write(db, ctx, _project_of(db, memory))
    check_version(memory, body.version)
    sent = body.model_dump(exclude_unset=True, exclude={"archived", "version"})
    if "kind" in sent and sent["kind"] is None:
        del sent["kind"]
    if "content" in sent and sent["content"] is None:
        del sent["content"]
    if "project_id" in sent and sent["project_id"] != memory.project_id:
        _require_write(db, ctx, get_optional_project(db, ctx, sent["project_id"]))  # allowed in both
    _check_links(db, ctx, sent)

    diff: dict[str, Any] = {
        key: {"from": getattr(memory, key), "to": value}
        for key, value in sent.items()
        if getattr(memory, key) != value
    }
    for key in diff:
        setattr(memory, key, sent[key])
    archive_verb = None
    if body.archived is not None and body.archived != (memory.archived_at is not None):
        memory.archived_at = utcnow() if body.archived else None
        archive_verb = "memory.archived" if body.archived else "memory.restored"
    if not diff and archive_verb is None:
        return memory
    memory.updated_by_user_id = ctx.auth.user.id
    bump_version(memory)
    if diff:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="memory.updated",
            entity_type="memory",
            entity_id=memory.id,
            project_id=memory.project_id,
            summary=f"Updated memory: {_preview(memory.content)}",
            changes=diff,
        )
    if archive_verb:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb=archive_verb,
            entity_type="memory",
            entity_id=memory.id,
            project_id=memory.project_id,
            summary=f"{'Archived' if body.archived else 'Restored'} memory: {_preview(memory.content)}",
        )
    db.flush()
    return memory
