"""Agents and agent runs (PR 3.4): configuration, the orchestrator and worker, human control, limits,
retries, recovery and permissions. AI calls go to a scripted fake provider: no test calls a real one."""

import json
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from ai_fakes import FakeProvider, prompt_of
from booski_core.access.roles import Role
from booski_core.core.request_meta import utcnow
from booski_core.models import Approval, Membership
from booski_core.modules.agents import worker
from booski_core.modules.agents.models import Agent, AgentRun, AgentRunEvent
from booski_core.modules.ai.models import AiRequest, WorkspaceAiSettings
from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import AiCall, AiResult, ProviderError, ProviderErrorKind
from studio import Studio, build_studio

pytestmark = pytest.mark.db

B = "/api/v1/w/booski"
SignedIn = Callable[..., TestClient]
TWO_STEP_PLAN = {
    "steps": [
        {"title": "List the milestones", "instruction": "Outline the alpha milestones.", "agent": "producer"},
        {
            "title": "Draft the combat design",
            "instruction": "Draft the core combat loop.",
            "agent": "game-designer",
        },
    ]
}


def _result(text_: str, *, input_tokens: int = 100, output_tokens: int = 50) -> AiResult:
    return AiResult(
        text=text_,
        stop_reason="end_turn",
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def scripted(plan: dict[str, Any] | str = TWO_STEP_PLAN) -> Callable[[AiCall], AiResult]:
    """Answers planning prompts with ``plan``, steps with "Result of step N", and the final call."""

    def respond(call: AiCall) -> AiResult:
        prompt = prompt_of(call)
        if "Make a short plan" in prompt:
            return _result(plan if isinstance(plan, str) else json.dumps(plan))
        if "Combine these into the final deliverable" in prompt:
            return _result("# Alpha plan\nFinal deliverable.")
        step = prompt.split("Do step ", 1)[1].split(" ", 1)[0]
        return _result(f"Result of step {step}")

    return respond


@pytest.fixture
def studio(db: Session) -> Studio:
    s = build_studio(db)
    db.add(WorkspaceAiSettings(workspace_id=s.workspace_id, enabled=True))
    db.commit()
    return s


@pytest.fixture
def sessions(migrated_db: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_db, expire_on_commit=False)


@pytest.fixture
def owner(studio: Studio, signed_in: SignedIn) -> TestClient:
    return signed_in(studio.members[Role.OWNER])


@pytest.fixture
def developer(studio: Studio, signed_in: SignedIn) -> TestClient:
    return signed_in(studio.members[Role.DEVELOPER])


Work = Callable[..., Any]


@pytest.fixture
def work(sessions: sessionmaker[Session], fake_ai: FakeProvider) -> Work:
    """Runs the agent worker until the queue is empty; returns the backoff sleeps it asked for."""

    def go(name: str = "test-worker") -> list[float]:
        sleeps: list[float] = []
        while worker.run_once(sessions, {"anthropic": fake_ai}, worker=name, sleep=sleeps.append):
            pass
        return sleeps

    return go


def _start(
    client: TestClient, agent: str = "producer", goal: str = "Plan the alpha", **extra: Any
) -> dict[str, Any]:
    response = client.post(f"{B}/agent-runs", json={"agent": agent, "goal": goal, **extra})
    assert response.status_code == 201, response.text
    run: dict[str, Any] = response.json()
    return run


def _run(client: TestClient, run_id: str) -> dict[str, Any]:
    run: dict[str, Any] = client.get(f"{B}/agent-runs/{run_id}").json()
    return run


def _events(client: TestClient, run_id: str) -> list[str]:
    return [e["type"] for e in client.get(f"{B}/agent-runs/{run_id}/events").json()]


# ---------------------------------------------------------------- a full run


def test_a_run_plans_delegates_and_asks_for_review(
    developer: TestClient, owner: TestClient, studio: Studio, db: Session, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted()
    run = _start(developer)
    assert run["status"] == "queued"
    work()

    run = _run(developer, run["id"])
    assert run["status"] == "succeeded", run
    assert [s["agent"] for s in run["plan"]] == ["producer", "game-designer"]
    assert [s["output"] for s in run["plan"]] == ["Result of step 1", "Result of step 2"]
    assert run["output"] == "# Alpha plan\nFinal deliverable."
    assert run["steps_used"] == 4  # plan, two steps, final deliverable
    assert _events(developer, run["id"]) == [
        "created", "claimed", "planned", "step_started", "step_completed", "step_started", "step_completed",
        "completed", "review_requested",
    ]  # fmt: skip

    # Routing: the Producer plans on the "plan" task (Opus 5.5); the delegated design step uses the Game
    # Designer's "draft" task (Sonnet 5.5). Every call is in the AI request log, costed.
    assert [c.model_key for c in fake_ai.calls] == [
        "claude-opus-5-5", "claude-opus-5-5", "claude-sonnet-5-5", "claude-opus-5-5"
    ]  # fmt: skip
    assert "You are Producer" in (fake_ai.calls[0].system or "")
    assert "You are Game Designer" in (fake_ai.calls[2].system or "")
    assert "cannot change studio records" in (fake_ai.calls[0].system or "")
    requests = db.scalars(select(AiRequest).order_by(AiRequest.created_at)).all()
    assert [r.task_key for r in requests] == ["plan", "plan", "draft", "plan"]
    assert {r.actor_user_id for r in requests} == {studio.members[Role.DEVELOPER].id}
    assert Decimal(run["cost_usd"]) == sum(r.cost_usd for r in requests)

    # The output goes to review as an "AI output" approval, requested by the agent (no user)...
    approval = db.get(Approval, run["approval_id"])
    assert approval is not None
    assert (approval.kind, approval.requested_by_user_id, approval.status) == ("ai_output", None, "pending")
    assert approval.payload["agent_run_id"] == run["id"]
    assert approval.description == run["output"]
    # ...so even the owner who could have started it can decide it.
    review = owner.post(f"{B}/approvals/{approval.id}/reviews", json={"action": "approve"})
    assert review.status_code == 201, review.text


def test_single_step_plans_skip_the_final_call(
    developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted(
        {"steps": [{"title": "Draft", "instruction": "Write it.", "agent": "producer"}]}
    )
    run_id = _start(developer)["id"]
    work()
    run = _run(developer, run_id)
    assert (run["status"], run["output"], run["steps_used"]) == ("succeeded", "Result of step 1", 2)
    assert len(fake_ai.calls) == 2


def test_an_unusable_plan_becomes_a_single_step(
    developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted("I would start by thinking about it.")
    run_id = _start(developer)["id"]
    work()
    run = _run(developer, run_id)
    assert run["status"] == "succeeded"
    assert [s["title"] for s in run["plan"]] == ["Do the work"]


def test_delegation_is_limited_to_the_agents_allowed_colleagues(
    developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    # The Game Designer may not delegate (its delegates_to is empty), so a step it hands to someone else
    # is done by the Game Designer itself.
    plan = {"steps": [{"title": "Review", "instruction": "Review it.", "agent": "technical-director"}]}
    fake_ai.responder = scripted(plan)
    run_id = _start(developer, agent="game-designer")["id"]
    work()
    assert _run(developer, run_id)["plan"][0]["agent"] == "game-designer"
    assert all("You are Game Designer" in (c.system or "") for c in fake_ai.calls)


def test_assist_agents_answer_without_an_approval(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Work, db: Session
) -> None:
    assert owner.patch(f"{B}/agents/qa-lead", json={"autonomy": "assist"}).status_code == 200
    fake_ai.responder = scripted(
        {"steps": [{"title": "Plan tests", "instruction": "Do it.", "agent": "qa-lead"}]}
    )
    run_id = _start(developer, agent="qa-lead")["id"]
    work()
    run = _run(developer, run_id)
    assert run["status"] == "succeeded" and run["approval_id"] is None
    assert db.scalar(select(func.count()).select_from(Approval).where(Approval.kind == "ai_output")) == 0


# ---------------------------------------------------------------- human control


def test_pause_resume_and_redirect_between_steps(
    developer: TestClient, sessions: sessionmaker[Session], fake_ai: FakeProvider, work: Work
) -> None:
    run_id = _start(developer)["id"]
    base = scripted()

    def respond_and_pause_after_first_step(call: AiCall) -> AiResult:
        prompt = prompt_of(call)
        if "Do step 1" in prompt:  # a person pauses while step 1 is running
            assert developer.post(f"{B}/agent-runs/{run_id}/pause").status_code == 200
        return base(call)

    fake_ai.responder = respond_and_pause_after_first_step
    work()
    run = _run(developer, run_id)
    assert run["status"] == "paused"
    assert [s["status"] for s in run["plan"]] == ["completed", "pending"]  # step 1's work was kept

    redirected = developer.post(
        f"{B}/agent-runs/{run_id}/redirect", json={"instruction": "Keep combat melee-only."}
    )
    assert redirected.json()["notes"][0]["text"] == "Keep combat melee-only."
    assert developer.post(f"{B}/agent-runs/{run_id}/resume").json()["status"] == "queued"

    calls_before = len(fake_ai.calls)
    fake_ai.responder = base
    work()
    run = _run(developer, run_id)
    assert run["status"] == "succeeded"
    later = fake_ai.calls[calls_before:]
    assert len(later) == 2  # step 2 and the final deliverable: no re-planning, step 1 not repeated
    assert all("Keep combat melee-only." in prompt_of(c) for c in later)
    assert "paused" in _events(developer, run_id) and "redirected" in _events(developer, run_id)


def test_cancelled_and_paused_runs_are_not_picked_up(
    developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted()
    cancelled = _start(developer)["id"]
    paused = _start(developer)["id"]
    developer.post(f"{B}/agent-runs/{cancelled}/cancel")
    developer.post(f"{B}/agent-runs/{paused}/pause")
    work()
    assert fake_ai.calls == []
    assert _run(developer, cancelled)["status"] == "cancelled"
    assert developer.post(f"{B}/agent-runs/{cancelled}/resume").status_code == 409
    assert (
        developer.post(f"{B}/agent-runs/{cancelled}/redirect", json={"instruction": "x"}).status_code == 409
    )


def test_only_the_starter_or_an_admin_controls_a_run(
    developer: TestClient, signed_in: SignedIn, studio: Studio
) -> None:
    run_id = _start(developer)["id"]
    other_developer = signed_in(studio.requester)  # also a developer
    assert other_developer.post(f"{B}/agent-runs/{run_id}/pause").status_code == 403
    assert _run(other_developer, run_id)["can_control"] is False
    admin = signed_in(studio.members[Role.ADMIN])
    assert admin.post(f"{B}/agent-runs/{run_id}/pause").status_code == 200


# ---------------------------------------------------------------- limits, retries and failures


def test_transient_failures_are_retried_with_backoff(
    developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted()
    fake_ai.errors = [
        ProviderError(ProviderErrorKind.RATE_LIMITED, "busy"),
        ProviderError(ProviderErrorKind.TIMEOUT, "slow"),
    ]
    run_id = _start(developer)["id"]
    sleeps = work()
    assert _run(developer, run_id)["status"] == "succeeded"
    assert sleeps == [2.0, 4.0]
    assert _events(developer, run_id).count("step_retried") == 2


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        ("auth", "authentication_failed"),
        ("ai_off", "ai_disabled"),
        ("refusal", "refused"),
        ("persistent_timeout", "timeout"),
    ],
)
def test_failures_stop_the_run_with_a_reason(
    developer: TestClient,
    studio: Studio,
    db: Session,
    fake_ai: FakeProvider,
    work: Work,
    setup: str,
    code: str,
) -> None:
    if setup == "auth":
        fake_ai.error = ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key")
    elif setup == "ai_off":
        db.merge(WorkspaceAiSettings(workspace_id=studio.workspace_id, enabled=False))
        db.commit()
    elif setup == "refusal":
        fake_ai.result = AiResult(text="", stop_reason="refusal", refusal_category="cyber")
    else:
        fake_ai.error = ProviderError(ProviderErrorKind.TIMEOUT, "slow")
    run_id = _start(developer)["id"]
    work()
    run = _run(developer, run_id)
    assert (run["status"], run["error_code"]) == ("failed", code)
    assert _events(developer, run_id)[-1] == "failed"


def test_the_cost_limit_stops_a_run(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    owner.patch(f"{B}/agents/producer", json={"max_cost_usd": "0.01"})

    def expensive(call: AiCall) -> AiResult:
        result = scripted()(call)
        return AiResult(text=result.text, stop_reason="end_turn", usage=TokenUsage(input_tokens=10_000))

    fake_ai.responder = expensive  # $0.04 per call on Opus 5.5
    run_id = _start(developer)["id"]
    work()
    run = _run(developer, run_id)
    assert (run["status"], run["error_code"]) == ("failed", "cost_limit")
    assert len(fake_ai.calls) == 1


def test_the_step_limit_caps_the_plan(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Work
) -> None:
    owner.patch(f"{B}/agents/producer", json={"max_steps": 1})
    fake_ai.responder = scripted()
    run_id = _start(developer)["id"]
    work()
    run = _run(developer, run_id)
    assert run["status"] == "succeeded" and len(run["plan"]) == 1


# ---------------------------------------------------------------- permissions


def test_a_run_never_outlives_its_starters_permissions(
    developer: TestClient, studio: Studio, db: Session, fake_ai: FakeProvider, work: Work
) -> None:
    fake_ai.responder = scripted()
    run_id = _start(developer)["id"]
    membership = db.scalars(
        select(Membership).where(
            Membership.workspace_id == studio.workspace_id,
            Membership.user_id == studio.members[Role.DEVELOPER].id,
        )
    ).one()
    membership.role = "viewer"  # demoted after starting the run
    db.commit()
    work()
    run = _run(developer, run_id)
    assert (run["status"], run["error_code"]) == ("failed", "starter_not_allowed")
    assert fake_ai.calls == []


def test_who_may_start_runs(signed_in: SignedIn, studio: Studio) -> None:
    collaborator = signed_in(studio.members[Role.COLLABORATOR])
    assert collaborator.post(f"{B}/agent-runs", json={"agent": "producer", "goal": "x"}).status_code == 403


def test_runs_in_restricted_projects_stay_private(
    db: Session, signed_in: SignedIn, migrated_db: Engine
) -> None:
    s = build_studio(db, project_visibility="restricted")
    db.add(WorkspaceAiSettings(workspace_id=s.workspace_id, enabled=True))
    db.commit()
    owner, developer = signed_in(s.members[Role.OWNER]), signed_in(s.members[Role.DEVELOPER])
    run_id = _start(owner, project="horizon")["id"]
    assert developer.get(f"{B}/agent-runs/{run_id}").status_code == 404
    assert run_id not in [r["id"] for r in developer.get(f"{B}/agent-runs").json()["items"]]
    assert (
        developer.post(
            f"{B}/agent-runs", json={"agent": "producer", "goal": "x", "project": "horizon"}
        ).status_code
        == 404
    )


# ---------------------------------------------------------------- recovery


def test_a_crashed_workers_run_is_resumed_by_another_worker(
    developer: TestClient, sessions: sessionmaker[Session], fake_ai: FakeProvider, work: Work, db: Session
) -> None:
    fake_ai.responder = scripted()
    run_id = _start(developer)["id"]
    assert worker.claim(sessions, "crashed-worker") is not None  # claimed, then the worker "dies"
    assert (
        worker.run_once(sessions, {"anthropic": fake_ai}, worker="second-worker") is None
    )  # lease still valid
    db.execute(text("UPDATE agent_runs SET lease_expires_at = now() - interval '1 minute'"))
    db.commit()
    work("second-worker")
    run = _run(developer, run_id)
    assert (run["status"], run["attempts"]) == ("succeeded", 2)
    claimed = db.scalars(
        select(AgentRunEvent).where(AgentRunEvent.type == "claimed").order_by(AgentRunEvent.seq)
    ).all()
    assert [e.data["resumed"] for e in claimed] == [False, True]


def test_runs_that_keep_crashing_are_stopped(
    developer: TestClient, sessions: sessionmaker[Session], fake_ai: FakeProvider, db: Session
) -> None:
    run_id = _start(developer)["id"]
    db.execute(
        text(
            "UPDATE agent_runs SET status = 'running', attempts = 3, lease_owner = 'x', lease_expires_at = :t"
        ),
        {"t": utcnow() - timedelta(minutes=1)},
    )
    db.commit()
    assert worker.run_once(sessions, {"anthropic": fake_ai}, worker="w") is None
    run = _run(developer, run_id)
    assert (run["status"], run["error_code"]) == ("failed", "too_many_attempts")
    assert fake_ai.calls == []


def test_run_history_is_append_only(developer: TestClient, db: Session) -> None:
    _start(developer)
    event_id = db.scalars(select(AgentRunEvent.id)).first()
    for statement in (
        "UPDATE agent_run_events SET seq = 99 WHERE id = :id",
        "DELETE FROM agent_run_events WHERE id = :id",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement), {"id": event_id})
        db.rollback()


# ---------------------------------------------------------------- agent configuration


def test_workspaces_start_with_the_starter_agents(
    owner: TestClient, signed_in: SignedIn, studio: Studio
) -> None:
    agents = {a["key"]: a for a in owner.get(f"{B}/agents").json()}
    assert set(agents) == {"producer", "technical-director", "game-designer", "qa-lead"}
    assert agents["producer"]["delegates_to"] == ["technical-director", "game-designer", "qa-lead"]
    assert agents["producer"]["department_id"] is not None
    created = owner.post("/api/v1/workspaces", json={"name": "Side Project", "slug": "side-project"})
    assert created.status_code == 201, created.text
    assert len(owner.get("/api/v1/w/side-project/agents").json()) == 4


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"delegates_to": ["nobody"]}, 422),
        ({"delegates_to": ["producer"]}, 422),
        ({"autonomy": "controlled_autonomy"}, 422),
        ({"task_key": "no-such-task"}, 422),
        ({"max_steps": 21}, 422),
        ({"version": 99, "name": "Stale"}, 409),
    ],
)
def test_invalid_agent_changes_are_rejected(owner: TestClient, body: dict[str, Any], status: int) -> None:
    assert owner.patch(f"{B}/agents/producer", json=body).status_code == status


def test_switched_off_agents_cannot_be_started(owner: TestClient, developer: TestClient) -> None:
    owner.patch(f"{B}/agents/producer", json={"is_active": False})
    assert developer.post(f"{B}/agent-runs", json={"agent": "producer", "goal": "x"}).status_code == 409
    assert "producer" not in [a["key"] for a in owner.get(f"{B}/agents").json()]


def test_switching_an_agent_off_stops_its_queued_runs(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Work, db: Session
) -> None:
    run_id = _start(developer)["id"]
    agent = db.scalars(select(Agent).where(Agent.key == "producer")).first()
    assert agent is not None
    owner.patch(f"{B}/agents/producer", json={"is_active": False})
    work()
    assert _run(developer, run_id)["error_code"] == "agent_inactive"
    assert db.get(AgentRun, run_id) is not None
