"""Invitations: creating, previewing, accepting (new and existing accounts), expiry and revocation."""

import hashlib
import uuid
from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.core.request_meta import utcnow
from booski_core.modules.identity.dependencies import CSRF_HEADER, SESSION_COOKIE
from booski_core.modules.workspaces.models import Invitation, Membership
from helpers import Account, add_member, make_user, make_workspace

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]
INVITES = "/api/v1/w/booski/invitations"


@pytest.fixture
def owner(db: Session) -> Account:
    return make_user(db, "owner@booski.test")


@pytest.fixture
def workspace_id(db: Session, owner: Account) -> uuid.UUID:
    return make_workspace(db, owner, "booski", "Booski Studios")


def _invite(client: TestClient, email: str, role: str = "developer") -> str:
    response = client.post(INVITES, json={"email": email, "role": role})
    assert response.status_code == 201, response.text
    token: str = response.json()["token"]
    return token


def test_invitation_token_is_shown_once_and_stored_hashed(
    signed_in: SignedIn, owner: Account, workspace_id: uuid.UUID, db: Session
) -> None:
    client = signed_in(owner)
    token = _invite(client, "New.Person@Example.com")
    invitation = db.scalars(select(Invitation)).one()
    assert invitation.email == "new.person@example.com"
    assert invitation.token_hash == hashlib.sha256(token.encode()).digest()
    pending = client.get(INVITES).json()
    assert [p["email"] for p in pending] == ["new.person@example.com"]
    assert "token" not in pending[0]


