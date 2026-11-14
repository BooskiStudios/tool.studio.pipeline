import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from booski_core.access.roles import Capability
from booski_core.core.fields import (
    HttpsUrl,
    Label40,
    Label80,
    Name80,
    Name120,
    ProjectSlug,
    Text2000,
    Text5000,
)
from booski_core.modules.tasks.progress import Progress
from booski_core.vocab import AccentColor, ProjectAccess, ProjectStatus, ProjectVisibility

PropertyValue = str | int | float | bool | None
Properties = Annotated[dict[str, PropertyValue], Field(max_length=50)]


def _check_properties(value: dict[str, PropertyValue] | None) -> dict[str, PropertyValue] | None:
    if value is None:
        return value
    for key, item in value.items():
        if not 1 <= len(key) <= 64:
            raise ValueError("property names must be 1-64 characters")
        if isinstance(item, str) and len(item) > 1000:
            raise ValueError("property values must be at most 1000 characters")
    return value


class ProjectCreate(BaseModel):
    slug: ProjectSlug
    name: Name120
    description: Text5000 = ""
    project_type: Label80 = ""
    engine: Label40 = ""
    status: ProjectStatus = "concept"
    visibility: ProjectVisibility = "workspace"
    accent_color: AccentColor = "cyan"
    cover_image_url: HttpsUrl | None = None
    properties: Properties = Field(default_factory=dict)

    _properties = field_validator("properties")(_check_properties)


class ProjectUpdate(BaseModel):
    """Only the fields you send change; the slug is permanent. Send ``version`` to detect conflicts."""

    name: Name120 | None = None
    description: Text5000 | None = None
    project_type: Label80 | None = None
    engine: Label40 | None = None
    status: ProjectStatus | None = None
    visibility: ProjectVisibility | None = None
    accent_color: AccentColor | None = None
    cover_image_url: HttpsUrl | None = None
    properties: Properties | None = None
    archived: bool | None = None
    version: int | None = None

    _properties = field_validator("properties")(_check_properties)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str
    project_type: str
    engine: str
    status: ProjectStatus
    visibility: ProjectVisibility
    accent_color: AccentColor
    cover_image_url: str | None
    properties: dict[str, PropertyValue]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    progress: Progress
    capabilities: list[Capability] = Field(description="What you can do in this project.")


ProjectSort = Literal["updated_at", "created_at", "name"]


class ProjectMemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    access: ProjectAccess
    added_at: datetime


class ProjectMemberSet(BaseModel):
    access: ProjectAccess


class WorkstreamCreate(BaseModel):
    department_id: uuid.UUID
    name: Name80
    description: Text2000 = ""
    sort_order: int = 0


class WorkstreamUpdate(BaseModel):
    name: Name80 | None = None
    description: Text2000 | None = None
    sort_order: int | None = None
    archived: bool | None = None


class WorkstreamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    department_id: uuid.UUID
    name: str
    description: str
    sort_order: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
