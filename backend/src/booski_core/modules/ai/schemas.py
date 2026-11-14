import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from booski_core.vocab import AiEffort, AiRequestStatus, AiTier


class AiSettingsOut(BaseModel):
    enabled: bool
    monthly_budget_usd: Decimal
    month: str  # "YYYY-MM" (UTC)
    spent_this_month_usd: Decimal
    providers_configured: list[str] = Field(description="AI providers with a key on the server.")
    updated_at: datetime | None


class AiSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    monthly_budget_usd: Decimal | None = Field(default=None, ge=0, le=100_000, decimal_places=2)


class AiCheckOut(BaseModel):
    status: AiRequestStatus
    model_key: str
    duration_ms: int
    cost_usd: Decimal
    request_id: uuid.UUID


class PriceBandOut(BaseModel):
    max_prompt_tokens: int | None
    input: Decimal
    output: Decimal
    cache_write_5m: Decimal
    cache_write_1h: Decimal
    cache_read: Decimal


class AiModelOut(BaseModel):
    provider: str
    model_key: str
    display_name: str
    is_active: bool
    price_bands: list[PriceBandOut] = Field(description="US dollars per million tokens.")


class AiTierOut(BaseModel):
    tier: AiTier
    model_key: str
    effort: AiEffort
    max_tokens: int


class AiTaskOut(BaseModel):
    task_key: str
    description: str
    tier: AiTier
    model_key: str = Field(description="The model this task uses (its override, or its tier's model).")
    effort: AiEffort
    max_tokens: int
    is_active: bool


class AiCatalogOut(BaseModel):
    models: list[AiModelOut]
    tiers: list[AiTierOut]
    tasks: list[AiTaskOut]


class UsageTotals(BaseModel):
    requests: int
    succeeded: int
    refused: int
    failed: int
    blocked: int
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    cost_usd: Decimal


class UsageByKey(UsageTotals):
    key: str


class AiUsageOut(BaseModel):
    month: str
    monthly_budget_usd: Decimal
    totals: UsageTotals
    by_model: list[UsageByKey]
    by_task: list[UsageByKey]


class AiRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    project_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    task_key: str
    tier: AiTier
    provider: str | None
    model_key: str | None
    effort: AiEffort | None
    status: AiRequestStatus
    error_code: str | None
    stop_reason: str | None
    refusal_category: str | None
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    cost_usd: Decimal
    duration_ms: int | None
