import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.activity import service
from booski_core.modules.activity.schemas import ActivityOut
from booski_core.modules.identity.dependencies import DbSession

router = APIRouter(prefix="/w/{workspace_slug}/activity", tags=["activity"])


@router.get("", response_model=Page[ActivityOut])
def list_activity(
    ctx: MemberContext,
    db: DbSession,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: uuid.UUID | None = None,
    actor: Annotated[uuid.UUID | None, Query(description="User id of whoever acted.")] = None,
    verb: Annotated[list[str] | None, Query(description="e.g. task.completed (repeatable).")] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[ActivityOut]:
    """The workspace's activity and audit history, newest first.

    You only see events for projects you can access. Invitation events are shown to owners and admins only.
    """
    items, next_cursor = service.list_activity(
        db,
        ctx,
        project_id=get_project(db, ctx, slug=project).id if project else None,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor,
        verbs=verb,
        since=since,
        until=until,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=items, next_cursor=next_cursor)
