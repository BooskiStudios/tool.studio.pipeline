"""Workspaces and memberships: creation, isolation between workspaces, role changes and ownership."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.modules.activity.models import ActivityEvent
from booski_core.modules.workspaces.models import Membership
from helpers import Account, add_member, make_user, make_workspace

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]


@dataclass
class Studio:
    """One workspace with a member of every role, plus an unrelated workspace next door."""

    workspace_id: uuid.UUID
    members: dict[Role, Account]
    neighbour: Account  # owner of the other workspace
    neighbour_member: Account


@pytest.fixture
def studio(db: Session) -> Studio:
    owner = make_user(db, "owner@booski.test")
    workspace_id = make_workspace(db, owner, "booski", "Booski Studios")
    members = {Role.OWNER: owner}
    for role in (Role.ADMIN, Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER):
        members[role] = make_user(db, f"{role.value}@booski.test")
        add_member(db, workspace_id, members[role], role)
    neighbour = make_user(db, "rival@other.test")
    other_id = make_workspace(db, neighbour, "other-studio", "Other Studio")
    neighbour_member = make_user(db, "rival.dev@other.test")
    add_member(db, other_id, neighbour_member, Role.DEVELOPER)
    return Studio(workspace_id, members, neighbour, neighbour_member)


def _role_of(db: Session, workspace_id: uuid.UUID, account: Account) -> str | None:
    db.expire_all()
    return db.scalar(
        select(Membership.role).where(
            Membership.workspace_id == workspace_id, Membership.user_id == account.id
        )
    )


# ---------------------------------------------------------------- creating and listing


def test_create_workspace_makes_you_owner(signed_in: SignedIn, db: Session) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    response = client.post("/api/v1/workspaces", json={"name": "Ada's Studio", "slug": "Ada-Studio"})
    assert response.status_code == 201
    assert response.json()["slug"] == "ada-studio"
    assert response.json()["role"] == "owner"
    assert [w["slug"] for w in client.get("/api/v1/workspaces").json()] == ["ada-studio"]


def test_workspace_address_must_be_unique_and_well_formed(signed_in: SignedIn, db: Session) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    assert client.post("/api/v1/workspaces", json={"name": "One", "slug": "studio"}).status_code == 201
    taken = client.post("/api/v1/workspaces", json={"name": "Two", "slug": "studio"})
    assert taken.status_code == 409
    for bad in ("a", "has space", "-leading", "trailing-", "UNDER_score", "x" * 49):
        assert client.post("/api/v1/workspaces", json={"name": "Bad", "slug": bad}).status_code == 422


def test_you_only_see_workspaces_you_belong_to(signed_in: SignedIn, studio: Studio) -> None:
    client = signed_in(studio.members[Role.VIEWER])
    assert [w["slug"] for w in client.get("/api/v1/workspaces").json()] == ["booski"]
    me = client.get("/api/v1/auth/me").json()
    assert me["workspaces"] == [
        {
            "workspace_id": str(studio.workspace_id),
            "workspace_slug": "booski",
            "workspace_name": "Booski Studios",
            "role": "viewer",
        }
    ]


# ---------------------------------------------------------------- isolation between workspaces


def test_non_members_get_not_found_whether_or_not_the_workspace_exists(
    signed_in: SignedIn, studio: Studio
) -> None:
    outsider = signed_in(studio.neighbour)
    existing = outsider.get("/api/v1/w/booski")
    missing = outsider.get("/api/v1/w/no-such-workspace")
    assert existing.status_code == missing.status_code == 404
    assert existing.json()["detail"] == missing.json()["detail"] == "Workspace not found."
    for path in ("/members", "/invitations"):
        assert outsider.get(f"/api/v1/w/booski{path}").status_code == 404
    assert outsider.patch("/api/v1/w/booski", json={"name": "Hijacked"}).status_code == 404


def test_member_ids_from_another_workspace_are_not_found(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    """Insecure direct object reference check: a valid user id from elsewhere must not resolve here."""
    owner = signed_in(studio.members[Role.OWNER])
    foreign = studio.neighbour_member.id
    assert owner.patch(f"/api/v1/w/booski/members/{foreign}", json={"role": "viewer"}).status_code == 404
    assert owner.delete(f"/api/v1/w/booski/members/{foreign}").status_code == 404
    assert owner.post("/api/v1/w/booski/ownership", json={"user_id": str(foreign)}).status_code == 404
    assert _role_of(db, studio.workspace_id, studio.neighbour_member) is None


def test_removed_member_loses_access_immediately(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    assert developer.get("/api/v1/w/booski").status_code == 200
    admin = signed_in(studio.members[Role.ADMIN])
    assert admin.delete(f"/api/v1/w/booski/members/{studio.members[Role.DEVELOPER].id}").status_code == 204
    assert developer.get("/api/v1/w/booski").status_code == 404


# ---------------------------------------------------------------- role changes


def test_admin_can_change_roles_below_admin(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    admin = signed_in(studio.members[Role.ADMIN])
    viewer = studio.members[Role.VIEWER]
    response = admin.patch(f"/api/v1/w/booski/members/{viewer.id}", json={"role": "developer"})
    assert response.status_code == 200
    assert response.json()["role"] == "developer"
    assert _role_of(db, studio.workspace_id, viewer) == "developer"
    event = db.scalars(select(ActivityEvent).where(ActivityEvent.verb == "membership.role_changed")).one()
    assert event.changes["role"] == {"from": "viewer", "to": "developer"}
    assert event.workspace_id == studio.workspace_id


def test_admin_cannot_promote_to_admin_or_touch_other_admins(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    second_admin = make_user(db, "admin2@booski.test")
    add_member(db, studio.workspace_id, second_admin, Role.ADMIN)
    admin = signed_in(studio.members[Role.ADMIN])
    viewer = studio.members[Role.VIEWER]
    assert admin.patch(f"/api/v1/w/booski/members/{viewer.id}", json={"role": "admin"}).status_code == 403
    assert (
        admin.patch(f"/api/v1/w/booski/members/{second_admin.id}", json={"role": "viewer"}).status_code == 403
    )
    assert admin.delete(f"/api/v1/w/booski/members/{second_admin.id}").status_code == 403
    assert _role_of(db, studio.workspace_id, second_admin) == "admin"


def test_owner_can_promote_to_admin(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    developer = studio.members[Role.DEVELOPER]
    assert owner.patch(f"/api/v1/w/booski/members/{developer.id}", json={"role": "admin"}).status_code == 200
    assert _role_of(db, studio.workspace_id, developer) == "admin"


def test_nobody_can_assign_owner_change_the_owner_or_their_own_role(
    signed_in: SignedIn, studio: Studio
) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    admin = signed_in(studio.members[Role.ADMIN])
    viewer_id = studio.members[Role.VIEWER].id
    assert owner.patch(f"/api/v1/w/booski/members/{viewer_id}", json={"role": "owner"}).status_code == 422
    assert (
        admin.patch(
            f"/api/v1/w/booski/members/{studio.members[Role.OWNER].id}", json={"role": "viewer"}
        ).status_code
        == 409
    )
    assert (
        admin.patch(
            f"/api/v1/w/booski/members/{studio.members[Role.ADMIN].id}", json={"role": "viewer"}
        ).status_code
        == 403
    )


# ---------------------------------------------------------------- leaving and removing


def test_any_member_can_leave_except_the_owner(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    viewer = studio.members[Role.VIEWER]
    assert signed_in(viewer).delete(f"/api/v1/w/booski/members/{viewer.id}").status_code == 204
    assert _role_of(db, studio.workspace_id, viewer) is None
    owner = studio.members[Role.OWNER]
    response = signed_in(owner).delete(f"/api/v1/w/booski/members/{owner.id}")
    assert response.status_code == 409
    assert "Transfer ownership" in response.json()["detail"]


def test_members_without_manage_rights_cannot_remove_others(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    response = developer.delete(f"/api/v1/w/booski/members/{studio.members[Role.VIEWER].id}")
    assert response.status_code == 403


# ---------------------------------------------------------------- ownership


def test_ownership_transfer(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    developer = studio.members[Role.DEVELOPER]
    assert owner.post("/api/v1/w/booski/ownership", json={"user_id": str(developer.id)}).status_code == 204
    assert _role_of(db, studio.workspace_id, developer) == "owner"
    assert _role_of(db, studio.workspace_id, studio.members[Role.OWNER]) == "admin"
    # The former owner has lost owner-only powers straight away.
    again = owner.post("/api/v1/w/booski/ownership", json={"user_id": str(developer.id)})
    assert again.status_code == 403


def test_database_allows_only_one_owner_per_workspace(studio: Studio, db: Session) -> None:
    db.add(Membership(workspace_id=studio.workspace_id, user_id=studio.neighbour.id, role="owner"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------- audit log


def test_activity_log_is_append_only(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    signed_in(studio.members[Role.OWNER])  # writes a user.signed_in event
    for statement in ("UPDATE activity_events SET summary = 'tampered'", "DELETE FROM activity_events"):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement))
        db.rollback()
    assert db.scalar(select(ActivityEvent.summary)) == "Signed in"
