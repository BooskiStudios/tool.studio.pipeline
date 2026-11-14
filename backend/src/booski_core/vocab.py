"""Allowed values for status-like text columns, shared by models (CHECK constraints) and schemas.

Text + CHECK instead of PostgreSQL ENUM types (decision D12): adding a value is a one-line migration.
"""

from typing import Literal, get_args

AccentColor = Literal["pink", "blue", "green", "orange", "purple", "cyan", "red"]
ProjectStatus = Literal[
    "concept", "pre_production", "prototype", "production", "released", "paused", "cancelled"
]
ProjectVisibility = Literal["workspace", "restricted"]
ProjectAccess = Literal["viewer", "contributor"]
MilestoneStatus = Literal["planned", "in_progress", "completed", "cancelled"]
TaskStatus = Literal["backlog", "todo", "in_progress", "in_review", "blocked", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high"]
DocumentKind = Literal["guide", "research", "template", "reference", "design_doc", "note", "report"]
DecisionStatus = Literal["proposed", "accepted", "rejected", "superseded"]
ApprovalKind = Literal[
    "general", "ai_output", "code_change", "asset", "spending", "publishing", "project_decision"
]
ApprovalStatus = Literal["pending", "changes_requested", "approved", "rejected", "cancelled"]
ApprovalAction = Literal["approved", "rejected", "changes_requested", "commented", "resubmitted", "cancelled"]
ApprovalSubjectType = Literal["task", "document", "decision", "milestone", "project"]


def values(literal: object) -> tuple[str, ...]:
    return tuple(str(v) for v in get_args(literal))
