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
from booski_core.modules.ai.models import WorkspaceAiSettings
from booski_core.modules.workspaces.models import Invitation
from booski_core.security.tokens import hash_token
from helpers import sign_in
from studio import Studio, build_studio

pytestmark = pytest.mark.db

ADMINS = {Role.OWNER, Role.ADMIN}
DEVELOPERS = ADMINS | {Role.DEVELOPER}
CONTRIBUTORS = DEVELOPERS | {Role.COLLABORATOR}
EVERYONE = set(Role)
NOBODY: set[Role] = set()


@dataclass
class World:
    s: Studio
    invitation_id: uuid.UUID


@dataclass(frozen=True)
class Case:
    method: str
    template: str  # route path, for the coverage check
    allowed: set[Role]
    success: int
    path: Callable[[World], str]
    body: Callable[[World], dict[str, object]] | None = None


W = "/api/v1/w/{workspace_slug}"
B = "/api/v1/w/booski"
P = W + "/projects/{project_slug}"
MATRIX = [
    # ---- workspace, members, invitations (PR 2.2)
    Case("GET", W, EVERYONE, 200, lambda w: B),
    Case("PATCH", W, ADMINS, 200, lambda w: B, lambda w: {"name": "Renamed"}),
    Case("GET", W + "/members", EVERYONE, 200, lambda w: f"{B}/members"),
    Case(
        "PATCH",
        W + "/members/{user_id}",
        ADMINS,
        200,
        lambda w: f"{B}/members/{w.s.target.id}",
        lambda w: {"role": "developer"},
    ),
    Case("DELETE", W + "/members/{user_id}", ADMINS, 204, lambda w: f"{B}/members/{w.s.target.id}"),
    Case(
        "POST",
        W + "/ownership",
        {Role.OWNER},
        204,
        lambda w: f"{B}/ownership",
        lambda w: {"user_id": str(w.s.target.id)},
    ),
    Case("GET", W + "/invitations", ADMINS, 200, lambda w: f"{B}/invitations"),
    Case(
        "POST",
        W + "/invitations",
        ADMINS,
        201,
        lambda w: f"{B}/invitations",
        lambda w: {"email": "invitee@example.com", "role": "viewer"},
    ),
    Case(
        "DELETE",
        W + "/invitations/{invitation_id}",
        ADMINS,
        204,
        lambda w: f"{B}/invitations/{w.invitation_id}",
    ),
    # ---- departments
    Case("GET", W + "/departments", EVERYONE, 200, lambda w: f"{B}/departments"),
    Case(
        "POST",
        W + "/departments",
        ADMINS,
        201,
        lambda w: f"{B}/departments",
        lambda w: {"slug": "research", "name": "Research"},
    ),
    Case(
        "GET",
        W + "/departments/{department_slug}",
        EVERYONE,
        200,
        lambda w: f"{B}/departments/game-development",
    ),
    Case(
        "PATCH",
        W + "/departments/{department_slug}",
        ADMINS,
        200,
        lambda w: f"{B}/departments/game-development",
        lambda w: {"name": "Game Dev"},
    ),
    # ---- projects, access lists, workstreams
    Case("GET", W + "/projects", EVERYONE, 200, lambda w: f"{B}/projects"),
    Case(
        "POST",
        W + "/projects",
        ADMINS,
        201,
        lambda w: f"{B}/projects",
        lambda w: {"slug": "new-game", "name": "New Game"},
    ),
    Case("GET", P, EVERYONE, 200, lambda w: f"{B}/projects/horizon"),
    Case("PATCH", P, ADMINS, 200, lambda w: f"{B}/projects/horizon", lambda w: {"status": "production"}),
    Case("GET", P + "/members", EVERYONE, 200, lambda w: f"{B}/projects/horizon/members"),
    Case(
        "PUT",
        P + "/members/{user_id}",
        ADMINS,
        200,
        lambda w: f"{B}/projects/horizon/members/{w.s.target.id}",
        lambda w: {"access": "viewer"},
    ),
    Case(
        "DELETE",
        P + "/members/{user_id}",
        ADMINS,
        204,
        lambda w: f"{B}/projects/horizon/members/{w.s.target.id}",
    ),
    Case("GET", P + "/workstreams", EVERYONE, 200, lambda w: f"{B}/projects/horizon/workstreams"),
    Case(
        "POST",
        P + "/workstreams",
        ADMINS,
        201,
        lambda w: f"{B}/projects/horizon/workstreams",
        lambda w: {"department_id": str(w.s.department_id), "name": "Audio"},
    ),
    Case(
        "PATCH",
        P + "/workstreams/{workstream_id}",
        ADMINS,
        200,
        lambda w: f"{B}/projects/horizon/workstreams/{w.s.workstream_id}",
        lambda w: {"name": "Gameplay"},
    ),
    # ---- milestones
    Case("GET", P + "/milestones", EVERYONE, 200, lambda w: f"{B}/projects/horizon/milestones"),
    Case(
        "POST",
        P + "/milestones",
        DEVELOPERS,
        201,
        lambda w: f"{B}/projects/horizon/milestones",
        lambda w: {"name": "Alpha"},
    ),
    Case(
        "GET", W + "/milestones/{milestone_id}", EVERYONE, 200, lambda w: f"{B}/milestones/{w.s.milestone_id}"
    ),
    Case(
        "PATCH",
        W + "/milestones/{milestone_id}",
        DEVELOPERS,
        200,
        lambda w: f"{B}/milestones/{w.s.milestone_id}",
        lambda w: {"status": "in_progress"},
    ),
    # ---- tasks and comments
    Case("GET", W + "/tasks", EVERYONE, 200, lambda w: f"{B}/tasks"),
    Case(
        "POST",
        W + "/tasks",
        CONTRIBUTORS,
        201,
        lambda w: f"{B}/tasks",
        lambda w: {"title": "New task", "project_id": str(w.s.project_id)},
    ),
    Case("GET", W + "/tasks/{task_id}", EVERYONE, 200, lambda w: f"{B}/tasks/{w.s.task_id}"),
    # Collaborators may only edit tasks they created or are assigned to; this one is the owner's.
    Case(
        "PATCH",
        W + "/tasks/{task_id}",
        DEVELOPERS,
        200,
        lambda w: f"{B}/tasks/{w.s.task_id}",
        lambda w: {"priority": "high"},
    ),
    Case("GET", W + "/tasks/{task_id}/history", EVERYONE, 200, lambda w: f"{B}/tasks/{w.s.task_id}/history"),
    Case(
        "GET", W + "/tasks/{task_id}/comments", EVERYONE, 200, lambda w: f"{B}/tasks/{w.s.task_id}/comments"
    ),
    Case(
        "POST",
        W + "/tasks/{task_id}/comments",
        CONTRIBUTORS,
        201,
        lambda w: f"{B}/tasks/{w.s.task_id}/comments",
        lambda w: {"body": "Agreed"},
    ),
    Case(
        "PATCH",
        W + "/comments/{comment_id}",
        {Role.OWNER},
        200,
        lambda w: f"{B}/comments/{w.s.comment_id}",
        lambda w: {"body": "Edited"},
    ),
    Case("DELETE", W + "/comments/{comment_id}", ADMINS, 204, lambda w: f"{B}/comments/{w.s.comment_id}"),
    # ---- knowledge
    Case("GET", W + "/documents", EVERYONE, 200, lambda w: f"{B}/documents"),
    Case(
        "POST",
        W + "/documents",
        DEVELOPERS,
        201,
        lambda w: f"{B}/documents",
        lambda w: {"kind": "note", "title": "Notes"},
    ),
    Case("GET", W + "/documents/{document_id}", EVERYONE, 200, lambda w: f"{B}/documents/{w.s.document_id}"),
    Case(
        "PATCH",
        W + "/documents/{document_id}",
        DEVELOPERS,
        200,
        lambda w: f"{B}/documents/{w.s.document_id}",
        lambda w: {"body": "# Updated"},
    ),
    Case(
        "GET",
        W + "/documents/{document_id}/revisions",
        EVERYONE,
        200,
        lambda w: f"{B}/documents/{w.s.document_id}/revisions",
    ),
    Case(
        "GET",
        W + "/documents/{document_id}/revisions/{revision_no}",
        EVERYONE,
        200,
        lambda w: f"{B}/documents/{w.s.document_id}/revisions/1",
    ),
    # ---- decisions
    Case("GET", W + "/decisions", EVERYONE, 200, lambda w: f"{B}/decisions"),
    Case(
        "POST",
        W + "/decisions",
        DEVELOPERS,
        201,
        lambda w: f"{B}/decisions",
        lambda w: {"title": "Ship on Steam"},
    ),
    Case("GET", W + "/decisions/{decision_id}", EVERYONE, 200, lambda w: f"{B}/decisions/{w.s.decision_id}"),
    Case(
        "PATCH",
        W + "/decisions/{decision_id}",
        DEVELOPERS,
        200,
        lambda w: f"{B}/decisions/{w.s.decision_id}",
        lambda w: {"rationale": "Team knows it"},
    ),
    Case(
        "GET",
        W + "/decisions/{decision_id}/history",
        EVERYONE,
        200,
        lambda w: f"{B}/decisions/{w.s.decision_id}/history",
    ),
    # ---- approvals (requested by a separate developer, so no role below is the requester)
    Case("GET", W + "/approvals", EVERYONE, 200, lambda w: f"{B}/approvals"),
    Case(
        "POST",
        W + "/approvals",
        DEVELOPERS,
        201,
        lambda w: f"{B}/approvals",
        lambda w: {"title": "Publish trailer", "kind": "publishing"},
    ),
    Case("GET", W + "/approvals/{approval_id}", EVERYONE, 200, lambda w: f"{B}/approvals/{w.s.approval_id}"),
    Case(
        "PATCH",
        W + "/approvals/{approval_id}",
        ADMINS,
        200,
        lambda w: f"{B}/approvals/{w.s.approval_id}",
        lambda w: {"reviewer_user_id": str(w.s.members[Role.DEVELOPER].id)},
    ),
    Case(
        "GET",
        W + "/approvals/{approval_id}/reviews",
        EVERYONE,
        200,
        lambda w: f"{B}/approvals/{w.s.approval_id}/reviews",
    ),
    Case(
        "POST",
        W + "/approvals/{approval_id}/reviews",
        ADMINS,
        201,
        lambda w: f"{B}/approvals/{w.s.approval_id}/reviews",
        lambda w: {"action": "approve"},
    ),
    Case(
        "POST",
        W + "/approvals/{approval_id}/resubmit",
        NOBODY,
        200,
        lambda w: f"{B}/approvals/{w.s.approval_id}/resubmit",
        lambda w: {},
    ),
    Case(
        "POST",
        W + "/approvals/{approval_id}/cancel",
        ADMINS,
        200,
        lambda w: f"{B}/approvals/{w.s.approval_id}/cancel",
        lambda w: {},
    ),
    # ---- activity
    Case("GET", W + "/activity", EVERYONE, 200, lambda w: f"{B}/activity"),
    # ---- AI (PR 3.2): owners and admins only (D36). AI is switched on in this world.
    Case("GET", W + "/ai/settings", ADMINS, 200, lambda w: f"{B}/ai/settings"),
    Case(
        "PATCH",
        W + "/ai/settings",
        ADMINS,
        200,
        lambda w: f"{B}/ai/settings",
        lambda w: {"monthly_budget_usd": "25"},
    ),
    Case("POST", W + "/ai/check", ADMINS, 200, lambda w: f"{B}/ai/check", lambda w: {}),
    Case("GET", W + "/ai/catalog", ADMINS, 200, lambda w: f"{B}/ai/catalog"),
    Case("GET", W + "/ai/usage", ADMINS, 200, lambda w: f"{B}/ai/usage"),
    Case("GET", W + "/ai/requests", ADMINS, 200, lambda w: f"{B}/ai/requests"),
]


@pytest.fixture
def world(db: Session) -> World:
    studio = build_studio(db)
    invitation = Invitation(
        workspace_id=studio.workspace_id,
        email="pending@example.com",
        role="viewer",
        token_hash=hash_token(uuid.uuid4().hex),
        invited_by_user_id=studio.members[Role.OWNER].id,
        expires_at=utcnow().replace(year=utcnow().year + 1),
    )
    db.add(invitation)
    db.add(WorkspaceAiSettings(workspace_id=studio.workspace_id, enabled=True))
    db.commit()
    return World(studio, invitation.id)


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
    client = sign_in(make_client(), world.s.members[role])
    expected = case.success if role in case.allowed else 403
    assert _call(client, case, world) == expected


@pytest.mark.parametrize("case", MATRIX, ids=_id)
def test_non_members_get_not_found(case: Case, world: World, make_client: Callable[..., TestClient]) -> None:
    assert _call(sign_in(make_client(), world.s.outsider), case, world) == 404


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
