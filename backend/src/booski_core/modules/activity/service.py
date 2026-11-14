import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import project_scope
from booski_core.access.roles import Capability, has_capability
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta
from booski_core.modules.activity.models import ActivityEvent
from booski_core.modules.activity.schemas import ActivityOut


def json_safe(value: Any) -> Any:
    """Converts dates and UUIDs (anywhere in nested dicts/lists) to strings for the JSONB column."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, date):  # also covers datetime
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def record_event(
    db: Session,
    *,
    verb: str,
    entity_type: str,
    summary: str,
    meta: RequestMeta,
    actor_user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    """Adds an event to the current transaction, so it is saved only if the change itself is saved."""
    db.add(
        ActivityEvent(
            actor_type="user" if actor_user_id else "system",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            project_id=project_id,
            verb=verb,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            changes=json_safe(changes or {}),
            request_id=meta.request_id,
            ip=meta.ip,
        )
    )


def record_workspace_event(
    db: Session,
    ctx: WorkspaceContext,
    meta: RequestMeta,
    *,
    verb: str,
    entity_type: str,
    entity_id: uuid.UUID,
    summary: str,
    project_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    """Shorthand for events caused by the signed-in member, inside their workspace."""
    record_event(
        db,
        verb=verb,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        meta=meta,
        actor_user_id=ctx.auth.user.id,
        workspace_id=ctx.workspace.id,
        project_id=project_id,
        changes=changes,
    )


# ---------------------------------------------------------------- reading


def _visible_events(ctx: WorkspaceContext) -> Select[ActivityEvent]:
    """Events in this workspace the caller may see: restricted projects only for their members, and
    invitation events (which contain invitees' email addresses) only for owners and admins."""
    query = select(ActivityEvent).where(
        ActivityEvent.workspace_id == ctx.workspace.id, project_scope(ctx, ActivityEvent.project_id)
    )
    if not has_capability(ctx.role, Capability.AUDIT_READ):
        query = query.where(ActivityEvent.entity_type != "invitation")
    return query


def _page(
    db: Session, query: Select[ActivityEvent], limit: int, cursor: str | None
) -> tuple[list[ActivityOut], str | None]:
    rows, next_cursor = paginate(
        db,
        query,
        key=SortKey(ActivityEvent.created_at, datetime.fromisoformat, "desc"),
        id_column=ActivityEvent.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda e: e.created_at,
        row_id=lambda e: e.id,
    )
    return [ActivityOut.model_validate(e) for e in rows], next_cursor


def list_activity(
    db: Session,
    ctx: WorkspaceContext,
    *,
    project_id: uuid.UUID | None,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    verbs: list[str] | None,
    since: datetime | None,
    until: datetime | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[ActivityOut], str | None]:
    query = _visible_events(ctx)
    if project_id is not None:
        query = query.where(ActivityEvent.project_id == project_id)
    if entity_type is not None:
        query = query.where(ActivityEvent.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(ActivityEvent.entity_id == entity_id)
    if actor_user_id is not None:
        query = query.where(ActivityEvent.actor_user_id == actor_user_id)
    if verbs:
        query = query.where(ActivityEvent.verb.in_(verbs))
    if since is not None:
        query = query.where(ActivityEvent.created_at >= since)
    if until is not None:
        query = query.where(ActivityEvent.created_at < until)
    return _page(db, query, limit, cursor)


def entity_history(
    db: Session,
    ctx: WorkspaceContext,
    entity_type: str,
    entity_id: uuid.UUID,
    *,
    limit: int,
    cursor: str | None,
) -> tuple[list[ActivityOut], str | None]:
    query = _visible_events(ctx).where(
        ActivityEvent.entity_type == entity_type, ActivityEvent.entity_id == entity_id
    )
    return _page(db, query, limit, cursor)
