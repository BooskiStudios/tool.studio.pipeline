import json
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from booski_core.core.fields import Text20000, Title
from booski_core.vocab import ApprovalAction, ApprovalKind, ApprovalStatus, ApprovalSubjectType

Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
MAX_PAYLOAD_BYTES = 64_000


def _check_payload(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is not None and len(json.dumps(value)) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload must be at most {MAX_PAYLOAD_BYTES} bytes as JSON")
    return value


class ApprovalCreate(BaseModel):
    kind: ApprovalKind = "general"
    title: Title
    description: Text20000 = ""
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details of what is being approved (e.g. a diff summary).",
    )
    project_id: uuid.UUID | None = None
    subject_type: ApprovalSubjectType | None = None
    subject_id: uuid.UUID | None = None
    reviewer_user_id: uuid.UUID | None = Field(default=None, description="Who should decide. Optional.")
    due_at: datetime | None = None

    _payload = field_validator("payload")(_check_payload)


class ApprovalUpdate(BaseModel):
    """Reassign or reschedule an open request (requester, owners and admins)."""

    reviewer_user_id: uuid.UUID | None = None
    due_at: datetime | None = None
    version: int | None = None


ReviewAction = Literal["approve", "reject", "request_changes", "comment"]


class ReviewCreate(BaseModel):
    action: ReviewAction
    comment: Comment = ""


class ResubmitBody(BaseModel):
    comment: Comment = ""
    description: Text20000 | None = None
    payload: dict[str, Any] | None = None

    _payload = field_validator("payload")(_check_payload)


class CancelBody(BaseModel):
    comment: Comment = ""


class ApprovalOut(BaseModel):
    id: uuid.UUID
    kind: ApprovalKind
    title: str
    description: str
    payload: dict[str, Any]
    project_id: uuid.UUID | None
    subject_type: ApprovalSubjectType | None
    subject_id: uuid.UUID | None
    status: ApprovalStatus
    requested_by_user_id: uuid.UUID | None
    reviewer_user_id: uuid.UUID | None
    resolved_by_user_id: uuid.UUID | None
    resolution_comment: str
    resolved_at: datetime | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    can_decide: bool


class ReviewOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: ApprovalAction
    comment: str
    created_at: datetime
