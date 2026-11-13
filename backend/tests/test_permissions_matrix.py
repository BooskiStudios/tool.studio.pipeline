"""Every workspace endpoint for every role, plus non-members and signed-out callers.

When you add a route under /api/v1/w/{workspace_slug}, add it to MATRIX: the coverage test fails until you do.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.core.request_meta import utcnow
from booski_core.modules.workspaces.models import Invitation
from booski_core.security.tokens import hash_token
from helpers import Account, add_member, make_user, make_workspace, sign_in

pytestmark = pytest.mark.db

ADMINS = {Role.OWNER, Role.ADMIN}
EVERYONE = set(Role)


@dataclass(frozen=True)
class Case:
    method: str
    template: str  # route path, for the coverage check
    allowed: set[Role]
    success: int
    path: Callable[["World"], str]
    body: Callable[["World"], dict[str, object]] | None = None


@dataclass
class World:
    members: dict[Role, Account]
    target: Account  # a viewer that member-management actions are aimed at
    invitation_id: uuid.UUID
    outsider: Account


W = "/api/v1/w/{workspace_slug}"
MATRIX = [
    Case("GET", W, EVERYONE, 200, lambda w: "/api/v1/w/booski"),
    Case("PATCH", W, ADMINS, 200, lambda w: "/api/v1/w/booski", lambda w: {"name": "Renamed"}),
    Case("GET", W + "/members", EVERYONE, 200, lambda w: "/api/v1/w/booski/members"),
    Case(
        "PATCH",
        W + "/members/{user_id}",
        ADMINS,
        200,
        lambda w: f"/api/v1/w/booski/members/{w.target.id}",
        lambda w: {"role": "developer"},
    ),
    Case(
        "DELETE", W + "/members/{user_id}", ADMINS, 204, lambda w: f"/api/v1/w/booski/members/{w.target.id}"
    ),
    Case(
        "POST",
        W + "/ownership",
        {Role.OWNER},
        204,
        lambda w: "/api/v1/w/booski/ownership",
        lambda w: {"user_id": str(w.target.id)},
    ),
    Case("GET", W + "/invitations", ADMINS, 200, lambda w: "/api/v1/w/booski/invitations"),
    Case(
        "POST",
        W + "/invitations",
        ADMINS,
        201,
        lambda w: "/api/v1/w/booski/invitations",
        lambda w: {"email": "invitee@example.com", "role": "viewer"},
    ),
    Case(
        "DELETE",
        W + "/invitations/{invitation_id}",
        ADMINS,
        204,
        lambda w: f"/api/v1/w/booski/invitations/{w.invitation_id}",
    ),
]


@pytest.fixture
def world(db: Session) -> World:
    members = {Role.OWNER: make_user(db, "owner@booski.test")}
    workspace_id = make_workspace(db, members[Role.OWNER], "booski")
    for role in (Role.ADMIN, Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER):
        members[role] = make_user(db, f"{role.value}@booski.test")
        add_member(db, workspace_id, members[role], role)
    target = make_user(db, "target@booski.test")
    add_member(db, workspace_id, target, Role.VIEWER)
    invitation = Invitation(
        workspace_id=workspace_id,
        email="pending@example.com",
        role="viewer",
        token_hash=hash_token(uuid.uuid4().hex),
        invited_by_user_id=members[Role.OWNER].id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    )
    db.add(invitation)
    db.commit()
    outsider = make_user(db, "outsider@elsewhere.test")
    make_workspace(db, outsider, "elsewhere")
    return World(members, target, invitation.id, outsider)


def _call(client: TestClient, case: Case, world: World) -> int:
    body = case.body(world) if case.body else None
    return client.request(case.method, case.path(world), json=body).status_code


def _id(case: Case) -> str:
    return f"{case.method} {case.template.removeprefix(W) or '/'}"


@pytest.mark.parametrize("role", list(Role), ids=lambda r: r.value)
@pytest.mark.parametrize("case", MATRIX, ids=_id)
def test_role_permissions(
    case: Case, role: Role, world: World, make_client: Callable[..., TestClient]
) -> None:
    client = sign_in(make_client(), world.members[role])
    expected = case.success if role in case.allowed else 403
    assert _call(client, case, world) == expected


@pytest.mark.parametrize("case", MATRIX, ids=_id)
def test_non_members_get_not_found(case: Case, world: World, make_client: Callable[..., TestClient]) -> None:
    assert _call(sign_in(make_client(), world.outsider), case, world) == 404


@pytest.mark.parametrize("case", MATRIX, ids=_id)
def test_signed_out_callers_get_unauthorised(case: Case, world: World, client: TestClient) -> None:
    assert _call(client, case, world) == 401


def test_matrix_covers_every_workspace_route(app: FastAPI) -> None:
    routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/w/")
        for method in operations
    }
    assert routes  # guards against the check silently matching nothing
    assert routes == {(case.method, case.template) for case in MATRIX}
