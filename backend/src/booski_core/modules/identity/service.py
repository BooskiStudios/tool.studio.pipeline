"""Sign-in, sessions and passwords. Routers and the CLI call these; they never touch tokens directly."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from booski_core.config import Settings
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import IpAddress, RequestMeta
from booski_core.modules.identity.models import LoginAttempt, User, UserSession
from booski_core.security.passwords import (
    burn_verification_time,
    hash_password,
    needs_rehash,
    verify_password,
)
from booski_core.security.tokens import hash_token, new_token

logger = logging.getLogger("booski_core.auth")

ATTEMPT_RETENTION = timedelta(hours=24)
SIGN_IN_FAILED = "Email or password is incorrect."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == normalize_email(email))).one_or_none()


# ---------------------------------------------------------------- password rules


def check_password_rules(password: str, email: str) -> None:
    """Rules beyond length (which request validation enforces)."""
    local_part = email.split("@", 1)[0]
    if len(local_part) >= 4 and local_part.lower() in password.lower():
        raise ProblemError(422, "Choose a password that doesn't contain your email address.")


def set_password(user: User, new_password: str, now: datetime) -> None:
    check_password_rules(new_password, user.email)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now


# ---------------------------------------------------------------- rate limiting


def _recent_failures(
    db: Session, *, since: datetime, email: str | None = None, ip: IpAddress | None = None
) -> int:
    query = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.succeeded.is_(False), LoginAttempt.created_at > since)
    )
    query = (
        query.where(LoginAttempt.email == email) if email is not None else query.where(LoginAttempt.ip == ip)
    )
    return int(db.scalar(query) or 0)


def enforce_sign_in_limits(
    db: Session, settings: Settings, email: str, meta: RequestMeta, now: datetime
) -> None:
    since = now - settings.login_window
    too_many = _recent_failures(db, since=since, email=email) >= settings.login_max_failures_per_email or (
        meta.ip is not None
        and _recent_failures(db, since=since, ip=meta.ip) >= settings.login_max_failures_per_ip
    )
    if too_many:
        minutes = settings.login_window_minutes
        raise ProblemError(
            429,
            f"Too many failed sign-in attempts. Wait {minutes} minutes and try again.",
            headers={"Retry-After": str(minutes * 60)},
        )


def record_sign_in_attempt(
    db: Session, email: str, meta: RequestMeta, succeeded: bool, now: datetime
) -> None:
    db.add(LoginAttempt(email=email, ip=meta.ip, succeeded=succeeded))
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < now - ATTEMPT_RETENTION))


def authenticate(
    db: Session, settings: Settings, email: str, password: str, meta: RequestMeta, now: datetime
) -> User:
    """Returns the user if the email and password are right. Failures are counted and committed."""
    email = normalize_email(email)
    enforce_sign_in_limits(db, settings, email, meta, now)

    user = get_user_by_email(db, email)
    if user is not None and user.password_hash:
        valid = verify_password(user.password_hash, password) and user.is_active
    else:
        burn_verification_time(password)  # same timing whether or not the account exists
        valid = False

    record_sign_in_attempt(db, email, meta, valid, now)
    if not valid or user is None:
        db.commit()  # the failure must count even though the request fails
        logger.info("Sign-in failed (request_id=%s)", meta.request_id)  # never log the email or password
        raise ProblemError(401, SIGN_IN_FAILED)

    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


# ---------------------------------------------------------------- sessions


@dataclass(frozen=True)
class IssuedSession:
    session: UserSession
    token: str  # goes in the HttpOnly cookie; never stored
    csrf_token: str  # returned to the browser; never stored


def start_session(
    db: Session, settings: Settings, user: User, meta: RequestMeta, now: datetime
) -> IssuedSession:
    token, csrf_token = new_token(), new_token()
    absolute = now + settings.session_absolute
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token_hash=hash_token(csrf_token),
        last_seen_at=now,
        idle_expires_at=min(now + settings.session_idle, absolute),
        absolute_expires_at=absolute,
        ip=meta.ip,
        user_agent=meta.user_agent,
    )
    db.add(session)
    user.last_login_at = now
    db.flush()
    return IssuedSession(session=session, token=token, csrf_token=csrf_token)


def find_active_session(db: Session, token: str, now: datetime) -> tuple[UserSession, User] | None:
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.idle_expires_at > now,
            UserSession.absolute_expires_at > now,
            User.is_active.is_(True),
        )
    ).one_or_none()
    return (row[0], row[1]) if row else None


def touch_session(session: UserSession, settings: Settings, now: datetime) -> bool:
    """Extends the idle timeout at most once per ``session_touch`` (fewer writes). True if changed."""
    if now - session.last_seen_at < settings.session_touch:
        return False
    session.last_seen_at = now
    session.idle_expires_at = min(now + settings.session_idle, session.absolute_expires_at)
    return True


def revoke_session(session: UserSession, reason: str, now: datetime) -> None:
    if session.revoked_at is None:
        session.revoked_at = now
        session.revoked_reason = reason


def revoke_user_sessions(
    db: Session, user_id: uuid.UUID, reason: str, now: datetime, *, keep: uuid.UUID | None = None
) -> int:
    query = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now, revoked_reason=reason)
        .returning(UserSession.id)
    )
    if keep is not None:
        query = query.where(UserSession.id != keep)
    return len(db.execute(query).all())


def list_active_sessions(db: Session, user_id: uuid.UUID, now: datetime) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.idle_expires_at > now,
                UserSession.absolute_expires_at > now,
            )
            .order_by(UserSession.last_seen_at.desc())
        )
    )


def change_password(
    db: Session,
    settings: Settings,
    user: User,
    current_password: str,
    new_password: str,
    keep_session: uuid.UUID,
    meta: RequestMeta,
    now: datetime,
) -> int:
    """Checks the current password (rate-limited like sign-in), sets the new one, signs out other sessions."""
    enforce_sign_in_limits(db, settings, user.email, meta, now)
    if not user.password_hash or not verify_password(user.password_hash, current_password):
        record_sign_in_attempt(db, user.email, meta, False, now)
        db.commit()
        raise ProblemError(403, "Your current password is incorrect.")
    set_password(user, new_password, now)
    return revoke_user_sessions(db, user.id, "password_changed", now, keep=keep_session)
