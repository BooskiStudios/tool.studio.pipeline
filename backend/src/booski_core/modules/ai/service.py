"""Workspace AI settings, the catalogue view, usage totals and the request log."""

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import project_scope
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.ai import schemas
from booski_core.modules.ai.gateway import month_start, spent_this_month
from booski_core.modules.ai.models import AiModel, AiRequest, AiTask, AiTierRoute, WorkspaceAiSettings
from booski_core.modules.ai.pricing import Pricing
from booski_core.modules.ai.providers.base import AiProvider

DEFAULT_MONTHLY_BUDGET_USD = Decimal("20.00")  # D34
_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _month_label(moment: datetime) -> str:
    return moment.strftime("%Y-%m")


# ---------------------------------------------------------------- settings


def settings_out(
    db: Session, ctx: WorkspaceContext, providers: Mapping[str, AiProvider]
) -> schemas.AiSettingsOut:
    row = db.get(WorkspaceAiSettings, ctx.workspace.id)
    now = utcnow()
    return schemas.AiSettingsOut(
        enabled=bool(row and row.enabled),
        monthly_budget_usd=row.monthly_budget_usd if row else DEFAULT_MONTHLY_BUDGET_USD,
        month=_month_label(now),
        spent_this_month_usd=spent_this_month(db, ctx.workspace.id, now),
        providers_configured=sorted(providers),
        updated_at=row.updated_at if row else None,
    )


def update_settings(
    db: Session, ctx: WorkspaceContext, body: schemas.AiSettingsUpdate, meta: RequestMeta
) -> None:
    row = db.get(WorkspaceAiSettings, ctx.workspace.id)
    if row is None:
        row = WorkspaceAiSettings(
            workspace_id=ctx.workspace.id, enabled=False, monthly_budget_usd=DEFAULT_MONTHLY_BUDGET_USD
        )
        db.add(row)
    changes: dict[str, object] = {}
    if body.enabled is not None and body.enabled != row.enabled:
        changes["enabled"] = {"from": row.enabled, "to": body.enabled}
        row.enabled = body.enabled
    if body.monthly_budget_usd is not None and body.monthly_budget_usd != row.monthly_budget_usd:
        changes["monthly_budget_usd"] = {
            "from": str(row.monthly_budget_usd),
            "to": str(body.monthly_budget_usd),
        }
        row.monthly_budget_usd = body.monthly_budget_usd
    if not changes:
        return
    row.updated_at = utcnow()
    row.updated_by_user_id = ctx.auth.user.id
    if "enabled" in changes:
        summary = "Switched AI on" if row.enabled else "Switched AI off"
    else:
        summary = f"Set the monthly AI budget to ${row.monthly_budget_usd}"
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="ai.settings_updated",
        entity_type="workspace",
        entity_id=ctx.workspace.id,
        summary=summary,
        changes=changes,
    )


# ---------------------------------------------------------------- catalogue


def catalog_out(db: Session) -> schemas.AiCatalogOut:
    models = {m.id: m for m in db.scalars(select(AiModel).order_by(AiModel.provider, AiModel.model_key))}
    tiers = {t.tier: t for t in db.scalars(select(AiTierRoute))}
    tier_order = {"routine": 0, "standard": 1, "deep": 2}
    tasks = db.scalars(select(AiTask).order_by(AiTask.task_key)).all()
    return schemas.AiCatalogOut(
        models=[
            schemas.AiModelOut(
                provider=m.provider,
                model_key=m.model_key,
                display_name=m.display_name,
                is_active=m.is_active,
                price_bands=[
                    schemas.PriceBandOut(**band.model_dump())
                    for band in Pricing.model_validate(m.pricing).bands
                ],
            )
            for m in models.values()
        ],
        tiers=[
            schemas.AiTierOut(
                tier=t.tier, model_key=models[t.model_id].model_key, effort=t.effort, max_tokens=t.max_tokens
            )
            for t in sorted(tiers.values(), key=lambda t: tier_order.get(t.tier, 99))
        ],
        tasks=[
            schemas.AiTaskOut(
                task_key=task.task_key,
                description=task.description,
                tier=task.tier,
                model_key=models[task.model_id or tiers[task.tier].model_id].model_key,
                effort=task.effort or tiers[task.tier].effort,
                max_tokens=task.max_tokens or tiers[task.tier].max_tokens,
                is_active=task.is_active,
            )
            for task in tasks
        ],
    )


# ---------------------------------------------------------------- usage


def parse_month(month: str | None) -> datetime:
    """The first instant of ``month`` ("YYYY-MM", UTC), or of the current month."""
    if month is None:
        return month_start(utcnow())
    match = _MONTH.match(month)
    if match is None:
        raise ProblemError(400, "month must look like 2026-11.")
    return datetime(int(match[1]), int(match[2]), 1, tzinfo=UTC)


def _next_month(start: datetime) -> datetime:
    return (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )


def _totals_columns() -> list[ColumnElement[Any]]:
    def count_status(status: str) -> ColumnElement[Any]:
        return func.count(case((AiRequest.status == status, 1)))

    return [
        func.count(),
        count_status("succeeded"),
        count_status("refused"),
        count_status("failed"),
        count_status("blocked"),
        func.coalesce(func.sum(AiRequest.input_tokens), 0),
        func.coalesce(func.sum(AiRequest.output_tokens), 0),
        func.coalesce(func.sum(AiRequest.cache_write_tokens), 0),
        func.coalesce(func.sum(AiRequest.cache_read_tokens), 0),
        func.coalesce(func.sum(AiRequest.cost_usd), 0),
    ]


def _totals(row: tuple[object, ...]) -> dict[str, object]:
    names = ["requests", "succeeded", "refused", "failed", "blocked", "input_tokens", "output_tokens"]
    names += ["cache_write_tokens", "cache_read_tokens", "cost_usd"]
    return dict(zip(names, row, strict=True))


def usage_out(db: Session, ctx: WorkspaceContext, month: str | None) -> schemas.AiUsageOut:
    start = parse_month(month)
    where = (
        AiRequest.workspace_id == ctx.workspace.id,
        AiRequest.created_at >= start,
        AiRequest.created_at < _next_month(start),
    )
    totals = db.execute(select(*_totals_columns()).where(*where)).one()

    def grouped(column: InstrumentedAttribute[Any]) -> list[schemas.UsageByKey]:
        rows = db.execute(
            select(column, *_totals_columns()).where(*where).group_by(column).order_by(column)
        ).all()
        return [schemas.UsageByKey(key=row[0] or "none", **_totals(tuple(row[1:]))) for row in rows]

    settings = db.get(WorkspaceAiSettings, ctx.workspace.id)
    return schemas.AiUsageOut(
        month=_month_label(start),
        monthly_budget_usd=settings.monthly_budget_usd if settings else DEFAULT_MONTHLY_BUDGET_USD,
        totals=schemas.UsageTotals(**_totals(tuple(totals))),
        by_model=grouped(AiRequest.model_key),
        by_task=grouped(AiRequest.task_key),
    )


def list_requests(
    db: Session, ctx: WorkspaceContext, *, limit: int, cursor: str | None
) -> tuple[list[AiRequest], str | None]:
    query = select(AiRequest).where(
        AiRequest.workspace_id == ctx.workspace.id, project_scope(ctx, AiRequest.project_id)
    )
    rows, next_cursor = paginate(
        db,
        query,
        key=SortKey(AiRequest.created_at, datetime.fromisoformat),
        id_column=AiRequest.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda r: r.created_at,
        row_id=lambda r: r.id,
    )
    return list(rows), next_cursor
