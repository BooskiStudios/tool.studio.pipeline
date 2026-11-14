import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from booski_core.vocab import AccentColor


def _normalise_slug(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


DepartmentSlug = Annotated[
    str,
    BeforeValidator(_normalise_slug),
    StringConstraints(min_length=2, max_length=48, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"),
]
DepartmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
IconKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class DepartmentCreate(BaseModel):
    slug: DepartmentSlug
    name: DepartmentName
    description: Description = ""
    icon_key: IconKey = "layers"
    accent_color: AccentColor = "cyan"
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    """Only the fields you send change. The slug is permanent so links keep working."""

    name: DepartmentName | None = None
    description: Description | None = None
    icon_key: IconKey | None = None
    accent_color: AccentColor | None = None
    sort_order: int | None = None
    archived: bool | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str
    icon_key: str
    accent_color: AccentColor
    sort_order: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
