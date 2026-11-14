"""AI settings, connection check, catalogue, usage and request log for a workspace (PR 3.2).

There is no general "chat" endpoint: AI is used through features built in later milestones, all of which
go through ``gateway.complete``.
"""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from booski_core.access.dependencies import WorkspaceContext, require
from booski_core.access.roles import Capability
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.ai import gateway, service
from booski_core.modules.ai.providers.base import AiProvider, ChatMessage
from booski_core.modules.ai.schemas import (
    AiCatalogOut,
    AiCheckOut,
    AiRequestOut,
    AiSettingsOut,
    AiSettingsUpdate,
    AiUsageOut,
)
from booski_core.modules.identity.dependencies import DbSession, Meta

router = APIRouter(prefix="/w/{workspace_slug}/ai", tags=["ai"])

ManageAi = Annotated[WorkspaceContext, Depends(require(Capability.AI_MANAGE))]
ReadUsage = Annotated[WorkspaceContext, Depends(require(Capability.AI_USAGE_READ))]

CONNECTION_CHECK_PROMPT = "Reply with the single word OK."


def get_providers(request: Request) -> Mapping[str, AiProvider]:
    providers: Mapping[str, AiProvider] = request.app.state.ai_providers
    return providers


Providers = Annotated[Mapping[str, AiProvider], Depends(get_providers)]


@router.get("/settings", response_model=AiSettingsOut)
def get_settings(ctx: ManageAi, db: DbSession, providers: Providers) -> AiSettingsOut:
    """Whether AI is on, the monthly budget, this month's spend and which providers are configured."""
    return service.settings_out(db, ctx, providers)


@router.patch("/settings", response_model=AiSettingsOut)
def update_settings(
    body: AiSettingsUpdate, ctx: ManageAi, db: DbSession, meta: Meta, providers: Providers
) -> AiSettingsOut:
    service.update_settings(db, ctx, body, meta)
    db.commit()
    return service.settings_out(db, ctx, providers)


@router.post("/check", response_model=AiCheckOut)
def connection_check(ctx: ManageAi, db: DbSession, meta: Meta, providers: Providers) -> AiCheckOut:
    """Sends one tiny request through the gateway to prove the provider answers. It is logged and costs a
    fraction of a cent; it is blocked like any request when AI is off or the budget is used up."""
    result = gateway.complete(
        db,
        ctx,
        meta,
        providers,
        task_key="connection-check",
        messages=[ChatMessage(role="user", content=CONNECTION_CHECK_PROMPT)],
    )
    return AiCheckOut(
        status=result.status,
        model_key=result.model_key,
        duration_ms=result.duration_ms,
        cost_usd=result.cost_usd,
        request_id=result.request_id,
    )


@router.get("/catalog", response_model=AiCatalogOut)
def get_catalog(ctx: ManageAi, db: DbSession) -> AiCatalogOut:
    """Models with prices (US dollars per million tokens), tier defaults and task routes."""
    return service.catalog_out(db)


@router.get("/usage", response_model=AiUsageOut)
def get_usage(
    ctx: ReadUsage,
    db: DbSession,
    month: Annotated[str | None, Query(description="YYYY-MM (UTC); defaults to the current month.")] = None,
) -> AiUsageOut:
    """Request counts, tokens and cost for a month, in total and by model and task."""
    return service.usage_out(db, ctx, month)


@router.get("/requests", response_model=Page[AiRequestOut])
def list_requests(
    ctx: ReadUsage, db: DbSession, limit: Limit = 50, cursor: Cursor = None
) -> Page[AiRequestOut]:
    """The AI request log, newest first. Metadata only: prompts and responses are not stored."""
    rows, next_cursor = service.list_requests(db, ctx, limit=limit, cursor=cursor)
    return Page(items=[AiRequestOut.model_validate(row) for row in rows], next_cursor=next_cursor)
