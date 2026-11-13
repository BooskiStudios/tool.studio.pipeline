"""Workspace roles and the capability matrix.

Endpoints never check role names directly: they declare a ``Capability`` and the matrix below decides.
Adding a feature means adding a capability here and a row in tests/test_permissions_matrix.py.

Project-level restrictions (PR 2.3+) will narrow these workspace capabilities per project; they will
never widen them.
"""

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class Capability(StrEnum):
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_UPDATE = "workspace.update"
    MEMBERS_READ = "members.read"
    MEMBERS_MANAGE = "members.manage"
    INVITATIONS_MANAGE = "invitations.manage"
    OWNERSHIP_TRANSFER = "ownership.transfer"


_EVERYONE = frozenset({Capability.WORKSPACE_READ, Capability.MEMBERS_READ})
_ADMINISTER = frozenset(
    {Capability.WORKSPACE_UPDATE, Capability.MEMBERS_MANAGE, Capability.INVITATIONS_MANAGE}
)

ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.OWNER: _EVERYONE | _ADMINISTER | {Capability.OWNERSHIP_TRANSFER},
    Role.ADMIN: _EVERYONE | _ADMINISTER,
    Role.DEVELOPER: _EVERYONE,
    Role.COLLABORATOR: _EVERYONE,
    Role.VIEWER: _EVERYONE,
}

# Roles a member may grant, change or remove. Admins manage everyone below admin; only the owner
# manages admins. Nobody assigns "owner" directly: ownership moves only by transfer.
MANAGEABLE_ROLES: dict[Role, frozenset[Role]] = {
    Role.OWNER: frozenset({Role.ADMIN, Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER}),
    Role.ADMIN: frozenset({Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER}),
    Role.DEVELOPER: frozenset(),
    Role.COLLABORATOR: frozenset(),
    Role.VIEWER: frozenset(),
}


def has_capability(role: Role, capability: Capability) -> bool:
    return capability in ROLE_CAPABILITIES[role]


def can_manage(actor: Role, target: Role) -> bool:
    return target in MANAGEABLE_ROLES[actor]
