"""Workspace-scoped access checks for routes under ``/api/v1/w/{workspace_slug}``.

* Not a member (or the workspace doesn't exist or is archived) → 404, so outsiders can't even confirm
  that a workspace exists.
* A member whose role lacks the capability → 403.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from booski_core.access.roles import Capability, Role, has_capability
from booski_core.core.errors import ProblemError
from booski_core.modules.identity.dependencies import AuthContext, CurrentAuth, DbSession
from booski_core.modules.workspaces.models import Membership, Workspace

WORKSPACE_NOT_FOUND = "Workspace not found."


@dataclass(frozen=True)
class WorkspaceContext:
    auth: AuthContext
    workspace: Workspace
    membership: Membership

    @property
    def role(self) -> Role:
        return Role(self.membership.role)


def get_workspace_context(workspace_slug: str, auth: CurrentAuth, db: DbSession) -> WorkspaceContext:
    row = db.execute(
        select(Workspace, Membership)
        .join(
            Membership,
            (Membership.workspace_id == Workspace.id) & (Membership.user_id == auth.user.id),
        )
        .where(Workspace.slug == workspace_slug, Workspace.archived_at.is_(None))
    ).one_or_none()
    if row is None:
        raise ProblemError(404, WORKSPACE_NOT_FOUND)
    return WorkspaceContext(auth=auth, workspace=row[0], membership=row[1])


def require(capability: Capability) -> Callable[..., WorkspaceContext]:
    """Dependency factory: ``ctx: Annotated[WorkspaceContext, Depends(require(Capability.X))]``."""

    def dependency(ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)]) -> WorkspaceContext:
        if not has_capability(ctx.role, capability):
            raise ProblemError(403, "Your role in this workspace doesn't allow this.")
        return ctx

    dependency.__name__ = f"require_{capability.value.replace('.', '_')}"
    return dependency


MemberContext = Annotated[WorkspaceContext, Depends(get_workspace_context)]
