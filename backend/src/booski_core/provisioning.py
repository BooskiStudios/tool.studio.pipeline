"""Operator commands run on the server (``booski create-owner``, ``set-password``, ``deactivate-user``).

There are no default or hardcoded credentials: the first owner is created here with a password typed at
a hidden prompt (or piped on stdin for automation). Everyone else joins through invitations.
"""

import uuid
from dataclasses import dataclass

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from booski_core.core.errors import ProblemError
from booski_core.core.fields import DisplayName, Email, NewPassword
from booski_core.core.request_meta import SYSTEM_META, utcnow
from booski_core.modules.activity.service import record_event
from booski_core.modules.identity import service as identity
from booski_core.modules.identity.models import User
from booski_core.modules.workspaces import service as workspaces
from booski_core.modules.workspaces.schemas import Slug, WorkspaceName


class ProvisioningError(Exception):
    """A problem the operator can fix; the message says how."""


def _validated[T](adapter: TypeAdapter[T], value: object, label: str) -> T:
    try:
        return adapter.validate_python(value)
    except ValidationError as error:
        raise ProvisioningError(f"Invalid {label}: {error.errors()[0]['msg']}") from None


_EMAIL = TypeAdapter(Email)
_DISPLAY_NAME = TypeAdapter(DisplayName)
_PASSWORD = TypeAdapter(NewPassword)
_SLUG = TypeAdapter(Slug)
_WORKSPACE_NAME = TypeAdapter(WorkspaceName)


def validate_new_password(password: str) -> str:
    return _validated(_PASSWORD, password, "password")


@dataclass(frozen=True)
class CreatedOwner:
    user_id: uuid.UUID
    workspace_slug: str


def create_owner(
    db: Session, *, email: str, display_name: str, password: str, workspace_name: str, workspace_slug: str
) -> CreatedOwner:
    email = _validated(_EMAIL, email, "email")
    display_name = _validated(_DISPLAY_NAME, display_name, "display name")
    password = validate_new_password(password)
    workspace_name = _validated(_WORKSPACE_NAME, workspace_name, "workspace name")
    workspace_slug = _validated(_SLUG, workspace_slug, "workspace address")
    if identity.get_user_by_email(db, email) is not None:
        raise ProvisioningError(f"An account for {email} already exists.")

    now = utcnow()
    user = User(email=email, display_name=display_name)
    try:
        identity.set_password(user, password, now)
        db.add(user)
        db.flush()
        record_event(
            db,
            verb="user.created",
            entity_type="user",
            entity_id=user.id,
            summary="Created the owner account from the command line",
            meta=SYSTEM_META,
        )
        workspace, _ = workspaces.create_workspace(
            db, user, workspace_name, workspace_slug, SYSTEM_META, actor_user_id=None
        )
    except ProblemError as error:
        db.rollback()
        raise ProvisioningError(error.detail or str(error)) from None
    db.commit()
    return CreatedOwner(user_id=user.id, workspace_slug=workspace.slug)


def _require_user(db: Session, email: str) -> User:
    user = identity.get_user_by_email(db, _validated(_EMAIL, email, "email"))
    if user is None:
        raise ProvisioningError(f"No account exists for {email}.")
    return user


def set_password(db: Session, *, email: str, password: str) -> int:
    """Resets a password (e.g. a forgotten one) and signs out all of that user's sessions."""
    user = _require_user(db, email)
    now = utcnow()
    try:
        identity.set_password(user, validate_new_password(password), now)
    except ProblemError as error:
        raise ProvisioningError(error.detail or str(error)) from None
    revoked = identity.revoke_user_sessions(db, user.id, "password_reset", now)
    record_event(
        db,
        verb="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        summary="Password reset from the command line",
        meta=SYSTEM_META,
        changes={"sessions_revoked": revoked},
    )
    db.commit()
    return revoked


def set_active(db: Session, *, email: str, active: bool) -> int:
    """Deactivating blocks sign-in and ends every session at once. Memberships are kept."""
    user = _require_user(db, email)
    user.is_active = active
    revoked = 0 if active else identity.revoke_user_sessions(db, user.id, "deactivated", utcnow())
    record_event(
        db,
        verb="user.activated" if active else "user.deactivated",
        entity_type="user",
        entity_id=user.id,
        summary=("Reactivated" if active else "Deactivated") + " account from the command line",
        meta=SYSTEM_META,
        changes={"sessions_revoked": revoked},
    )
    db.commit()
    return revoked
