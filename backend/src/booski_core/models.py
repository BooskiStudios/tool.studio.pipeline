"""Single import point for every ORM model, so ``Base.metadata`` is complete for Alembic.

Add an import here whenever a module gains tables.
"""

from booski_core.db import Base
from booski_core.modules.activity.models import ActivityEvent
from booski_core.modules.identity.models import LoginAttempt, User, UserSession
from booski_core.modules.workspaces.models import Invitation, Membership, Workspace

__all__ = [
    "ActivityEvent",
    "Base",
    "Invitation",
    "LoginAttempt",
    "Membership",
    "User",
    "UserSession",
    "Workspace",
]