def test_new_person_accepts_and_is_signed_in(
    signed_in: SignedIn,
    make_client: Callable[..., TestClient],
    owner: Account,
    workspace_id: uuid.UUID,
    db: Session,
) -> None:
    token = _invite(signed_in(owner), "new@example.com", "collaborator")
    invitee = make_client()

    preview = invitee.post("/api/v1/invitations/preview", json={"token": token})
    assert preview.status_code == 200
    assert preview.json()["workspace_name"] == "Booski Studios"
    assert preview.json()["account_exists"] is False

    accepted = invitee.post(
        "/api/v1/invitations/accept",
        json={"token": token, "display_name": "New Person", "password": "a fresh long passphrase"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["signed_in"] is True
    assert accepted.json()["workspace"]["role"] == "collaborator"
    assert SESSION_COOKIE in invitee.cookies
    assert invitee.get("/api/v1/w/booski").status_code == 200

    # Single use.
    again = make_client().post(
        "/api/v1/invitations/accept",
        json={"token": token, "display_name": "Someone Else", "password": "another long passphrase"},
    )
    assert again.status_code == 404


def test_new_account_needs_a_name_and_a_valid_password(
    signed_in: SignedIn, make_client: Callable[..., TestClient], owner: Account, workspace_id: uuid.UUID
) -> None:
    token = _invite(signed_in(owner), "kim.smith@example.com")
    invitee = make_client()
    accept = "/api/v1/invitations/accept"
    assert invitee.post(accept, json={"token": token}).status_code == 422
    assert (
        invitee.post(accept, json={"token": token, "display_name": "Kim", "password": "short"}).status_code
        == 422
    )
    contains_email = invitee.post(
        accept, json={"token": token, "display_name": "Kim", "password": "kim.smith rocks forever"}
    )
    assert contains_email.status_code == 422


def test_existing_account_must_sign_in_to_accept(
    signed_in: SignedIn,
    make_client: Callable[..., TestClient],
    owner: Account,
    workspace_id: uuid.UUID,
    db: Session,
) -> None:
    existing = make_user(db, "existing@example.com")
    token = _invite(signed_in(owner), existing.email, "viewer")

    # Knowing the token isn't enough to attach a workspace to someone else's account.
    anonymous = make_client().post("/api/v1/invitations/accept", json={"token": token})
    assert anonymous.status_code == 409

    wrong_person = signed_in(make_user(db, "intruder@example.com"))
    assert wrong_person.post("/api/v1/invitations/accept", json={"token": token}).status_code == 403

    right_person = signed_in(existing)
    accepted = right_person.post("/api/v1/invitations/accept", json={"token": token})
    assert accepted.status_code == 200
    assert accepted.json()["signed_in"] is False
    assert right_person.get("/api/v1/w/booski").json()["role"] == "viewer"


def test_accepting_while_signed_in_requires_the_csrf_token(
    signed_in: SignedIn, owner: Account, workspace_id: uuid.UUID, db: Session
) -> None:
    existing = make_user(db, "existing@example.com")
    token = _invite(signed_in(owner), existing.email)
    client = signed_in(existing)
    client.headers.pop(CSRF_HEADER)
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 403


def test_expired_and_revoked_invitations_are_rejected(
    signed_in: SignedIn,
    make_client: Callable[..., TestClient],
    owner: Account,
    workspace_id: uuid.UUID,
    db: Session,
) -> None:
    owner_client = signed_in(owner)
    expired_token = _invite(owner_client, "late@example.com")
    db.execute(update(Invitation).values(expires_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    revoked_token = _invite(owner_client, "revoked@example.com")
    revoked_id = owner_client.get(INVITES).json()[0]["id"]
    assert owner_client.delete(f"{INVITES}/{revoked_id}").status_code == 204

    body = {"display_name": "X", "password": "a long enough password"}
    for token in (expired_token, revoked_token, "not-a-real-invitation-token-at-all"):
        assert make_client().post("/api/v1/invitations/preview", json={"token": token}).status_code == 404
        assert (
            make_client().post("/api/v1/invitations/accept", json={"token": token, **body}).status_code == 404
        )
    # An expired invitation doesn't block sending a fresh one.
    _invite(owner_client, "late@example.com")


def test_duplicate_and_member_invitations_are_refused(
    signed_in: SignedIn, owner: Account, workspace_id: uuid.UUID, db: Session
) -> None:
    client = signed_in(owner)
    _invite(client, "dup@example.com")
    assert client.post(INVITES, json={"email": "dup@example.com", "role": "viewer"}).status_code == 409
    member = make_user(db, "member@example.com")
    add_member(db, workspace_id, member, Role.VIEWER)
    assert client.post(INVITES, json={"email": "member@example.com", "role": "viewer"}).status_code == 409


def test_invitation_role_limits(
    signed_in: SignedIn, owner: Account, workspace_id: uuid.UUID, db: Session
) -> None:
    admin = make_user(db, "admin@booski.test")
    add_member(db, workspace_id, admin, Role.ADMIN)
    admin_client = signed_in(admin)
    assert admin_client.post(INVITES, json={"email": "a@example.com", "role": "admin"}).status_code == 403
    assert admin_client.post(INVITES, json={"email": "a@example.com", "role": "developer"}).status_code == 201
    assert signed_in(owner).post(INVITES, json={"email": "b@example.com", "role": "owner"}).status_code == 422
    # Admins can't revoke an invitation for a role they couldn't grant.
    _invite(signed_in(owner), "future.admin@example.com", "admin")
    admin_invite = next(i for i in admin_client.get(INVITES).json() if i["role"] == "admin")
    assert admin_client.delete(f"{INVITES}/{admin_invite['id']}").status_code == 403


def test_invitations_from_another_workspace_cannot_be_revoked(
    signed_in: SignedIn, owner: Account, workspace_id: uuid.UUID, db: Session
) -> None:
    rival = make_user(db, "rival@other.test")
    make_workspace(db, rival, "other-studio")
    rival_client = signed_in(rival)
    rival_client.post("/api/v1/w/other-studio/invitations", json={"email": "x@example.com", "role": "viewer"})
    foreign_invitation = rival_client.get("/api/v1/w/other-studio/invitations").json()[0]["id"]
    assert signed_in(owner).delete(f"{INVITES}/{foreign_invitation}").status_code == 404
    assert (
        db.scalar(select(Invitation.revoked_at).where(Invitation.id == uuid.UUID(foreign_invitation))) is None
    )


def test_accepting_records_who_invited_you(
    signed_in: SignedIn,
    make_client: Callable[..., TestClient],
    owner: Account,
    workspace_id: uuid.UUID,
    db: Session,
) -> None:
    token = _invite(signed_in(owner), "new@example.com")
    make_client().post(
        "/api/v1/invitations/accept",
        json={"token": token, "display_name": "New", "password": "a fresh long passphrase"},
    )
    membership = db.scalars(select(Membership).where(Membership.role == "developer")).one()
    assert membership.invited_by_user_id == owner.id
