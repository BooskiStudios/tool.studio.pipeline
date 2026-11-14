import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from booski_core.core.fields import Text10000, Text20000, Title
from booski_core.vocab import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: Title
    description: Text20000 = ""
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    project_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    workstream_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    assignee_user_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    position: float | None = None  # default: after the last task in the same project

    @model_validator(mode="after")
    def _dates_ordered(self) -> "TaskCreate":
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValueError("due_date can't be before start_date")
        return self


class TaskUpdate(BaseModel):
    """Only the fields you send change; send ``null`` to clear an optional link. A task's project is fixed
    when it's created. Send ``version`` to detect conflicting edits."""

    title: Title | None = None
    description: Text20000 | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    department_id: uuid.UUID | None = None
    workstream_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    assignee_user_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    position: float | None = None
    archived: bool | None = None
    version: int | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    workstream_id: uuid.UUID | None
    milestone_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    assignee_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    start_date: date | None
    due_date: date | None
    completed_at: datetime | None
    position: float
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    can_edit: bool


TaskSort = Literal["position", "due_date", "priority", "created_at", "updated_at"]


class CommentCreate(BaseModel):
    body: Text10000


class CommentOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author_user_id: uuid.UUID | None
    body: str  # empty when deleted
    created_at: datetime
    edited_at: datetime | None
    deleted: bool
