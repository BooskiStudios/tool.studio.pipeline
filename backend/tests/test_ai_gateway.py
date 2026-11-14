"""The AI gateway, settings, usage and the request log, against a real database and a fake provider."""

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from ai_fakes import FakeProvider
from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.roles import Role
from booski_core.config import Settings
from booski_core.core.errors import ProblemError
from booski_core.core.request_meta import RequestMeta
from booski_core.main import create_app
from booski_core.models import ActivityEvent, Membership, Project, User, Workspace
from booski_core.modules.ai import gateway
from booski_core.modules.ai.models import AiModel, AiRequest, AiTask, WorkspaceAiSettings
from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import AiResult, ChatMessage, ProviderError, ProviderErrorKind
from booski_core.modules.identity.dependencies import AuthContext
from helpers import sign_in
from studio import Studio, build_studio

pytestmark = pytest.mark.db

B = "/api/v1/w/booski/ai"
SignedIn = Callable[..., TestClient]


@pytest.fixture
def studio(db: Session) -> Studio:
    return build_studio(db, project_visibility="restricted")


@pytest.fixture
def owner(studio: Studio, signed_in: SignedIn) -> TestClient:
    return signed_in(studio.members[Role.OWNER])


def _enable(db: Session, studio: Studio, budget: str = "20") -> None:
    db.merge(
        WorkspaceAiSettings(
            workspace_id=studio.workspace_id, enabled=True, monthly_budget_usd=Decimal(budget)
        )
    )
    db.commit()


def _requests(db: Session) -> list[AiRequest]:
    db.expire_all()
    return list(db.scalars(select(AiRequest).order_by(AiRequest.created_at)))


def _context(db: Session, studio: Studio, role: Role) -> WorkspaceContext:
    user_id = studio.members[role].id
    user = db.get(User, user_id)
    workspace = db.get(Workspace, studio.workspace_id)
    membership = db.scalars(
        select(Membership).where(
            Membership.workspace_id == studio.workspace_id, Membership.user_id == user_id
        )
    ).one()
    auth = AuthContext(user=cast(Any, user), session=cast(Any, None))
    return WorkspaceContext(auth=auth, workspace=cast(Any, workspace), membership=cast(Any, membership))


META = RequestMeta(request_id="req-test", ip=None, user_agent=None)
HELLO = [ChatMessage(role="user", content="Hello")]


# ---------------------------------------------------------------- settings


def test_ai_is_off_by_default_with_a_twenty_dollar_budget(owner: TestClient) -> None:
    body = owner.get(f"{B}/settings").json()
    assert body["enabled"] is False
    assert Decimal(body["monthly_budget_usd"]) == Decimal("20")
    assert Decimal(body["spent_this_month_usd"]) == 0
    assert body["providers_configured"] == ["anthropic"]


def test_switching_ai_on_is_recorded_in_the_activity_log(owner: TestClient, db: Session) -> None:
    response = owner.patch(f"{B}/settings", json={"enabled": True, "monthly_budget_usd": "35.50"})
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert Decimal(response.json()["monthly_budget_usd"]) == Decimal("35.50")
    event = db.scalars(select(ActivityEvent).where(ActivityEvent.verb == "ai.settings_updated")).one()
    assert event.summary == "Switched AI on"
    assert event.changes["monthly_budget_usd"] == {"from": "20.00", "to": "35.50"}


@pytest.mark.parametrize(
    "body", [{"monthly_budget_usd": "-1"}, {"monthly_budget_usd": "1.234"}, {"api_key": "x"}]
)
def test_invalid_settings_are_rejected(owner: TestClient, body: dict[str, object]) -> None:
    assert owner.patch(f"{B}/settings", json=body).status_code == 422


def test_the_server_key_is_never_returned(studio: Studio, migrated_db: Any, db_settings: Settings) -> None:
    secret = "sk-ant-secret-for-this-test-only"
    app = create_app(db_settings.model_copy(update={"anthropic_api_key": SecretStr(secret)}))
    try:
        client = sign_in(TestClient(app, base_url="https://testserver"), studio.members[Role.OWNER])
        assert client.get(f"{B}/settings").json()["providers_configured"] == ["anthropic"]
        for path in ("/settings", "/catalog", "/usage", "/requests"):
            assert secret not in client.get(f"{B}{path}").text
        assert secret not in repr(db_settings.model_copy(update={"anthropic_api_key": SecretStr(secret)}))
    finally:
        app.state.engine.dispose()


# ---------------------------------------------------------------- connection check through the gateway


def test_check_is_blocked_and_logged_while_ai_is_off(
    owner: TestClient, db: Session, fake_ai: FakeProvider
) -> None:
    response = owner.post(f"{B}/check")
    assert response.status_code == 409
    assert response.json()["code"] == "ai_disabled"
    assert fake_ai.calls == []
    [row] = _requests(db)
    assert (row.status, row.error_code) == ("blocked", "ai_disabled")
    assert row.cost_usd == 0


