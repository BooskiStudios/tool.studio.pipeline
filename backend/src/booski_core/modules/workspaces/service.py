"""Workspace, membership and invitation rules. Every function that changes data records an activity event."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.roles import Capability, Role, can_manage, has_capability
from booski_core.config import Settings
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta
from booski_core.modules.activity.service import record_event
from booski_core.modules.identity.models import User
from booski_core.modules.identity.service import get_user_by_email, set_password
from booski_core.modules.workspaces.models import Invitation, Membership, Workspace
from booski_core.security.tokens import hash_token, new_token

MEMBER_NOT_FOUND = "Member not found."
INVITATION_NOT_FOUND = "This invitation is invalid, has expired or has already been used."


# ---------------------------------------------------------------- workspaces


def list_user_workspaces(db: Session, user_id: uuid.UUID) -> list[tuple[Workspace, Membership]]:
    rows = db.execute(
        select(Workspace, Membership)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user_id, Workspace.archived_at.is_(None))
        .order_by(Workspace.name)
    ).all()
    return [(w, m) for w, m in rows]


def create_workspace(
    db: Session, owner: User, name: str, slug: str, meta: RequestMeta, *, actor_user_id: uuid.UUID | None
) -> tuple[Workspace, Membership]:
    """Creates a workspace with ``owner`` as its owner. ``actor_user_id`` is None when the CLI does it."""
    workspace = Workspace(name=name, slug=slug, created_by_user_id=owner.id)
    try:
        with db.begin_nested():
            db.add(workspace)
            db.flush()
    except IntegrityError:
        raise ProblemError(409, "That workspace address is already taken. Choose another.") from None
    membership = Membership(workspace_id=workspace.id, user_id=owner.id, role=Role.OWNER.value)
    db.add(membership)
    db.flush()
    record_event(
        db,
        verb="workspace.created",
        entity_type="workspace",
        entity_id=workspace.id,
        workspace_id=workspace.id,
        actor_user_id=actor_user_id,
        summary=f"Created workspace {name}",
        meta=meta,
        changes={"slug": slug, "owner_user_id": str(owner.id)},
    )
    return workspace, membership


def rename_workspace(db: Session, ctx: WorkspaceContext, name: str, meta: RequestMeta) -> None:
    previous = ctx.workspace.name
    if previous == name:
        return
    ctx.workspace.name = name
    record_event(
        db,
        verb="workspace.renamed",
        entity_type="workspace",
        entity_id=ctx.workspace.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary=f"Renamed workspace to {name}",
        meta=meta,
        changes={"name": {"from": previous, "to": name}},
    )


# ---------------------------------------------------------------- members


def list_members(db: Session, workspace_id: uuid.UUID) -> list[tuple[Membership, User]]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
        .order_by(User.display_name)
    ).all()
    return [(m, u) for m, u in rows]


def _get_member(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
    membership = db.scalars(
        select(Membership)
        .where(Membership.workspace_id == workspace_id, Membership.user_id == user_id)
        .with_for_update()
    ).one_or_none()
    if membership is None:
        raise ProblemError(404, MEMBER_NOT_FOUND)
    return membership


def change_role(
    db: Session, ctx: WorkspaceContext, target_user_id: uuid.UUID, new_role: Role, meta: RequestMeta
) -> Membership:
    if target_user_id == ctx.auth.user.id:
        raise ProblemError(403, "You can't change your own role.")
    membership = _get_member(db, ctx.workspace.id, target_user_id)
    current = Role(membership.role)
    if current is Role.OWNER:
        raise ProblemError(409, "The owner's role can only change by transferring ownership.")
    if not can_manage(ctx.role, current) or not can_manage(ctx.role, new_role):
        raise ProblemError(403, "Your role can't assign or change that role.")
    if current is new_role:
        return membership
    membership.role = new_role.value
    record_event(
        db,
        verb="membership.role_changed",
        entity_type="membership",
        entity_id=membership.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary=f"Changed a member's role from {current} to {new_role}",
        meta=meta,
        changes={"user_id": str(target_user_id), "role": {"from": current.value, "to": new_role.value}},
    )
    return membership


def remove_member(db: Session, ctx: WorkspaceContext, target_user_id: uuid.UUID, meta: RequestMeta) -> None:
    """Removes a member, or lets any member leave (except the owner, who must transfer ownership first)."""
    leaving = target_user_id == ctx.auth.user.id
    membership = _get_member(db, ctx.workspace.id, target_user_id)
    role = Role(membership.role)
    if leaving:
        if role is Role.OWNER:
            raise ProblemError(409, "Transfer ownership to another member before leaving the workspace.")
    elif not has_capability(ctx.role, Capability.MEMBERS_MANAGE) or not can_manage(ctx.role, role):
        raise ProblemError(403, "Your role can't remove this member.")
    db.delete(membership)
    record_event(
        db,
        verb="membership.left" if leaving else "membership.removed",
        entity_type="membership",
        entity_id=membership.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary="Left the workspace" if leaving else f"Removed a {role} from the workspace",
        meta=meta,
        changes={"user_id": str(target_user_id), "role": role.value},
    )


def transfer_ownership(
    db: Session, ctx: WorkspaceContext, target_user_id: uuid.UUID, meta: RequestMeta
) -> None:
    """The target becomes owner; the current owner becomes an admin."""
    if target_user_id == ctx.auth.user.id:
        raise ProblemError(409, "You already own this workspace.")
    own = _get_member(db, ctx.workspace.id, ctx.auth.user.id)
    target = _get_member(db, ctx.workspace.id, target_user_id)
    previous_target_role = target.role
    own.role = Role.ADMIN.value
    db.flush()  # the one-owner index requires demoting before promoting
    target.role = Role.OWNER.value
    db.flush()
    record_event(
        db,
        verb="workspace.ownership_transferred",
        entity_type="workspace",
        entity_id=ctx.workspace.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary="Transferred ownership",
        meta=meta,
        changes={
            "from_user_id": str(ctx.auth.user.id),
            "to_user_id": str(target_user_id),
            "to_previous_role": previous_target_role,
        },
    )


# ---------------------------------------------------------------- invitations


def _pending(now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None), Invitation.expires_at > now)


def list_pending_invitations(db: Session, workspace_id: uuid.UUID, now: datetime) -> list[Invitation]:
    return list(
        db.scalars(
            select(Invitation)
            .where(Invitation.workspace_id == workspace_id, *_pending(now))
            .order_by(Invitation.created_at.desc())
        )
    )


def create_invitation(
    db: Session,
    settings: Settings,
    ctx: WorkspaceContext,
    email: str,
    role: Role,
    meta: RequestMeta,
    now: datetime,
) -> tuple[Invitation, str]:
    if not can_manage(ctx.role, role):
        raise ProblemError(403, "Your role can't invite people with that role.")
    already_member = db.scalar(
        select(
            exists()
            .where(Membership.workspace_id == ctx.workspace.id, Membership.user_id == User.id)
            .where(User.email == email)
        )
    )
    if already_member:
        raise ProblemError(409, "That person is already a member of this workspace.")

    # Expired invitations still occupy the "one pending per email" slot until they are retired.
    db.execute(
        update(Invitation)
        .where(
            Invitation.workspace_id == ctx.workspace.id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at <= now,
        )
        .values(revoked_at=now)
    )
    token = new_token()
    invitation = Invitation(
        workspace_id=ctx.workspace.id,
        email=email,
        role=role.value,
        token_hash=hash_token(token),
        invited_by_user_id=ctx.auth.user.id,
        expires_at=now + settings.invitation_ttl,
    )
    try:
        with db.begin_nested():
            db.add(invitation)
            db.flush()
    except IntegrityError:
        raise ProblemError(
            409, "There's already a pending invitation for this email. Revoke it to send a new one."
        ) from None
    record_event(
        db,
        verb="invitation.created",
        entity_type="invitation",
        entity_id=invitation.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary=f"Invited {email} as {role}",
        meta=meta,
        changes={"email": email, "role": role.value},
    )
    return invitation, token


def revoke_invitation(
    db: Session, ctx: WorkspaceContext, invitation_id: uuid.UUID, meta: RequestMeta, now: datetime
) -> None:
    invitation = db.scalars(
        select(Invitation)
        .where(Invitation.id == invitation_id, Invitation.workspace_id == ctx.workspace.id, *_pending(now))
        .with_for_update()
    ).one_or_none()
    if invitation is None:
        raise ProblemError(404, "Invitation not found.")
    if not can_manage(ctx.role, Role(invitation.role)):
        raise ProblemError(403, "Your role can't revoke this invitation.")
    invitation.revoked_at = now
    record_event(
        db,
        verb="invitation.revoked",
        entity_type="invitation",
        entity_id=invitation.id,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.auth.user.id,
        summary=f"Revoked the invitation for {invitation.email}",
        meta=meta,
    )


def find_valid_invitation(
    db: Session, token: str, now: datetime, *, lock: bool = False
) -> tuple[Invitation, Workspace]:
    query = (
        select(Invitation, Workspace)
        .join(Workspace, Workspace.id == Invitation.workspace_id)
        .where(Invitation.token_hash == hash_token(token), Workspace.archived_at.is_(None), *_pending(now))
    )
    if lock:
        query = query.with_for_update(of=Invitation)
    row = db.execute(query).one_or_none()
    if row is None:
        raise ProblemError(404, INVITATION_NOT_FOUND)
    return row[0], row[1]


@dataclass(frozen=True)
class AcceptedInvitation:
    workspace: Workspace
    membership: Membership
    user: User
    new_account: bool


def accept_invitation(
    db: Session,
    token: str,
    signed_in_user: User | None,
    display_name: str | None,
    password: str | None,
    meta: RequestMeta,
    now: datetime,
) -> AcceptedInvitation:
    """Joins the workspace. Creates the account first if none exists for the invited email.

    If an account exists, the invitee must be signed in as that account: knowing the token is not enough
    to attach a workspace to someone else's account.
    """
    invitation, workspace = find_valid_invitation(db, token, now, lock=True)
    existing = get_user_by_email(db, invitation.email)

    if signed_in_user is not None and signed_in_user.email != invitation.email:
        raise ProblemError(
            403, "This invitation is for a different email address. Sign out and open it again."
        )

    new_account = False
    if existing is not None:
        if signed_in_user is None:
            raise ProblemError(
                409, "An account already exists for this email. Sign in, then accept the invitation."
            )
        user = existing
    else:
        if not display_name or not password:
            raise ProblemError(422, "Choose a display name and a password to create your account.")
        user = User(email=invitation.email, display_name=display_name)
        set_password(user, password, now)  # also applies the password rules
        db.add(user)
        db.flush()
        new_account = True
        record_event(
            db,
            verb="user.created",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            summary="Created an account from an invitation",
            meta=meta,
        )

    membership = db.scalars(
        select(Membership).where(Membership.workspace_id == workspace.id, Membership.user_id == user.id)
    ).one_or_none()
    if membership is None:
        membership = Membership(
            workspace_id=workspace.id,
            user_id=user.id,
            role=invitation.role,
            invited_by_user_id=invitation.invited_by_user_id,
        )
        db.add(membership)
        db.flush()
    invitation.accepted_at = now
    invitation.accepted_by_user_id = user.id
    record_event(
        db,
        verb="invitation.accepted",
        entity_type="invitation",
        entity_id=invitation.id,
        workspace_id=workspace.id,
        actor_user_id=user.id,
        summary=f"Joined as {membership.role}",
        meta=meta,
        changes={"role": membership.role},
    )
    return AcceptedInvitation(workspace=workspace, membership=membership, user=user, new_account=new_account)
