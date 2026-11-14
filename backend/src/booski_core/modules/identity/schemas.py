import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from booski_core.access.roles import Role
from booski_core.core.fields import Email, NewPassword, SubmittedPassword
from booski_core.core.request_meta import IpAddress


class LoginRequest(BaseModel):
    email: Email
    password: SubmittedPassword


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    ip: IpAddress | None
    user_agent: str | None
    current: bool = False


class LoginResponse(BaseModel):
    user: UserOut
    session: SessionOut
    csrf_token: str  # also set as a cookie; send it back in the X-CSRF-Token header


class MembershipSummary(BaseModel):
    workspace_id: uuid.UUID
    workspace_slug: str
    workspace_name: str
    role: Role


class MeResponse(BaseModel):
    user: UserOut
    session: SessionOut
    workspaces: list[MembershipSummary]


class PasswordChangeRequest(BaseModel):
    current_password: SubmittedPassword
    new_password: NewPassword


class RevokedCount(BaseModel):
    revoked: int