def test_check_succeeds_and_records_tokens_and_exact_cost(
    owner: TestClient, db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    _enable(db, studio)
    response = owner.post(f"{B}/check")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["model_key"] == "claude-haiku-5-5"

    [call] = fake_ai.calls
    assert (call.model_key, call.effort, call.max_tokens) == ("claude-haiku-5-5", "low", 1024)

    [row] = _requests(db)
    assert row.status == "succeeded"
    assert (row.task_key, row.tier, row.provider) == ("connection-check", "routine", "anthropic")
    assert (row.input_tokens, row.output_tokens) == (12, 4)
    # Haiku 5.5: 12 x $0.10 + 4 x $0.50 per million tokens.
    assert row.cost_usd == Decimal("0.0000032")
    assert Decimal(body["cost_usd"]) == row.cost_usd
    assert row.actor_user_id == studio.members[Role.OWNER].id
    assert row.provider_request_id == "req_fake"
    assert row.request_id  # our request id, to match logs


def test_requests_are_refused_once_the_budget_is_used_up(
    owner: TestClient, db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    _enable(db, studio, budget="0.05")
    assert owner.post(f"{B}/check").status_code == 200  # costs $0.0000032
    # Earlier spend this month brings the total to the budget.
    db.add(
        AiRequest(
            workspace_id=studio.workspace_id,
            task_key="draft",
            tier="standard",
            status="succeeded",
            cost_usd=Decimal("0.05"),
        )
    )
    db.commit()
    response = owner.post(f"{B}/check")
    assert response.status_code == 409
    assert response.json()["code"] == "budget_reached"
    assert len(fake_ai.calls) == 1
    assert [r.status for r in _requests(db)] == ["succeeded", "succeeded", "blocked"]


def test_requests_are_blocked_when_no_provider_is_configured(
    owner: TestClient, db: Session, studio: Studio, app: Any
) -> None:
    _enable(db, studio)
    app.state.ai_providers = {}
    response = owner.post(f"{B}/check")
    assert response.status_code == 503
    assert response.json()["code"] == "provider_not_configured"
    assert _requests(db)[0].error_code == "provider_not_configured"


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        (ProviderErrorKind.TIMEOUT, 504),
        (ProviderErrorKind.RATE_LIMITED, 502),
        (ProviderErrorKind.UNAVAILABLE, 502),
    ],
)
def test_provider_failures_are_reported_and_logged(
    owner: TestClient,
    db: Session,
    studio: Studio,
    fake_ai: FakeProvider,
    kind: ProviderErrorKind,
    status: int,
) -> None:
    _enable(db, studio)
    fake_ai.error = ProviderError(kind, "simulated failure", provider_request_id="req_x")
    response = owner.post(f"{B}/check")
    assert response.status_code == status
    assert response.json()["code"] == kind.value
    [row] = _requests(db)
    assert (row.status, row.error_code, row.provider_request_id) == ("failed", kind.value, "req_x")
    assert row.cost_usd == 0


