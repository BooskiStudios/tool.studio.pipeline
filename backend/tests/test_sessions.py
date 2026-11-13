"""Session lifetime, listing and revocation, password changes and deactivation."""

from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from booski_core import provisioning
from booski_core.core.request_meta import utcnow
from booski_core.modules.identity.models import UserSession
from helpers import Account, make_user, sign_in

pytestmark = pytest.mark.db

ME = "/api/v1/auth/me"
SESSIONS = "/api/v1/auth/sessions"


def _only_session(db: Session) -> UserSession:
    db.expire_all()
    return db.scalars(select(UserSession)).one()


def test_idle_session_expires(signed_in: Callable[[Account], TestClient], db: Session) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    db.execute(update(UserSession).values(idle_expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    assert client.get(ME).status_code == 401


def test_session_expires_at_its_absolute_limit_even_if_active(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    past = utcnow() - timedelta(seconds=1)
    db.execute(update(UserSession).values(idle_expires_at=past, absolute_expires_at=past))
    db.commit()
    assert client.get(ME).status_code == 401


def test_activity_extends_the_idle_timeout_but_never_past_the_absolute_limit(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    session = _only_session(db)
    stale = utcnow() - timedelta(minutes=10)
    db.execute(
        update(UserSession).values(last_seen_at=stale, idle_expires_at=utcnow() + timedelta(minutes=1))
    )
    db.commit()

    assert client.get(ME).status_code == 200
    refreshed = _only_session(db)
    assert refreshed.last_seen_at > stale
    assert refreshed.idle_expires_at > utcnow() + timedelta(hours=11)
    assert refreshed.idle_expires_at <= session.absolute_expires_at


def test_lists_only_your_own_active_sessions(make_client: Callable[..., TestClient], db: Session) -> None:
    ada = make_user(db, "ada@example.com")
    laptop = sign_in(make_client(), ada)
    sign_in(make_client(ip="198.51.100.20"), ada)
    sign_in(make_client(), make_user(db, "bob@example.com"))

    sessions = laptop.get(SESSIONS).json()
    assert len(sessions) == 2
    assert [s["current"] for s in sessions].count(True) == 1
    assert {s["ip"] for s in sessions} == {"198.51.100.10", "198.51.100.20"}


def test_revoke_another_of_your_sessions(make_client: Callable[..., TestClient], db: Session) -> None:
    ada = make_user(db, "ada@example.com")
    laptop = sign_in(make_client(), ada)
    phone = sign_in(make_client(), ada)
    phone_session = next(s for s in phone.get(SESSIONS).json() if s["current"])

    assert laptop.delete(f"{SESSIONS}/{phone_session['id']}").status_code == 204
    assert phone.get(ME).status_code == 401
    assert laptop.get(ME).status_code == 200


def test_cannot_revoke_someone_elses_session(make_client: Callable[..., TestClient], db: Session) -> None:
    ada = sign_in(make_client(), make_user(db, "ada@example.com"))
    bob = sign_in(make_client(), make_user(db, "bob@example.com"))
    bobs_session = bob.get(SESSIONS).json()[0]["id"]

    assert ada.delete(f"{SESSIONS}/{bobs_session}").status_code == 404
    assert bob.get(ME).status_code == 200


def test_revoke_all_other_sessions(make_client: Callable[..., TestClient], db: Session) -> None:
    ada = make_user(db, "ada@example.com")
    keep = sign_in(make_client(), ada)
    others = [sign_in(make_client(), ada) for _ in range(2)]

    response = keep.post(f"{SESSIONS}/revoke-others")
    assert response.json() == {"revoked": 2}
    assert keep.get(ME).status_code == 200
    assert all(other.get(ME).status_code == 401 for other in others)


def test_password_change_requires_the_current_password(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    response = client.post(
        "/api/v1/auth/password", json={"current_password": "wrong", "new_password": "a brand new passphrase"}
    )
    assert response.status_code == 403


def test_password_change_enforces_the_password_rules(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    account = make_user(db, "ada.lovelace@example.com")
    client = signed_in(account)
    too_short = client.post(
        "/api/v1/auth/password", json={"current_password": account.password, "new_password": "short"}
    )
    contains_email = client.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": "my ada.lovelace password"},
    )
    assert too_short.status_code == 422
    assert contains_email.status_code == 422


def test_password_change_signs_out_other_sessions_and_replaces_the_password(
    make_client: Callable[..., TestClient], db: Session
) -> None:
    account = make_user(db, "ada@example.com")
    current = sign_in(make_client(), account)
    other = sign_in(make_client(), account)
    new_password = "a brand new passphrase"

    response = current.post(
        "/api/v1/auth/password", json={"current_password": account.password, "new_password": new_password}
    )
    assert response.json() == {"revoked": 1}
    assert current.get(ME).status_code == 200
    assert other.get(ME).status_code == 401

    login = "/api/v1/auth/login"
    assert (
        make_client().post(login, json={"email": account.email, "password": account.password}).status_code
        == 401
    )
    assert (
        make_client().post(login, json={"email": account.email, "password": new_password}).status_code == 200
    )


def test_deactivation_ends_sessions_and_blocks_sign_in(
    signed_in: Callable[[Account], TestClient], make_client: Callable[..., TestClient], db: Session
) -> None:
    account = make_user(db, "ada@example.com")
    client = signed_in(account)
    assert provisioning.set_active(db, email=account.email, active=False) == 1
    assert client.get(ME).status_code == 401
    login = make_client().post(
        "/api/v1/auth/login", json={"email": account.email, "password": account.password}
    )
    assert login.status_code == 401

    provisioning.set_active(db, email=account.email, active=True)
    assert sign_in(make_client(), account).get(ME).status_code == 200
