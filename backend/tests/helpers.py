"""Helpers for arranging test data directly in the database, and for signing in."""

import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.core.request_meta import utcnow
from booski_core.models import Membership, User, Workspace
from booski_core.modules.identity.dependencies import CSRF_HEADER
from booski_core.modules.identity.service import set_password

DEFAULT_PASSWORD = "correct horse battery staple"


@dataclass(frozen=True)
class Account:
    id: uuid.UUID
    email: str
    password: str


def make_user(
    db: Session, email: str, *, password: str = DEFAULT_PASSWORD, name: str | None = None, active: bool = True
) -> Account:
    user = User(email=email, display_name=name or email.split("@")[0].title(), is_active=active)
    set_password(user, password, utcnow())
    db.add(user)
    db.commit()
    return Account(id=user.id, email=email, password=password)


def make_workspace(db: Session, owner: Account, slug: str, name: str | None = None) -> uuid.UUID:
    workspace = Workspace(slug=slug, name=name or slug.title(), created_by_user_id=owner.id)
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=owner.id, role=Role.OWNER.value))
    db.commit()
    return workspace.id


def add_member(db: Session, workspace_id: uuid.UUID, account: Account, role: Role) -> None:
    db.add(Membership(workspace_id=workspace_id, user_id=account.id, role=role.value))
    db.commit()


def sign_in(client: TestClient, account: Account) -> TestClient:
    """Signs the client in and makes it send the CSRF header on every request, like the frontend will."""
    response = client.post("/api/v1/auth/login", json={"email": account.email, "password": account.password})
    assert response.status_code == 200, response.text
    client.headers[CSRF_HEADER] = response.json()["csrf_token"]
    return client