def test_refusals_are_logged_with_their_category(
    owner: TestClient, db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    _enable(db, studio)
    fake_ai.result = AiResult(
        text="", stop_reason="refusal", usage=TokenUsage(input_tokens=10), refusal_category="cyber"
    )
    assert owner.post(f"{B}/check").json()["status"] == "refused"
    [row] = _requests(db)
    assert (row.status, row.stop_reason, row.refusal_category) == ("refused", "refusal", "cyber")
    assert row.cost_usd == Decimal("0.000001")  # input tokens are still billed


# ---------------------------------------------------------------- routing and permissions (gateway directly)


def test_tasks_use_their_tier_defaults_or_their_own_overrides(
    db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    _enable(db, studio)
    ctx = _context(db, studio, Role.OWNER)
    providers = {"anthropic": fake_ai}

    gateway.complete(db, ctx, META, providers, task_key="draft", messages=HELLO)
    gateway.complete(db, ctx, META, providers, task_key="review", messages=HELLO)
    draft, review = fake_ai.calls
    assert (draft.model_key, draft.effort, draft.max_tokens) == ("claude-sonnet-5-5", "medium", 16000)
    assert (review.model_key, review.effort) == ("claude-opus-5-5", "high")

    # A task override (data, not code) changes the model and effort without touching any caller.
    task = db.get(AiTask, "summarise")
    opus = db.scalar(select(AiModel).where(AiModel.model_key == "claude-opus-5-5"))
    task.model_id, task.effort = opus.id, "medium"  # type: ignore[union-attr]
    db.commit()
    gateway.complete(db, ctx, META, providers, task_key="summarise", messages=HELLO)
    assert (fake_ai.calls[-1].model_key, fake_ai.calls[-1].effort) == ("claude-opus-5-5", "medium")


def test_unknown_tasks_are_rejected(db: Session, studio: Studio, fake_ai: FakeProvider) -> None:
    _enable(db, studio)
    with pytest.raises(ProblemError) as caught:
        gateway.complete(
            db,
            _context(db, studio, Role.OWNER),
            META,
            {"anthropic": fake_ai},
            task_key="nope",
            messages=HELLO,
        )
    assert caught.value.status == 400


@pytest.mark.parametrize("role", [Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER])
def test_only_owners_and_admins_may_use_ai_for_now(
    db: Session, studio: Studio, fake_ai: FakeProvider, role: Role
) -> None:
    _enable(db, studio)
    with pytest.raises(ProblemError) as caught:
        gateway.complete(
            db, _context(db, studio, role), META, {"anthropic": fake_ai}, task_key="classify", messages=HELLO
        )
    assert caught.value.status == 403
    assert fake_ai.calls == []


def test_requests_are_tagged_with_their_project(db: Session, studio: Studio, fake_ai: FakeProvider) -> None:
    _enable(db, studio)
    project = db.get(Project, studio.project_id)
    gateway.complete(
        db,
        _context(db, studio, Role.ADMIN),
        META,
        {"anthropic": fake_ai},
        task_key="classify",
        messages=HELLO,
        project=project,
    )
    assert _requests(db)[0].project_id == studio.project_id


# ---------------------------------------------------------------- usage, log and history


def test_usage_totals_by_model_and_task(
    owner: TestClient, db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    _enable(db, studio)
    ctx = _context(db, studio, Role.OWNER)
    gateway.complete(db, ctx, META, {"anthropic": fake_ai}, task_key="draft", messages=HELLO)
    owner.post(f"{B}/check")
    fake_ai.error = ProviderError(ProviderErrorKind.TIMEOUT, "slow")
    owner.post(f"{B}/check")

    usage = owner.get(f"{B}/usage").json()
    assert usage["totals"]["requests"] == 3
    assert (usage["totals"]["succeeded"], usage["totals"]["failed"]) == (2, 1)
    # draft on Sonnet: 12 x $2 + 4 x $10 per million; check on Haiku: $0.0000032.
    assert Decimal(usage["totals"]["cost_usd"]) == Decimal("0.000064") + Decimal("0.0000032")
    assert {row["key"]: row["requests"] for row in usage["by_task"]} == {"connection-check": 2, "draft": 1}
    assert {row["key"] for row in usage["by_model"]} == {"claude-haiku-5-5", "claude-sonnet-5-5"}

    assert owner.get(f"{B}/usage", params={"month": "2020-01"}).json()["totals"]["requests"] == 0
    assert owner.get(f"{B}/usage", params={"month": "2026-13"}).status_code == 400


def test_request_log_is_paginated_newest_first(owner: TestClient, db: Session, studio: Studio) -> None:
    _enable(db, studio)
    for _ in range(3):
        owner.post(f"{B}/check")
    first = owner.get(f"{B}/requests", params={"limit": 2}).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = owner.get(f"{B}/requests", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert len(second["items"]) == 1
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == [str(r.id) for r in reversed(_requests(db))]


def test_the_request_log_is_append_only(owner: TestClient, db: Session) -> None:
    owner.post(f"{B}/check")  # blocked, but logged
    row_id = _requests(db)[0].id
    for statement in (
        "UPDATE ai_requests SET cost_usd = 99 WHERE id = :id",
        "DELETE FROM ai_requests WHERE id = :id",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement), {"id": row_id})
        db.rollback()


def test_other_workspaces_cannot_see_this_workspaces_ai(
    db: Session, studio: Studio, signed_in: SignedIn
) -> None:
    outsider = signed_in(studio.outsider)
    assert outsider.get(f"{B}/usage").status_code == 404
    assert outsider.get("/api/v1/w/other-studio/ai/requests").json()["items"] == []


def test_catalog_lists_models_prices_tiers_and_tasks(owner: TestClient) -> None:
    catalog = owner.get(f"{B}/catalog").json()
    models = {m["model_key"]: m for m in catalog["models"]}
    assert set(models) == {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"}
    assert len(models["claude-haiku-5-5"]["price_bands"]) == 2
    assert [t["tier"] for t in catalog["tiers"]] == ["routine", "standard", "deep"]
    tasks = {t["task_key"]: t for t in catalog["tasks"]}
    assert tasks["review"]["model_key"] == "claude-opus-5-5"
    assert tasks["connection-check"]["max_tokens"] == 1024


def test_gateway_log_survives_a_rolled_back_caller(
    db: Session, studio: Studio, fake_ai: FakeProvider
) -> None:
    ctx = _context(db, studio, Role.OWNER)  # AI is off, so the request is blocked
    with pytest.raises(ProblemError):
        gateway.complete(db, ctx, META, {"anthropic": fake_ai}, task_key="classify", messages=HELLO)
    db.rollback()
    assert [r.error_code for r in _requests(db)] == ["ai_disabled"]
    assert isinstance(_requests(db)[0].id, uuid.UUID)
