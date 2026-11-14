import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from booski_core.core.fields import Name120, Text5000
from booski_core.modules.tasks.progress import Progress
from booski_core.vocab import MilestoneStatus


class MilestoneCreate(BaseModel):
    name: Name120
    description: Text5000 = ""
    target_date: date | None = None
    status: MilestoneStatus = "planned"
    position: float | None = None  # default: after the project's last milestone


class MilestoneUpdate(BaseModel):
    name: Name120 | None = None
    description: Text5000 | None = None
    target_date: date | None = None
    status: MilestoneStatus | None = None
    position: float | None = None
    archived: bool | None = None
    version: int | None = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str
    target_date: date | None
    status: MilestoneStatus
    completed_at: datetime | None
    position: float
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    progress: Progress
