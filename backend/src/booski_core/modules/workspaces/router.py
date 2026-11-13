"""Workspace routes.

* ``/api/v1/workspaces``: your workspaces; create one.
* ``/api/v1/w/{workspace_slug}/…``: one workspace, its members and invitations (members only).
* ``/api/v1/invitations/…``: preview and accept an invitation (works before you have an account).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from booski_core.access.dependencies import MemberContext, WorkspaceContext, require
from booski_core.access.roles import Capability, Role
from booski_core.core.request_meta import utcnow
from booski_core.modules.identity import service as identity_service
from booski_core.modules.identity.dependencies import (
    AppSettings,
    CurrentAuth,
    DbSession,
    Meta,
    OptionalAuth,
    set_session_cookies,
)
from booski_core.modules.identity.models import User
from booski_core.modules.identity.schemas import UserOut
from booski_core.modules.workspaces import service
from booski_core.modules.workspaces.models import Membership, Workspace
from booski_core.modules.workspaces.schemas import (
    InvitationAccept,
    InvitationAccepted,
    InvitationCreate,
    InvitationCreated,
    InvitationOut,
    InvitationPreview,
    InvitationTokenBody,
    MemberOut,
    OwnershipTransfer,
    RoleChange,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)

CanUpdateWorkspace = Annotated[WorkspaceContext, Depends(require(Capability.WORKSPACE_UPDATE))]
CanReadMembers = Annotated[WorkspaceContext, Depends(require(Capability.MEMBERS_READ))]
CanManageMembers = Annotated[WorkspaceContext, Depends(require(Capability.MEMBERS_MANAGE))]
CanManageInvitations = Annotated[WorkspaceContext, Depends(require(Capability.INVITATIONS_MANAGE))]
CanTransferOwnership = Annotated[WorkspaceContext, Depends(require(Capability.OWNERSHIP_TRANSFER))]
CanReadWorkspace = Annotated[WorkspaceContext, Depends(require(Capability.WORKSPACE_READ))]

workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])
workspace_router = APIRouter(prefix="/w/{workspace_slug}", tags=["workspaces"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


def _workspace_out(workspace: Workspace, membership: Membership) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        created_at=workspace.created_at,
        role=Role(membership.role),
    )


# ---------------------------------------------------------------- /workspaces


@workspaces_router.get("", response_model=list[WorkspaceOut])
def list_workspaces(auth: CurrentAuth, db: DbSession) -> list[WorkspaceOut]:
    """Workspaces you belong to."""
    return [_workspace_out(w, m) for w, m in service.list_user_workspaces(db, auth.user.id)]


@workspaces_router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(body: WorkspaceCreate, auth: CurrentAuth, db: DbSession, meta: Meta) -> WorkspaceOut:
    """Creates a workspace. You become its owner."""
    workspace, membership = service.create_workspace(
        db, auth.user, body.name, body.slug, meta, actor_user_id=auth.user.id
    )
    db.commit()
    return _workspace_out(workspace, membership)


# ---------------------------------------------------------------- /w/{workspace_slug}


@workspace_router.get("", response_model=WorkspaceOut)
def get_workspace(ctx: CanReadWorkspace) -> WorkspaceOut:
    return _workspace_out(ctx.workspace, ctx.membership)


@workspace_router.patch("", response_model=WorkspaceOut)
def update_workspace(
    body: WorkspaceUpdate, ctx: CanUpdateWorkspace, db: DbSession, meta: Meta
) -> WorkspaceOut:
    """Renames the workspace. Its address (slug) can't change, so links keep working."""
    service.rename_workspace(db, ctx, body.name, meta)
    db.commit()
    return _workspace_out(ctx.workspace, ctx.membership)


@workspace_router.get("/members", response_model=list[MemberOut])
def list_members(ctx: CanReadMembers, db: DbSession) -> list[MemberOut]:
    return [
        MemberOut(
            user_id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=Role(m.role),
            joined_at=m.created_at,
        )
        for m, u in service.list_members(db, ctx.workspace.id)
    ]


