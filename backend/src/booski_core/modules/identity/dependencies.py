"""Request dependencies: the database session, settings, the signed-in user and cookie handling.

Every signed-in request that changes something (POST, PATCH, PUT, DELETE) must carry the session's CSRF
token in the ``X-CSRF-Token`` header. That check lives here, so no endpoint can forget it.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from booski_core.config import Settings
from booski_core.core.errors import ProblemError
from booski_core.core.origin import SAFE_METHODS
from booski_core.core.request_meta import RequestMeta, get_request_meta, utcnow
from booski_core.db import get_session
from booski_core.modules.identity.models import User, UserSession
from booski_core.modules.identity.service import IssuedSession, find_active_session, touch_session
from booski_core.security.tokens import token_matches

# "__Host-" cookies must be Secure, have Path=/ and no Domain: browsers then refuse to let any other
# site or subdomain set or overwrite them.
SESSION_COOKIE = "__Host-booski_session"
CSRF_COOKIE = "__Host-booski_csrf"
CSRF_HEADER = "X-CSRF-Token"


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
Meta = Annotated[RequestMeta, Depends(get_request_meta)]


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: UserSession


def get_optional_auth(request: Request, db: DbSession, settings: AppSettings) -> AuthContext | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    now = utcnow()
    found = find_active_session(db, token, now)
    if found is None:
        return None  # expired, revoked or unknown: treated exactly like no cookie
    session, user = found

    if request.method not in SAFE_METHODS:
        submitted = request.headers.get(CSRF_HEADER, "")
        if not submitted or not token_matches(submitted, session.csrf_token_hash):
            raise ProblemError(403, "Missing or invalid CSRF token. Reload the page and try again.")

    if touch_session(session, settings, now):
        db.commit()
    return AuthContext(user=user, session=session)


def require_auth(auth: Annotated[AuthContext | None, Depends(get_optional_auth)]) -> AuthContext:
    if auth is None:
        raise ProblemError(401, "Sign in to continue.")
    return auth


OptionalAuth = Annotated[AuthContext | None, Depends(get_optional_auth)]
CurrentAuth = Annotated[AuthContext, Depends(require_auth)]


def set_session_cookies(response: Response, issued: IssuedSession) -> None:
    max_age = int((issued.session.absolute_expires_at - utcnow()).total_seconds())
    response.set_cookie(
        SESSION_COOKIE, issued.token, max_age=max_age, path="/", secure=True, httponly=True, samesite="lax"
    )
    # Readable by the page's JavaScript (that's the point): it proves the request came from our own page.
    response.set_cookie(
        CSRF_COOKIE, issued.csrf_token, max_age=max_age, path="/", secure=True, httponly=False, samesite="lax"
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=True, httponly=False, samesite="lax")
