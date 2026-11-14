import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from booski_core.access.roles import Role
from booski_core.core.fields import DisplayName, Email, NewPassword
from booski_core.modules.identity.schemas import UserOut


def _normalise_slug(value: object) -> object:
    # Lower-case before the pattern check (StringConstraints checks the pattern on the raw input).
    return value.strip().lower() if isinstance(value, str) else value


Slug = Annotated[
    str,
    BeforeValidator(_normalise_slug),
    StringConstraints(min_length=3, max_length=48, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"),
]
WorkspaceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# "owner" is deliberately absent: ownership only moves by transfer.
AssignableRole = Literal["admin", "developer", "collaborator", "viewer"]
InvitationTokenField = Annotated[str, Field(min_length=20, max_length=128)]


class WorkspaceCreate(BaseModel):
    name: WorkspaceName
    slug: Slug


class WorkspaceUpdate(BaseModel):
    name: WorkspaceName


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    created_at: datetime
    role: Role  # the caller's role


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    role: Role
    joined_at: datetime


class RoleChange(BaseModel):
    role: AssignableRole


class OwnershipTransfer(BaseModel):
    user_id: uuid.UUID


class InvitationCreate(BaseModel):
    email: Email
    role: AssignableRole


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    created_at: datetime
    expires_at: datetime
    invited_by_user_id: uuid.UUID | None


class InvitationCreated(BaseModel):
    invitation: InvitationOut
    token: str = Field(
        description="Shown once. Share it with the invitee; it is not stored and can't be shown again."
    )


class InvitationTokenBody(BaseModel):
    token: InvitationTokenField


class InvitationPreview(BaseModel):
    workspace_slug: str
    workspace_name: str
    email: str
    role: Role
    expires_at: datetime
    account_exists: bool


class InvitationAccept(BaseModel):
    token: InvitationTokenField
    # Required only when no account exists yet for the invited email.
    display_name: DisplayName | None = None
    password: NewPassword | None = None


class InvitationAccepted(BaseModel):
    workspace: WorkspaceOut
    user: UserOut
    signed_in: bool  # True when a new account was created and signed in
    csrf_token: str | None = None
