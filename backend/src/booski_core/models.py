"""Single import point for every ORM model, so ``Base.metadata`` is complete for Alembic.

Add an import here whenever a module gains tables.
"""

from booski_core.db import Base
from booski_core.modules.activity.models import ActivityEvent
from booski_core.modules.agents.models import Agent, AgentRun, AgentRunEvent
from booski_core.modules.ai.models import AiModel, AiRequest, AiTask, AiTierRoute, WorkspaceAiSettings
from booski_core.modules.approvals.models import Approval, ApprovalReview
from booski_core.modules.decisions.models import Decision, DecisionDocument
from booski_core.modules.departments.models import Department
from booski_core.modules.identity.models import LoginAttempt, User, UserSession
from booski_core.modules.knowledge.models import Document, DocumentRevision
from booski_core.modules.memory.models import Memory
from booski_core.modules.milestones.models import Milestone
from booski_core.modules.projects.models import Project, ProjectMember, Workstream
from booski_core.modules.tasks.models import Task, TaskComment
from booski_core.modules.workspaces.models import Invitation, Membership, Workspace

__all__ = [
    "ActivityEvent",
    "Agent",
    "AgentRun",
    "AgentRunEvent",
    "AiModel",
    "AiRequest",
    "AiTask",
    "AiTierRoute",
    "Approval",
    "ApprovalReview",
    "Base",
    "Decision",
    "DecisionDocument",
    "Department",
    "Document",
    "DocumentRevision",
    "Invitation",
    "LoginAttempt",
    "Membership",
    "Memory",
    "Milestone",
    "Project",
    "ProjectMember",
    "Task",
    "TaskComment",
    "User",
    "UserSession",
    "Workspace",
    "WorkspaceAiSettings",
    "Workstream",
]
