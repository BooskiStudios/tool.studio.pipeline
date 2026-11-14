"""Signing in and out, cookies, CSRF, rate limiting and safe failures."""

import hashlib
import logging
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.core.errors import PROBLEM_JSON
from booski_core.modules.activity.models import ActivityEvent
from booski_core.modules.identity.dependencies import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from booski_core.modules.identity.models import LoginAttempt, User, UserSession
from helpers import DEFAULT_PASSWORD, Account, make_user, sign_in

pytestmark = pytest.mark.db

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _set_cookies(response_headers: list[tuple[str, str]]) -> dict[str, str]:
    return {v.split("=", 1)[0]: v for k, v in response_headers if k.lower() == "set-cookie"}


# ---------------------------------------------------------------- successful sign-in


def test_sign_in_sets_secure_cookies_and_returns_csrf_token(client: TestClient, db: Session) -> None:
    account = make_user(db, "ada@example.com")
    response = client.post(LOGIN, json={"email": account.email, "password": account.password})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["session"]["current"] is True

    cookies = _set_cookies(response.headers.multi_items())
    session_cookie = cookies[SESSION_COOKIE].lower()
    for attribute in ("httponly", "secure", "samesite=lax", "path=/", "max-age="):
        assert attribute in session_cookie
    csrf_cookie = cookies[CSRF_COOKIE].lower()
    assert "secure" in csrf_cookie and "httponly" not in csrf_cookie
    assert client.cookies[CSRF_COOKIE] == body["csrf_token"]


def test_session_persists_across_requests_and_new_clients(
    make_client: Callable[..., TestClient], db: Session
) -> None:
    account = make_user(db, "ada@example.com")
    first = sign_in(make_client(), account)
    assert first.get(ME).json()["user"]["email"] == account.email

    # A browser restart: a new client presenting the same persistent cookie is still signed in.
    restarted = make_client()
    restarted.cookies.set(SESSION_COOKIE, first.cookies[SESSION_COOKIE])
    assert restarted.get(ME).status_code == 200


def test_email_is_case_insensitive(client: TestClient, db: Session) -> None:
    make_user(db, "ada@example.com")
    response = client.post(LOGIN, json={"email": "  ADA@Example.COM ", "password": DEFAULT_PASSWORD})
    assert response.status_code == 200


def test_only_hashes_are_stored(client: TestClient, db: Session) -> None:
    account = make_user(db, "ada@example.com")
    sign_in(client, account)
    user = db.scalars(select(User)).one()
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")
    assert account.password not in user.password_hash

    session = db.scalars(select(UserSession)).one()
    raw_token = client.cookies[SESSION_COOKIE]
    assert session.token_hash == hashlib.sha256(raw_token.encode()).digest()
    assert raw_token.encode() not in session.token_hash
    assert session.csrf_token_hash == hashlib.sha256(client.headers[CSRF_HEADER].encode()).digest()


def test_sign_in_is_recorded_in_the_activity_log(client: TestClient, db: Session) -> None:
    account = make_user(db, "ada@example.com")
    sign_in(client, account)
    event = db.scalars(select(ActivityEvent).where(ActivityEvent.verb == "user.signed_in")).one()
    assert event.actor_user_id == account.id
    assert event.request_id


# ---------------------------------------------------------------- failed sign-in


def _failed_body(response_json: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in response_json.items() if k != "request_id"}


def test_wrong_password_unknown_email_and_inactive_account_fail_identically(
    client: TestClient, db: Session
) -> None:
    make_user(db, "ada@example.com")
    make_user(db, "gone@example.com", active=False)
    wrong_password = client.post(LOGIN, json={"email": "ada@example.com", "password": "not the password"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD})
    inactive = client.post(LOGIN, json={"email": "gone@example.com", "password": DEFAULT_PASSWORD})

    for response in (wrong_password, unknown_email, inactive):
        assert response.status_code == 401
        assert response.headers["content-type"] == PROBLEM_JSON
        assert SESSION_COOKIE not in response.cookies
    assert (
        _failed_body(wrong_password.json())
        == _failed_body(unknown_email.json())
        == _failed_body(inactive.json())
    )
    assert wrong_password.json()["detail"] == "Email or password is incorrect."


