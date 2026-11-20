import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from booski_core.modules.agents.models import MAX_GOAL_CHARS, MAX_GUIDANCE_CHARS
from booski_core.vocab import AgentRunEventType, AgentRunStatus, ChangeStatus, ToolCallStatus, ToolKind

Key = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", min_length=2, max_length=48)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Guidance = Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_GUIDANCE_CHARS)]
Goal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_GOAL_CHARS)]
Instruction = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)]
ToolName = Annotated[str, StringConstraints(pattern=r"^[a-z_]{2,40}$")]
# Levels 3-4 (controlled autonomy, coordinated workflows) are not enabled yet (D58).
ConfigurableAutonomy = Literal["assist", "execute_with_approval"]


class AgentFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    guidance: Guidance = ""
    responsibilities: list[Line] = Field(default_factory=list, max_length=20)
    must_not: list[Line] = Field(default_factory=list, max_length=20)
    delegates_to: list[Key] = Field(default_factory=list, max_length=10)
    department_id: uuid.UUID | None = None
    task_key: Key = "draft"
    autonomy: ConfigurableAutonomy = "execute_with_approval"
    max_steps: int = Field(default=6, ge=1, le=20)
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), gt=0, le=100, decimal_places=2)
    tools: list[ToolName] = Field(default_factory=list, max_length=30)
    max_tool_calls_per_step: int = Field(default=10, ge=0, le=50)
    max_tool_calls_per_run: int = Field(default=40, ge=0, le=200)
    max_changes_per_run: int = Field(default=20, ge=0, le=100)


class AgentCreate(AgentFields):
    key: Key
    name: Name


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    guidance: Guidance | None = None
    responsibilities: list[Line] | None = Field(default=None, max_length=20)
    must_not: list[Line] | None = Field(default=None, max_length=20)
    delegates_to: list[Key] | None = Field(default=None, max_length=10)
    department_id: uuid.UUID | None = None
    task_key: Key | None = None
    autonomy: ConfigurableAutonomy | None = None
    max_steps: int | None = Field(default=None, ge=1, le=20)
    max_cost_usd: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=2)
    tools: list[ToolName] | None = Field(default=None, max_length=30)
    max_tool_calls_per_step: int | None = Field(default=None, ge=0, le=50)
    max_tool_calls_per_run: int | None = Field(default=None, ge=0, le=200)
    max_changes_per_run: int | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None
    version: int | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    department_id: uuid.UUID | None
    description: str
    guidance: str
    responsibilities: list[str]
    must_not: list[str]
    delegates_to: list[str]
    task_key: str
    autonomy: str
    max_steps: int
    max_cost_usd: Decimal
    tools: list[str]
    max_tool_calls_per_step: int
    max_tool_calls_per_run: int
    max_changes_per_run: int
    is_active: bool
    version: int
    updated_at: datetime


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Key = Field(description="The agent's key, e.g. producer.")
    goal: Goal
    project: str | None = Field(default=None, description="Project slug.")
    task_id: uuid.UUID | None = None


class RedirectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: Instruction


class RunStep(BaseModel):
    n: int
    title: str
    instruction: str
    agent: str
    status: Literal["pending", "completed"]
    output: str = ""


class RunSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent: str
    goal: str
    status: AgentRunStatus
    project_id: uuid.UUID | None
    task_id: uuid.UUID | None
    started_by_user_id: uuid.UUID | None
    steps_used: int
    cost_usd: Decimal
    error_code: str | None
    approval_id: uuid.UUID | None
    created_at: datetime
    finished_at: datetime | None
    version: int


class RunOut(RunSummaryOut):
    plan: list[RunStep]
    notes: list[dict[str, Any]]
    output: str
    error_detail: str | None
    attempts: int
    tool_calls_used: int
    started_at: datetime | None
    can_control: bool = False


class ToolOut(BaseModel):
    name: str
    kind: ToolKind
    description: str
    input_schema: dict[str, Any]


class ToolCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step: int
    agent_key: str
    tool: str
    kind: ToolKind
    input: dict[str, Any]
    status: ToolCallStatus
    result_preview: str
    error: str | None
    duration_ms: int
    change_id: uuid.UUID | None
    created_at: datetime


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seq: int
    tool: str
    summary: str
    payload: dict[str, Any]
    status: ChangeStatus
    applied_ids: list[str]
    error: str | None
    created_at: datetime
    updated_at: datetime


class RunEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    type: AgentRunEventType
    actor_user_id: uuid.UUID | None
    ai_request_id: uuid.UUID | None
    data: dict[str, Any]
    created_at: datetime
