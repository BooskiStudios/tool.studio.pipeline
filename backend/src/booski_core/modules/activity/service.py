import uuid
from typing import Any

from sqlalchemy.orm import Session

from booski_core.core.request_meta import RequestMeta
from booski_core.modules.activity.models import ActivityEvent


def record_event(
    db: Session,
    *,
    verb: str,
    entity_type: str,
    summary: str,
    meta: RequestMeta,
    actor_user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    """Adds an event to the current transaction, so it is saved only if the change itself is saved."""
    db.add(
        ActivityEvent(
            actor_type="user" if actor_user_id else "system",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            verb=verb,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            changes=changes or {},
            request_id=meta.request_id,
            ip=meta.ip,
        )
    )
