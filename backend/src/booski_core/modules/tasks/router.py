import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.activity.schemas import ActivityOut
from booski_core.modules.activity.service import entity_history
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.tasks import service
from booski_core.modules.tasks.schemas import (
    CommentCreate,
    CommentOut,
    TaskCreate,
    TaskOut,
    TaskSort,
    TaskUpdate,
)
from booski_core.vocab import TaskPriority, TaskStatus

router = APIRouter(prefix="/w/{workspace_slug}", tags=["tasks"])


@router.get("/tasks", response_model=Page[TaskOut])
def list_tasks(
    ctx: MemberContext,
    db: DbSession,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    department: Annotated[str | None, Query(description="Department slug.")] = None,
    workstream: uuid.UUID | None = None,
    milestone: uuid.UUID | None = None,
    status: Annotated[list[TaskStatus] | None, Query()] = None,
    priority: Annotated[list[TaskPriority] | None, Query()] = None,
    assignee: Annotated[
        Literal["me", "none"] | uuid.UUID | None, Query(description="`me`, `none` or a user id.")
    ] = None,
    parent: Annotated[
        Literal["none"] | uuid.UUID | None,
        Query(description="`none` for top-level tasks, or a parent task id."),
    ] = None,
    q: Annotated[str | None, Query(max_length=100, description="Search in titles.")] = None,
    archived: bool = False,
    due_before: date | None = None,
    sort: TaskSort = "position",
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[TaskOut]:
    """Tasks you can see, filtered and sorted. Restricted projects' tasks only appear for their members."""
    rows, next_cursor = service.list_tasks(
        db,
        ctx,
        project=get_project(db, ctx, slug=project) if project else None,
        department_id=get_department(db, ctx, slug=department).id if department else None,
        workstream_id=workstream,
        milestone_id=milestone,
        status=list(status) if status else None,
        priority=list(priority) if priority else None,
        assignee=assignee,
        parent=parent,
        q=q,
        archived=archived,
        due_before=due_before,
        sort=sort,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=service.to_out(db, ctx, rows), next_cursor=next_cursor)


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> TaskOut:
    task = service.create_task(db, ctx, body, meta)
    db.commit()
    db.refresh(task)
    return service.to_out(db, ctx, [task])[0]


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> TaskOut:
    return service.to_out(db, ctx, [service.get_task(db, ctx, task_id)])[0]


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID, body: TaskUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> TaskOut:
    """Edits, completes, reassigns, archives or restores a task. Send ``version`` to detect conflicts."""
    task = service.update_task(db, ctx, service.get_task(db, ctx, task_id), body, meta)
    db.commit()
    db.refresh(task)
    return service.to_out(db, ctx, [task])[0]


@router.get("/tasks/{task_id}/history", response_model=Page[ActivityOut])
def task_history(
    task_id: uuid.UUID, ctx: MemberContext, db: DbSession, limit: Limit = 50, cursor: Cursor = None
) -> Page[ActivityOut]:
    """Everything that happened to this task, newest first (changes, assignments, comments)."""
    task = service.get_task(db, ctx, task_id)
    items, next_cursor = entity_history(db, ctx, "task", task.id, limit=limit, cursor=cursor)
    return Page(items=items, next_cursor=next_cursor)


@router.get("/tasks/{task_id}/comments", response_model=Page[CommentOut])
def list_comments(
    task_id: uuid.UUID, ctx: MemberContext, db: DbSession, limit: Limit = 50, cursor: Cursor = None
) -> Page[CommentOut]:
    """Comments, oldest first. Deleted comments keep their place with an empty body."""
    items, next_cursor = service.list_comments(
        db, service.get_task(db, ctx, task_id), limit=limit, cursor=cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    task_id: uuid.UUID, body: CommentCreate, ctx: MemberContext, db: DbSession, meta: Meta
) -> CommentOut:
    comment = service.add_comment(db, ctx, service.get_task(db, ctx, task_id), body.body, meta)
    db.commit()
    return comment


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def edit_comment(
    comment_id: uuid.UUID, body: CommentCreate, ctx: MemberContext, db: DbSession, meta: Meta
) -> CommentOut:
    """Edits your own comment."""
    comment = service.edit_comment(db, ctx, comment_id, body.body, meta)
    db.commit()
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta) -> None:
    """Deletes your own comment (owners and admins can delete any)."""
    service.delete_comment(db, ctx, comment_id, meta)
    db.commit()
