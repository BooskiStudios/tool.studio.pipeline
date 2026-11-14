"""Task rules. Every check here applies equally to people and, later, to AI agents acting for a person."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import ColumnElement, Select, case, func, literal, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, project_capabilities, project_scope
from booski_core.access.roles import SEES_ALL_PROJECTS, Capability, Role
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.core.schemas import attributes
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.departments.service import get_department
from booski_core.modules.milestones.models import Milestone
from booski_core.modules.projects.models import Project, ProjectMember, Workstream
from booski_core.modules.tasks.models import Task, TaskComment
from booski_core.modules.tasks.schemas import CommentOut, TaskCreate, TaskOut, TaskSort, TaskUpdate
from booski_core.modules.workspaces.models import Membership

TASK_NOT_FOUND = "Task not found."
CANT_EDIT = "You can only change tasks you created or are assigned to."
MAX_DEPTH = 5  # subtasks can nest this deep


class _Caps:
    """Per-request cache of project capabilities (a task list may span many projects)."""

    def __init__(self, db: Session, ctx: WorkspaceContext) -> None:
        self.db = db
        self.ctx = ctx
        self._cache: dict[uuid.UUID | None, frozenset[Capability]] = {}

    def for_project(self, project: Project | None) -> frozenset[Capability]:
        key = project.id if project else None
        if key not in self._cache:
            self._cache[key] = project_capabilities(self.db, self.ctx, project)
        return self._cache[key]

    def for_task(self, task: Task) -> frozenset[Capability]:
        if task.project_id not in self._cache:
            project = self.db.get(Project, task.project_id) if task.project_id else None
            return self.for_project(project)
        return self._cache[task.project_id]


def _can_edit(ctx: WorkspaceContext, caps: frozenset[Capability], task: Task) -> bool:
    if Capability.TASKS_EDIT_ANY in caps:
        return True
    me = ctx.auth.user.id
    return Capability.TASKS_CREATE in caps and me in (task.created_by_user_id, task.assignee_user_id)


def to_out(db: Session, ctx: WorkspaceContext, tasks: list[Task]) -> list[TaskOut]:
    caps = _Caps(db, ctx)
    return [
        TaskOut.model_validate({**attributes(t, TaskOut), "can_edit": _can_edit(ctx, caps.for_task(t), t)})
        for t in tasks
    ]


# ---------------------------------------------------------------- loading


def _scoped(ctx: WorkspaceContext) -> Select[Task]:
    return select(Task).where(Task.workspace_id == ctx.workspace.id, project_scope(ctx, Task.project_id))


def get_task(db: Session, ctx: WorkspaceContext, task_id: uuid.UUID) -> Task:
    """A task in this workspace that the caller can see; 404 for anything else, including other workspaces."""
    task = db.scalars(_scoped(ctx).where(Task.id == task_id)).one_or_none()
    if task is None:
        raise ProblemError(404, TASK_NOT_FOUND)
    return task


# ---------------------------------------------------------------- listing

_PRIORITY_RANK = case({"high": 3, "medium": 2, "low": 1}, value=Task.priority, else_=0)
_FAR_FUTURE = date(9999, 12, 31)


def _sort_key(sort: TaskSort) -> SortKey:
    if sort == "position":
        return SortKey(Task.position, float, "asc")
    if sort == "due_date":
        return SortKey(func.coalesce(Task.due_date, literal(_FAR_FUTURE)), date.fromisoformat, "asc")
    if sort == "priority":
        return SortKey(_PRIORITY_RANK, int, "desc")
    column = Task.created_at if sort == "created_at" else Task.updated_at
    return SortKey(column, datetime.fromisoformat, "desc")


def _sort_value(task: Task, sort: TaskSort) -> date | datetime | float | int:
    if sort == "position":
        return task.position
    if sort == "due_date":
        return task.due_date or _FAR_FUTURE
    if sort == "priority":
        return {"high": 3, "medium": 2, "low": 1}.get(task.priority, 0)
    value: datetime = task.created_at if sort == "created_at" else task.updated_at
    return value


def list_tasks(
    db: Session,
    ctx: WorkspaceContext,
    *,
    project: Project | None,
    department_id: uuid.UUID | None,
    workstream_id: uuid.UUID | None,
    milestone_id: uuid.UUID | None,
    status: list[str] | None,
    priority: list[str] | None,
    assignee: Literal["me", "none"] | uuid.UUID | None,
    parent: Literal["none"] | uuid.UUID | None,
    q: str | None,
    archived: bool,
    due_before: date | None,
    sort: TaskSort,
    limit: int,
    cursor: str | None,
) -> tuple[list[Task], str | None]:
    query = _scoped(ctx).where(Task.archived_at.is_not(None) if archived else Task.archived_at.is_(None))
    filters: list[ColumnElement[bool]] = []
    if project is not None:
        filters.append(Task.project_id == project.id)
    if department_id is not None:
        filters.append(Task.department_id == department_id)
    if workstream_id is not None:
        filters.append(Task.workstream_id == workstream_id)
    if milestone_id is not None:
        filters.append(Task.milestone_id == milestone_id)
    if status:
        filters.append(Task.status.in_(status))
    if priority:
        filters.append(Task.priority.in_(priority))
    if assignee == "me":
        filters.append(Task.assignee_user_id == ctx.auth.user.id)
    elif assignee == "none":
        filters.append(Task.assignee_user_id.is_(None))
    elif assignee is not None:
        filters.append(Task.assignee_user_id == assignee)
    if parent == "none":
        filters.append(Task.parent_task_id.is_(None))
    elif parent is not None:
        filters.append(Task.parent_task_id == parent)
    if q:
        filters.append(Task.title.icontains(q, autoescape=True))
    if due_before is not None:
        filters.append(Task.due_date <= due_before)
    rows, next_cursor = paginate(
        db,
        query.where(*filters),
        key=_sort_key(sort),
        id_column=Task.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda t: _sort_value(t, sort),
        row_id=lambda t: t.id,
    )
    return list(rows), next_cursor


# ---------------------------------------------------------------- validation of links


def _workstream(
    db: Session, ctx: WorkspaceContext, workstream_id: uuid.UUID, project: Project | None
) -> Workstream:
    if project is None:
        raise ProblemError(422, "A workstream can only be set on a task that belongs to a project.")
    workstream = db.scalars(
        select(Workstream).where(Workstream.id == workstream_id, Workstream.workspace_id == ctx.workspace.id)
    ).one_or_none()
    if workstream is None or workstream.project_id != project.id:
        raise ProblemError(422, "That workstream isn't part of this task's project.")
    return workstream


def _milestone(
    db: Session, ctx: WorkspaceContext, milestone_id: uuid.UUID, project: Project | None
) -> Milestone:
    if project is None:
        raise ProblemError(422, "A milestone can only be set on a task that belongs to a project.")
    milestone = db.scalars(
        select(Milestone).where(Milestone.id == milestone_id, Milestone.workspace_id == ctx.workspace.id)
    ).one_or_none()
    if milestone is None or milestone.project_id != project.id:
        raise ProblemError(422, "That milestone isn't part of this task's project.")
    return milestone


def _parent(
    db: Session,
    ctx: WorkspaceContext,
    parent_id: uuid.UUID,
    project_id: uuid.UUID | None,
    task_id: uuid.UUID | None,
) -> Task:
    try:
        parent = get_task(db, ctx, parent_id)
    except ProblemError:
        raise ProblemError(422, "The parent task doesn't exist in this workspace.") from None
    if parent.project_id != project_id:
        raise ProblemError(422, "A subtask must belong to the same project as its parent.")
    if parent.id == task_id:
        raise ProblemError(422, "A task can't be its own parent.")
    # Walk up from the new parent. Meeting this task on the way would create a loop.
    depth, current = 1, parent
    while current.parent_task_id is not None:
        if current.parent_task_id == task_id:
            raise ProblemError(422, "A task can't be placed under its own subtask.")
        depth += 1
        current = db.get_one(Task, current.parent_task_id)
    if depth >= MAX_DEPTH:
        raise ProblemError(422, f"Subtasks can only be nested {MAX_DEPTH} levels deep.")
    return parent


def _check_assignee(
    db: Session,
    ctx: WorkspaceContext,
    caps: frozenset[Capability],
    user_id: uuid.UUID,
    project: Project | None,
) -> None:
    if Capability.TASKS_EDIT_ANY not in caps and user_id != ctx.auth.user.id:
        raise ProblemError(403, "Your role can only assign tasks to yourself.")
    role = db.scalar(
        select(Membership.role).where(
            Membership.workspace_id == ctx.workspace.id, Membership.user_id == user_id
        )
    )
    if role is None:
        raise ProblemError(422, "The assignee isn't a member of this workspace.")
    if project is not None and project.visibility == "restricted" and Role(role) not in SEES_ALL_PROJECTS:
        on_list = db.get(ProjectMember, (project.id, user_id)) is not None
        if not on_list:
            raise ProblemError(422, "The assignee can't access this restricted project.")


def _next_position(db: Session, ctx: WorkspaceContext, project_id: uuid.UUID | None) -> float:
    scope = Task.project_id == project_id if project_id else Task.project_id.is_(None)
    highest = db.scalar(select(func.max(Task.position)).where(Task.workspace_id == ctx.workspace.id, scope))
    return float(highest or 0) + 1


# ---------------------------------------------------------------- create / update


def create_task(db: Session, ctx: WorkspaceContext, body: TaskCreate, meta: RequestMeta) -> Task:
    project = get_optional_project(db, ctx, body.project_id)
    caps = project_capabilities(db, ctx, project)
    if Capability.TASKS_CREATE not in caps:
        raise ProblemError(403, "Your role doesn't allow creating tasks here.")
    department_id = body.department_id
    if body.workstream_id is not None:
        workstream = _workstream(db, ctx, body.workstream_id, project)
        if department_id is not None and department_id != workstream.department_id:
            raise ProblemError(422, "The department must match the workstream's department.")
        department_id = workstream.department_id
    if department_id is not None:
        get_department(db, ctx, department_id=department_id)
    if body.milestone_id is not None:
        _milestone(db, ctx, body.milestone_id, project)
    if body.parent_task_id is not None:
        _parent(db, ctx, body.parent_task_id, project.id if project else None, None)
    if body.assignee_user_id is not None:
        _check_assignee(db, ctx, caps, body.assignee_user_id, project)

    task = Task(
        workspace_id=ctx.workspace.id,
        created_by_user_id=ctx.auth.user.id,
        **body.model_dump(exclude={"department_id", "position"}),
        department_id=department_id,
        position=body.position if body.position is not None else _next_position(db, ctx, body.project_id),
        completed_at=utcnow() if body.status == "done" else None,
    )
    db.add(task)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="task.created",
        entity_type="task",
        entity_id=task.id,
        project_id=task.project_id,
        summary=f"Created task {task.title}",
        changes={"status": task.status, "assignee_user_id": task.assignee_user_id},
    )
    return task


def update_task(db: Session, ctx: WorkspaceContext, task: Task, body: TaskUpdate, meta: RequestMeta) -> Task:
    project = db.get(Project, task.project_id) if task.project_id else None
    caps = project_capabilities(db, ctx, project)
    if not _can_edit(ctx, caps, task):
        raise ProblemError(
            403,
            CANT_EDIT if Capability.TASKS_CREATE in caps else "Your role doesn't allow editing tasks here.",
        )
    check_version(task, body.version)
    sent = body.model_dump(exclude_unset=True, exclude={"archived", "version"})

    if "workstream_id" in sent and sent["workstream_id"] is not None:
        workstream = _workstream(db, ctx, sent["workstream_id"], project)
        if "department_id" not in sent:
            sent["department_id"] = workstream.department_id
        elif sent["department_id"] != workstream.department_id:
            raise ProblemError(422, "The department must match the workstream's department.")
    if sent.get("department_id") is not None:
        get_department(db, ctx, department_id=sent["department_id"])
    if sent.get("milestone_id") is not None:
        _milestone(db, ctx, sent["milestone_id"], project)
    if sent.get("parent_task_id") is not None:
        _parent(db, ctx, sent["parent_task_id"], task.project_id, task.id)
    if "assignee_user_id" in sent and sent["assignee_user_id"] != task.assignee_user_id:
        if sent["assignee_user_id"] is not None:
            _check_assignee(db, ctx, caps, sent["assignee_user_id"], project)
        elif Capability.TASKS_EDIT_ANY not in caps and task.assignee_user_id != ctx.auth.user.id:
            raise ProblemError(403, "Your role can only assign tasks to yourself.")
    start = sent.get("start_date", task.start_date)
    due = sent.get("due_date", task.due_date)
    if start and due and due < start:
        raise ProblemError(422, "The due date can't be before the start date.")

    diff: dict[str, Any] = {}
    for key, value in sent.items():
        if getattr(task, key) != value:
            diff[key] = {"from": getattr(task, key), "to": value}
            setattr(task, key, value)
    if "status" in diff:
        task.completed_at = (task.completed_at or utcnow()) if task.status == "done" else None
    if body.archived is not None and body.archived != (task.archived_at is not None):
        task.archived_at = utcnow() if body.archived else None
        diff["archived"] = {"from": not body.archived, "to": body.archived}
    if not diff:
        return task
    bump_version(task)
    db.flush()
    _record_update_events(db, ctx, task, diff, meta)
    return task


def _record_update_events(
    db: Session, ctx: WorkspaceContext, task: Task, diff: dict[str, Any], meta: RequestMeta
) -> None:
    """Meaningful events (completed, assigned, archived) are recorded separately from general edits."""

    def event(verb: str, summary: str, changes: dict[str, Any]) -> None:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb=verb,
            entity_type="task",
            entity_id=task.id,
            project_id=task.project_id,
            summary=summary,
            changes=changes,
        )

    remaining = dict(diff)
    if "status" in remaining:
        status = remaining.pop("status")
        verb = "task.completed" if status["to"] == "done" else "task.status_changed"
        event(
            verb,
            f"{'Completed' if status['to'] == 'done' else 'Moved'} task {task.title}",
            {"status": status},
        )
    if "assignee_user_id" in remaining:
        event(
            "task.assigned",
            f"Reassigned task {task.title}",
            {"assignee_user_id": remaining.pop("assignee_user_id")},
        )
    if "archived" in remaining:
        archived = remaining.pop("archived")
        event(
            "task.archived" if archived["to"] else "task.restored",
            f"{'Archived' if archived['to'] else 'Restored'} task {task.title}",
            {},
        )
    if remaining:
        event("task.updated", f"Updated task {task.title}", remaining)


# ---------------------------------------------------------------- comments


def _comment_out(comment: TaskComment) -> CommentOut:
    deleted = comment.deleted_at is not None
    return CommentOut(
        id=comment.id,
        task_id=comment.task_id,
        author_user_id=comment.author_user_id,
        body="" if deleted else comment.body,
        created_at=comment.created_at,
        edited_at=comment.edited_at,
        deleted=deleted,
    )


def list_comments(
    db: Session, task: Task, *, limit: int, cursor: str | None
) -> tuple[list[CommentOut], str | None]:
    query = select(TaskComment).where(TaskComment.task_id == task.id)
    rows, next_cursor = paginate(
        db,
        query,
        key=SortKey(TaskComment.created_at, datetime.fromisoformat, "asc"),
        id_column=TaskComment.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda c: c.created_at,
        row_id=lambda c: c.id,
    )
    return [_comment_out(c) for c in rows], next_cursor


def add_comment(db: Session, ctx: WorkspaceContext, task: Task, body: str, meta: RequestMeta) -> CommentOut:
    project = db.get(Project, task.project_id) if task.project_id else None
    if Capability.COMMENTS_WRITE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Your role doesn't allow commenting here.")
    comment = TaskComment(
        workspace_id=ctx.workspace.id, task_id=task.id, author_user_id=ctx.auth.user.id, body=body
    )
    db.add(comment)
    db.flush()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="task.comment_added",
        entity_type="task",
        entity_id=task.id,
        project_id=task.project_id,
        summary=f"Commented on {task.title}",
        changes={"comment_id": comment.id},
    )
    return _comment_out(comment)


def _get_comment(db: Session, ctx: WorkspaceContext, comment_id: uuid.UUID) -> tuple[TaskComment, Task]:
    comment = db.scalars(
        select(TaskComment).where(TaskComment.id == comment_id, TaskComment.workspace_id == ctx.workspace.id)
    ).one_or_none()
    if comment is None or comment.deleted_at is not None:
        raise ProblemError(404, "Comment not found.")
    try:
        task = get_task(db, ctx, comment.task_id)
    except ProblemError:
        raise ProblemError(404, "Comment not found.") from None
    return comment, task


def edit_comment(
    db: Session, ctx: WorkspaceContext, comment_id: uuid.UUID, body: str, meta: RequestMeta
) -> CommentOut:
    comment, task = _get_comment(db, ctx, comment_id)
    if comment.author_user_id != ctx.auth.user.id:
        raise ProblemError(403, "You can only edit your own comments.")
    comment.body, comment.edited_at = body, utcnow()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="task.comment_edited",
        entity_type="task",
        entity_id=task.id,
        project_id=task.project_id,
        summary=f"Edited a comment on {task.title}",
        changes={"comment_id": comment.id},
    )
    db.flush()
    return _comment_out(comment)


def delete_comment(db: Session, ctx: WorkspaceContext, comment_id: uuid.UUID, meta: RequestMeta) -> None:
    comment, task = _get_comment(db, ctx, comment_id)
    if comment.author_user_id != ctx.auth.user.id and ctx.role not in SEES_ALL_PROJECTS:
        raise ProblemError(403, "You can only delete your own comments.")
    comment.deleted_at = utcnow()
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="task.comment_deleted",
        entity_type="task",
        entity_id=task.id,
        project_id=task.project_id,
        summary=f"Deleted a comment on {task.title}",
        changes={"comment_id": comment.id},
    )
