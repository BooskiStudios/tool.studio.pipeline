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
# AI Core (PR 3.2)
AiProviderKey = Literal["anthropic"]
AiTier = Literal["routine", "standard", "deep"]
AiEffort = Literal["low", "medium", "high", "xhigh", "max"]
# blocked: refused by Booski before calling a provider (AI off, budget reached, no provider configured).
# refused: the model declined the request. failed: the provider call errored or timed out.
AiRequestStatus = Literal["succeeded", "refused", "failed", "blocked"]
# Memory and retrieval (PR 3.3)
MemoryKind = Literal["fact", "convention", "lesson", "preference"]
SourceType = Literal["memory", "document", "decision"]
# Agents (PR 3.4). Autonomy levels 3-4 need tools (PR 3.5+); only the first two can be configured yet.
AutonomyLevel = Literal["assist", "execute_with_approval", "controlled_autonomy", "coordinated_workflows"]
AgentRunStatus = Literal["queued", "running", "paused", "succeeded", "failed", "cancelled"]
AgentRunEventType = Literal[
    "created",
    "claimed",
    "planned",
    "step_started",
    "step_completed",
    "step_retried",
    "step_failed",
    "paused",
    "resumed",
    "redirected",
    "cancelled",
    "completed",
    "failed",
    "review_requested",
    "changes_applied",
    "changes_rejected",
    "changes_failed",
]
# Tools (PR 3.5). "read" tools only look; "propose" tools stage a change that is applied only when a person
# approves the run's review (D57). There is deliberately no kind that edits or deletes.
ToolKind = Literal["read", "propose"]
ToolCallStatus = Literal["succeeded", "failed", "denied", "limit_reached"]
ChangeStatus = Literal["proposed", "applied", "rejected", "failed", "discarded"]


def values(literal: object) -> tuple[str, ...]:
    return tuple(str(v) for v in get_args(literal))