def test_failed_sign_in_never_logs_email_or_password(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    make_user(db, "ada@example.com")
    with caplog.at_level(logging.DEBUG):
        client.post(LOGIN, json={"email": "ada@example.com", "password": "Secret-Guess-123"})
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "Sign-in failed" in logged
    assert "ada@example.com" not in logged
    assert "Secret-Guess-123" not in logged


def test_failed_attempts_are_counted(client: TestClient, db: Session) -> None:
    make_user(db, "ada@example.com")
    client.post(LOGIN, json={"email": "ada@example.com", "password": "wrong"})
    attempt = db.scalars(select(LoginAttempt)).one()
    assert attempt.email == "ada@example.com" and attempt.succeeded is False
    assert str(attempt.ip) == "198.51.100.10"


def test_account_is_throttled_after_five_failures_even_with_the_right_password(
    make_client: Callable[..., TestClient], db: Session
) -> None:
    account = make_user(db, "ada@example.com")
    for i in range(5):
        response = make_client(ip=f"203.0.113.{i + 1}").post(
            LOGIN, json={"email": account.email, "password": "wrong"}
        )
        assert response.status_code == 401
    blocked = make_client(ip="203.0.113.99").post(
        LOGIN, json={"email": account.email, "password": account.password}
    )
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == str(15 * 60)


def test_address_is_throttled_after_twenty_failures(
    make_client: Callable[..., TestClient], db: Session
) -> None:
    account = make_user(db, "ada@example.com")
    attacker = make_client(ip="203.0.113.50")
    for i in range(20):
        attacker.post(LOGIN, json={"email": f"guess{i}@example.com", "password": "wrong"})
    assert (
        attacker.post(LOGIN, json={"email": account.email, "password": account.password}).status_code == 429
    )
    # Someone else, from another address, is unaffected.
    assert (
        make_client(ip="198.51.100.77")
        .post(LOGIN, json={"email": account.email, "password": account.password})
        .status_code
        == 200
    )


def test_oversized_password_is_rejected_before_hashing(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": "ada@example.com", "password": "x" * 2000})
    assert response.status_code == 422
    assert "x" * 50 not in response.text


# ---------------------------------------------------------------- unauthenticated access


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/auth/sessions"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/password"),
        ("POST", "/api/v1/auth/sessions/revoke-others"),
        ("GET", "/api/v1/workspaces"),
        ("POST", "/api/v1/workspaces"),
        ("GET", "/api/v1/w/anything"),
        ("GET", "/api/v1/w/anything/members"),
    ],
)
def test_protected_endpoints_require_sign_in(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to continue."


def test_garbage_session_cookie_is_treated_as_signed_out(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "not-a-real-session-token")
    assert client.get(ME).status_code == 401


# ---------------------------------------------------------------- CSRF and origin checks


def test_signed_in_writes_require_the_csrf_token(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    token = client.headers.pop(CSRF_HEADER)

    assert client.post("/api/v1/workspaces", json={"name": "A", "slug": "aaa"}).status_code == 403
    client.headers[CSRF_HEADER] = "wrong-token-value"
    assert client.post("/api/v1/workspaces", json={"name": "A", "slug": "aaa"}).status_code == 403
    client.headers[CSRF_HEADER] = token
    assert client.post("/api/v1/workspaces", json={"name": "A", "slug": "aaa"}).status_code == 201


def test_reads_do_not_need_the_csrf_token(signed_in: Callable[[Account], TestClient], db: Session) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    client.headers.pop(CSRF_HEADER)
    assert client.get(ME).status_code == 200


def test_cross_site_requests_are_blocked(client: TestClient, db: Session) -> None:
    account = make_user(db, "ada@example.com")
    body = {"email": account.email, "password": account.password}
    blocked = client.post(LOGIN, json=body, headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 403
    assert client.post(LOGIN, json=body, headers={"Origin": "http://localhost:5173"}).status_code == 200


# ---------------------------------------------------------------- sign-out


def test_sign_out_revokes_the_session_for_good(
    signed_in: Callable[[Account], TestClient], db: Session
) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    stolen_cookie = client.cookies[SESSION_COOKIE]

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert "max-age=0" in _set_cookies(response.headers.multi_items())[SESSION_COOKIE].lower()

    client.cookies.set(SESSION_COOKIE, stolen_cookie)  # replaying the old cookie must not work
    assert client.get(ME).status_code == 401
    session = db.scalars(select(UserSession)).one()
    assert session.revoked_reason == "signed_out"


def test_signing_in_again_retires_the_previous_session(client: TestClient, db: Session) -> None:
    account = make_user(db, "ada@example.com")
    sign_in(client, account)
    first_cookie = client.cookies[SESSION_COOKIE]
    sign_in(client, account)
    assert client.cookies[SESSION_COOKIE] != first_cookie
    reasons = sorted(str(s.revoked_reason) for s in db.scalars(select(UserSession)))
    assert reasons == ["None", "superseded"]
