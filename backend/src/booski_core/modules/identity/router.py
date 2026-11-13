"""``/api/v1/auth``: sign in and out, the current user, sessions and passwords."""

import uuid

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from booski_core.access.roles import Role
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import utcnow
from booski_core.modules.activity.service import record_event
from booski_core.modules.identity import service
from booski_core.modules.identity.dependencies import (
    SESSION_COOKIE,
    AppSettings,
    CurrentAuth,
    DbSession,
    Meta,
    clear_session_cookies,
    set_session_cookies,
)
from booski_core.modules.identity.schemas import (
    LoginRequest,
    LoginResponse,
    MembershipSummary,
    MeResponse,
    PasswordChangeRequest,
    RevokedCount,
    SessionOut,
    UserOut,
)
from booski_core.modules.workspaces.models import Membership, Workspace

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_out(session: object, current_id: uuid.UUID | None) -> SessionOut:
    out = SessionOut.model_validate(session)
    out.current = out.id == current_id
    return out


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest, request: Request, response: Response, db: DbSession, settings: AppSettings, meta: Meta
) -> LoginResponse:
    """Signs in with email and password. Sets the session and CSRF cookies."""
    now = utcnow()
    user = service.authenticate(db, settings, body.email, body.password, meta, now)

    # Never reuse a session across sign-ins (prevents session fixation): retire any session this browser had.
    previous = request.cookies.get(SESSION_COOKIE)
    if previous and (found := service.find_active_session(db, previous, now)) is not None:
        service.revoke_session(found[0], "superseded", now)

    issued = service.start_session(db, settings, user, meta, now)
    record_event(
        db,
        verb="user.signed_in",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        summary="Signed in",
        meta=meta,
    )
    db.commit()
    set_session_cookies(response, issued)
    return LoginResponse(
        user=UserOut.model_validate(user),
        session=_session_out(issued.session, issued.session.id),
        csrf_token=issued.csrf_token,
    )


@router.post("/logout", status_code=204)
def logout(auth: CurrentAuth, response: Response, db: DbSession, meta: Meta) -> None:
    """Signs out this browser. The session can never be used again."""
    service.revoke_session(auth.session, "signed_out", utcnow())
    record_event(
        db,
        verb="user.signed_out",
        entity_type="user",
        entity_id=auth.user.id,
        actor_user_id=auth.user.id,
        summary="Signed out",
        meta=meta,
    )
    db.commit()
    clear_session_cookies(response)


@router.get("/me", response_model=MeResponse)
def me(auth: CurrentAuth, db: DbSession) -> MeResponse:
    """The signed-in user, this session, and the workspaces they belong to."""
    rows = db.execute(
        select(Workspace, Membership)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == auth.user.id, Workspace.archived_at.is_(None))
        .order_by(Workspace.name)
    ).all()
    return MeResponse(
        user=UserOut.model_validate(auth.user),
        session=_session_out(auth.session, auth.session.id),
        workspaces=[
            MembershipSummary(
                workspace_id=w.id, workspace_slug=w.slug, workspace_name=w.name, role=Role(m.role)
            )
            for w, m in rows
        ],
    )


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(auth: CurrentAuth, db: DbSession) -> list[SessionOut]:
    """Every browser currently signed in to your account."""
    return [
        _session_out(s, auth.session.id) for s in service.list_active_sessions(db, auth.user.id, utcnow())
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: uuid.UUID, auth: CurrentAuth, response: Response, db: DbSession, meta: Meta
) -> None:
    """Signs out one of your sessions. Other people's sessions are reported as not found."""
    now = utcnow()
    target = next(
        (s for s in service.list_active_sessions(db, auth.user.id, now) if s.id == session_id), None
    )
    if target is None:
        raise ProblemError(404, "Session not found.")
    service.revoke_session(target, "revoked_by_user", now)
    record_event(
        db,
        verb="session.revoked",
        entity_type="session",
        entity_id=target.id,
        actor_user_id=auth.user.id,
        summary="Signed out a session",
        meta=meta,
    )
    db.commit()
    if target.id == auth.session.id:
        clear_session_cookies(response)


@router.post("/sessions/revoke-others", response_model=RevokedCount)
def revoke_other_sessions(auth: CurrentAuth, db: DbSession, meta: Meta) -> RevokedCount:
    """Signs out every session except this one."""
    count = service.revoke_user_sessions(db, auth.user.id, "revoked_by_user", utcnow(), keep=auth.session.id)
    record_event(
        db,
        verb="session.revoked_others",
        entity_type="user",
        entity_id=auth.user.id,
        actor_user_id=auth.user.id,
        summary=f"Signed out {count} other session(s)",
        meta=meta,
        changes={"revoked": count},
    )
    db.commit()
    return RevokedCount(revoked=count)


@router.post("/password", response_model=RevokedCount)
def change_password(
    body: PasswordChangeRequest, auth: CurrentAuth, db: DbSession, settings: AppSettings, meta: Meta
) -> RevokedCount:
    """Changes your password and signs out your other sessions."""
    count = service.change_password(
        db, settings, auth.user, body.current_password, body.new_password, auth.session.id, meta, utcnow()
    )
    record_event(
        db,
        verb="user.password_changed",
        entity_type="user",
        entity_id=auth.user.id,
        actor_user_id=auth.user.id,
        summary="Changed password",
        meta=meta,
        changes={"sessions_revoked": count},
    )
    db.commit()
    return RevokedCount(revoked=count)