@workspace_router.patch("/members/{user_id}", response_model=MemberOut)
def change_member_role(
    user_id: uuid.UUID, body: RoleChange, ctx: CanManageMembers, db: DbSession, meta: Meta
) -> MemberOut:
    membership = service.change_role(db, ctx, user_id, Role(body.role), meta)
    db.commit()
    user = db.get_one(User, user_id)
    return MemberOut(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=Role(membership.role),
        joined_at=membership.created_at,
    )


@workspace_router.delete("/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, ctx: MemberContext, db: DbSession, meta: Meta) -> None:
    """Removes a member. Any member may remove themselves (leave), except the owner."""
    service.remove_member(db, ctx, user_id, meta)
    db.commit()


@workspace_router.post("/ownership", status_code=204)
def transfer_ownership(body: OwnershipTransfer, ctx: CanTransferOwnership, db: DbSession, meta: Meta) -> None:
    """Makes another member the owner. You become an admin."""
    service.transfer_ownership(db, ctx, body.user_id, meta)
    db.commit()


@workspace_router.get("/invitations", response_model=list[InvitationOut])
def list_invitations(ctx: CanManageInvitations, db: DbSession) -> list[InvitationOut]:
    """Pending invitations (not yet accepted, revoked or expired)."""
    return [
        InvitationOut.model_validate(i)
        for i in service.list_pending_invitations(db, ctx.workspace.id, utcnow())
    ]


@workspace_router.post("/invitations", response_model=InvitationCreated, status_code=201)
def create_invitation(
    body: InvitationCreate, ctx: CanManageInvitations, db: DbSession, settings: AppSettings, meta: Meta
) -> InvitationCreated:
    """Creates an invitation and returns its token once. Nothing is emailed: share the link yourself."""
    invitation, token = service.create_invitation(
        db, settings, ctx, body.email, Role(body.role), meta, utcnow()
    )
    db.commit()
    return InvitationCreated(invitation=InvitationOut.model_validate(invitation), token=token)


@workspace_router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(invitation_id: uuid.UUID, ctx: CanManageInvitations, db: DbSession, meta: Meta) -> None:
    service.revoke_invitation(db, ctx, invitation_id, meta, utcnow())
    db.commit()


# ---------------------------------------------------------------- /invitations (token holders)
# The token travels in the request body, never the URL, so it can't end up in access logs or history.


@invitations_router.post("/preview", response_model=InvitationPreview)
def preview_invitation(body: InvitationTokenBody, db: DbSession) -> InvitationPreview:
    invitation, workspace = service.find_valid_invitation(db, body.token, utcnow())
    return InvitationPreview(
        workspace_slug=workspace.slug,
        workspace_name=workspace.name,
        email=invitation.email,
        role=Role(invitation.role),
        expires_at=invitation.expires_at,
        account_exists=identity_service.get_user_by_email(db, invitation.email) is not None,
    )


@invitations_router.post("/accept", response_model=InvitationAccepted)
def accept_invitation(
    body: InvitationAccept,
    auth: OptionalAuth,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    meta: Meta,
) -> InvitationAccepted:
    """Joins the workspace. Creates and signs in a new account if the email has none yet."""
    now = utcnow()
    accepted = service.accept_invitation(
        db, body.token, auth.user if auth else None, body.display_name, body.password, meta, now
    )
    csrf_token = None
    if accepted.new_account:
        issued = identity_service.start_session(db, settings, accepted.user, meta, now)
        set_session_cookies(response, issued)
        csrf_token = issued.csrf_token
    db.commit()
    return InvitationAccepted(
        workspace=_workspace_out(accepted.workspace, accepted.membership),
        user=UserOut.model_validate(accepted.user),
        signed_in=accepted.new_account,
        csrf_token=csrf_token,
    )
