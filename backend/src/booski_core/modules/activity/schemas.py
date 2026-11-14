import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    verb: str
    entity_type: str
    entity_id: uuid.UUID | None
    project_id: uuid.UUID | None
    actor_type: Literal["user", "system"]
    actor_user_id: uuid.UUID | None
    summary: str
    changes: dict[str, Any]
    request_id: str | None
