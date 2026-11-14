"""The AI gateway: the one way Booski sends a request to an AI provider.

For every request it, in order:
1. checks the caller may use AI here (the ``ai.use`` capability, narrowed by project access);
2. routes the task to a model, effort and output limit (task override → tier default);
3. refuses if AI is switched off for the workspace, the monthly budget is used up, or no provider is
   configured on the server ("blocked");
4. calls the provider (which applies its own timeouts and retries);
5. records the outcome, tokens and exact cost in ``ai_requests``, whatever happened.

The record is written in its own transaction, so it survives even when the caller's transaction is rolled
back. Prompts and responses are not stored (D35).
"""

import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import project_capabilities
from booski_core.access.roles import Capability
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.ai.models import AiModel, AiRequest, AiTask, AiTierRoute, WorkspaceAiSettings
from booski_core.modules.ai.pricing import Pricing, TokenUsage, cost_usd
from booski_core.modules.ai.providers.base import (
    AiCall,
    AiProvider,
    AiResult,
    ChatMessage,
    ProviderError,
    ProviderErrorKind,
)
from booski_core.modules.projects.models import Project


@dataclass(frozen=True)
class Route:
    task_key: str
    tier: str
    model: AiModel
    effort: str
    max_tokens: int


@dataclass(frozen=True)
class GatewayResult:
    request_id: uuid.UUID
    status: str  # "succeeded" or "refused"
    text: str
    model_key: str
    effort: str
    usage: TokenUsage
    cost_usd: Decimal
    duration_ms: int
    refusal_category: str | None


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def spent_this_month(db: Session, workspace_id: uuid.UUID, now: datetime | None = None) -> Decimal:
    start = month_start(now or utcnow())
    total = db.scalar(
        select(func.coalesce(func.sum(AiRequest.cost_usd), 0)).where(
            AiRequest.workspace_id == workspace_id, AiRequest.created_at >= start
        )
    )
    return Decimal(total or 0)


def resolve_route(db: Session, task_key: str) -> Route:
    task = db.get(AiTask, task_key)
    if task is None or not task.is_active:
        raise ProblemError(400, f"Unknown AI task: {task_key!r}.")
    tier = db.get(AiTierRoute, task.tier)
    if tier is None:  # pragma: no cover - prevented by the foreign key
        raise ProblemError(500, "The AI catalogue is incomplete.")
    model = db.get(AiModel, task.model_id or tier.model_id)
    if model is None or not model.is_active:
        raise ProblemError(503, "The model for this AI task is not available.")
    return Route(
        task_key=task.task_key,
        tier=task.tier,
        model=model,
        effort=task.effort or tier.effort,
        max_tokens=task.max_tokens or tier.max_tokens,
    )


def complete(
    db: Session,
    ctx: WorkspaceContext,
    meta: RequestMeta,
    providers: Mapping[str, AiProvider],
    *,
    task_key: str,
    messages: Sequence[ChatMessage],
    system: str | None = None,
    project: Project | None = None,
) -> GatewayResult:
    """Runs one AI request for the signed-in member. Raises ``ProblemError`` when it can't run."""
    if Capability.AI_USE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, "Your role doesn't allow using AI here.")
    if not messages:
        raise ProblemError(400, "An AI request needs at least one message.")

    route = resolve_route(db, task_key)
    record = _Record(db, ctx, meta, route, project)

    settings = db.get(WorkspaceAiSettings, ctx.workspace.id)
    if settings is None or not settings.enabled:
        record.blocked("ai_disabled")
        raise ProblemError(
            409,
            "AI is switched off for this workspace. An owner or admin can switch it on.",
            code="ai_disabled",
        )
    if spent_this_month(db, ctx.workspace.id) >= settings.monthly_budget_usd:
        record.blocked("budget_reached")
        raise ProblemError(409, "This workspace has reached its monthly AI budget.", code="budget_reached")
    provider = providers.get(route.model.provider)
    if provider is None:
        record.blocked("provider_not_configured")
        raise ProblemError(503, "No AI provider is configured on the server.", code="provider_not_configured")

    call = AiCall(
        model_key=route.model.model_key,
        messages=tuple(messages),
        max_tokens=route.max_tokens,
        system=system,
        effort=route.effort,
    )
    started = time.monotonic()
    try:
        result = provider.complete(call)
    except ProviderError as error:
        record.failed(error, _elapsed_ms(started))
        status = 504 if error.kind is ProviderErrorKind.TIMEOUT else 502
        raise ProblemError(status, str(error), code=error.kind.value) from None

    duration_ms = _elapsed_ms(started)
    cost = cost_usd(Pricing.model_validate(route.model.pricing), result.usage)
    request_id = record.finished(result, cost, duration_ms)
    return GatewayResult(
        request_id=request_id,
        status="refused" if result.refused else "succeeded",
        text=result.text,
        model_key=route.model.model_key,
        effort=route.effort,
        usage=result.usage,
        cost_usd=cost,
        duration_ms=duration_ms,
        refusal_category=result.refusal_category,
    )


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


class _Record:
    """Writes the ``ai_requests`` row in its own short transaction."""

    def __init__(
        self, db: Session, ctx: WorkspaceContext, meta: RequestMeta, route: Route, project: Project | None
    ) -> None:
        self._bind = db.get_bind()
        self._base = {
            "workspace_id": ctx.workspace.id,
            "project_id": project.id if project else None,
            "actor_user_id": ctx.auth.user.id,
            "task_key": route.task_key,
            "tier": route.tier,
            "provider": route.model.provider,
            "model_key": route.model.model_key,
            "effort": route.effort,
            "request_id": meta.request_id,
        }

    def _write(self, **fields: object) -> uuid.UUID:
        with Session(self._bind) as session:
            row = AiRequest(**self._base, **fields)
            session.add(row)
            session.commit()
            return row.id

    def blocked(self, reason: str) -> None:
        self._write(status="blocked", error_code=reason)

    def failed(self, error: ProviderError, duration_ms: int) -> None:
        self._write(
            status="failed",
            error_code=error.kind.value,
            duration_ms=duration_ms,
            provider_request_id=error.provider_request_id,
        )

    def finished(self, result: AiResult, cost: Decimal, duration_ms: int) -> uuid.UUID:
        usage = result.usage
        return self._write(
            status="refused" if result.refused else "succeeded",
            stop_reason=result.stop_reason,
            refusal_category=result.refusal_category,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            cache_read_tokens=usage.cache_read_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            provider_request_id=result.provider_request_id,
        )
