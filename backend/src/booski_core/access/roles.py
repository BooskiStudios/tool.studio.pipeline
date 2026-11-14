"""Workspace roles and the capability matrix.

Endpoints never check role names directly: they declare a ``Capability`` and the matrix below decides.
Adding a feature means adding a capability here and a row in tests/test_permissions_matrix.py.

Project access (``access/projects.py``) can only narrow these capabilities inside a project; it never
widens them.
"""

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class Capability(StrEnum):
    # Workspace and people
    WORKSPACE_READ = "workspace.read"  # also: read studio data (projects, tasks, documents, …)
    WORKSPACE_UPDATE = "workspace.update"
    MEMBERS_READ = "members.read"
    MEMBERS_MANAGE = "members.manage"
    INVITATIONS_MANAGE = "invitations.manage"
    OWNERSHIP_TRANSFER = "ownership.transfer"
    # Studio structure
    DEPARTMENTS_MANAGE = "departments.manage"
    PROJECTS_MANAGE = "projects.manage"  # create, edit, archive, restrict projects; workstreams
    # Work
    TASKS_CREATE = "tasks.create"
    TASKS_EDIT_ANY = "tasks.edit_any"  # without it, only tasks you created or are assigned to
    COMMENTS_WRITE = "comments.write"
    MILESTONES_WRITE = "milestones.write"
    # Knowledge and governance
    DOCUMENTS_WRITE = "documents.write"
    DECISIONS_WRITE = "decisions.write"
    MEMORY_WRITE = "memory.write"  # add, edit and archive AI memory entries (PR 3.3)
    APPROVALS_REQUEST = "approvals.request"
    APPROVALS_REVIEW_ASSIGNED = "approvals.review_assigned"  # decide approvals assigned to you
    APPROVALS_DECIDE = "approvals.decide"  # decide any approval
    # History
    ACTIVITY_READ = "activity.read"
    AUDIT_READ = "audit.read"  # security-sensitive events (invitations) in the activity feed
    # AI Core (PR 3.2). Owners and admins only for now; later milestones grant AI_USE to more roles.
    AI_USE = "ai.use"  # send requests through the AI gateway
    AI_MANAGE = "ai.manage"  # switch AI on/off, set the monthly budget, run the connection check
    AI_USAGE_READ = "ai.usage.read"  # see AI usage, cost and the request log


_EVERYONE = frozenset({Capability.WORKSPACE_READ, Capability.MEMBERS_READ, Capability.ACTIVITY_READ})
_COLLABORATE = frozenset({Capability.TASKS_CREATE, Capability.COMMENTS_WRITE})
_DEVELOP = frozenset(
    {
        Capability.TASKS_EDIT_ANY,
        Capability.MILESTONES_WRITE,
        Capability.DOCUMENTS_WRITE,
        Capability.DECISIONS_WRITE,
        Capability.MEMORY_WRITE,
        Capability.APPROVALS_REQUEST,
        Capability.APPROVALS_REVIEW_ASSIGNED,
    }
)
_ADMINISTER = frozenset(
    {
        Capability.WORKSPACE_UPDATE,
        Capability.MEMBERS_MANAGE,
        Capability.INVITATIONS_MANAGE,
        Capability.DEPARTMENTS_MANAGE,
        Capability.PROJECTS_MANAGE,
        Capability.APPROVALS_DECIDE,
        Capability.AUDIT_READ,
        Capability.AI_USE,
        Capability.AI_MANAGE,
        Capability.AI_USAGE_READ,
    }
)

ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.OWNER: _EVERYONE | _COLLABORATE | _DEVELOP | _ADMINISTER | {Capability.OWNERSHIP_TRANSFER},
    Role.ADMIN: _EVERYONE | _COLLABORATE | _DEVELOP | _ADMINISTER,
    Role.DEVELOPER: _EVERYONE | _COLLABORATE | _DEVELOP,
    Role.COLLABORATOR: _EVERYONE | _COLLABORATE,
    Role.VIEWER: _EVERYONE,
}

# Inside a project where someone has "viewer" project access, only these remain.
READ_ONLY_CAPABILITIES = _EVERYONE

# Roles a member may grant, change or remove. Admins manage everyone below admin; only the owner
# manages admins. Nobody assigns "owner" directly: ownership moves only by transfer.
MANAGEABLE_ROLES: dict[Role, frozenset[Role]] = {
    Role.OWNER: frozenset({Role.ADMIN, Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER}),
    Role.ADMIN: frozenset({Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER}),
    Role.DEVELOPER: frozenset(),
    Role.COLLABORATOR: frozenset(),
    Role.VIEWER: frozenset(),
}

# Roles that see every project, including restricted ones.
SEES_ALL_PROJECTS = frozenset({Role.OWNER, Role.ADMIN})


def has_capability(role: Role, capability: Capability) -> bool:
    return capability in ROLE_CAPABILITIES[role]


def can_manage(actor: Role, target: Role) -> bool:
    return target in MANAGEABLE_ROLES[actor]
