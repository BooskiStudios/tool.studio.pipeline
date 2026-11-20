"""Agent tools (PR 3.5): the registry, tool calls inside steps, permissions, limits, the tool-call log, and
proposed changes applied only when a person approves the run's review. Fake AI only."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from ai_fakes import FakeProvider, prompt_of
from booski_core.access.roles import Role
from booski_core.models import ActivityEvent, Decision, Document, DocumentRevision, Membership, Task
from booski_core.modules.agents import worker
from booski_core.modules.agents.models import AgentToolCall
from booski_core.modules.ai.models import WorkspaceAiSettings
from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import AiCall, AiResult, AssistantTurn, ToolCall, ToolResultsTurn
from booski_core.modules.tools.registry import FORBIDDEN_ACTIONS, TOOLS
from studio import Studio, build_studio

pytestmark = pytest.mark.db

B = "/api/v1/w/booski"
SignedIn = Callable[..., TestClient]
ONE_STEP = {"steps": [{"title": "Plan the alpha", "instruction": "Plan it.", "agent": "producer"}]}


def _text(value: str) -> AiResult:
    return AiResult(text=value, stop_reason="end_turn", usage=TokenUsage(input_tokens=50, output_tokens=20))


def tool_script(
    rounds: list[list[tuple[str, dict[str, Any]]]], final: str = "Step done."
) -> Callable[[AiCall], AiResult]:
    """Plans one step; in that step, asks for each round of tool calls in turn, then answers ``final``."""
    state = {"round": 0, "id": 0}

    def respond(call: AiCall) -> AiResult:
        prompt = prompt_of(call)
        if "Make a short plan" in prompt:
            return _text(json.dumps(ONE_STEP))
        if state["round"] < len(rounds):
            calls = []
            for name, args in rounds[state["round"]]:
                state["id"] += 1
                calls.append(ToolCall(id=f"call_{state['id']}", name=name, input=args))
            state["round"] += 1
            return AiResult(
                text="",
                stop_reason="tool_use",
                usage=TokenUsage(input_tokens=50, output_tokens=20),
                tool_calls=tuple(calls),
                assistant_turn=AssistantTurn(raw=[{"type": "text", "text": "Let me check."}]),
            )
        return _text(final)

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


@pytest.fixture
def work(sessions: sessionmaker[Session], fake_ai: FakeProvider) -> Callable[[], None]:
    def go() -> None:
        while worker.run_once(sessions, {"anthropic": fake_ai}, worker="test", sleep=lambda _: None):
            pass

    return go


def _start(client: TestClient, agent: str = "producer", **extra: Any) -> str:
    response = client.post(f"{B}/agent-runs", json={"agent": agent, "goal": "Plan the alpha", **extra})
    assert response.status_code == 201, response.text
    run_id: str = response.json()["id"]
    return run_id


def _calls(client: TestClient, run_id: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = client.get(f"{B}/agent-runs/{run_id}/tool-calls").json()
    return calls


def _changes(client: TestClient, run_id: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = client.get(f"{B}/agent-runs/{run_id}/changes").json()
    return changes


def _tool_results(call: AiCall) -> list[str]:
    turns = [m for m in call.messages if isinstance(m, ToolResultsTurn)]
    return [r.content for r in turns[-1].results] if turns else []


TASKS = {
    "project": "horizon",
    "tasks": [
        {"title": "Combat prototype", "priority": "high"},
        {"title": "Enemy AI pass", "description": "Basic"},
    ],
}
DOC = {"kind": "design_doc", "title": "Alpha scope", "summary": "What's in", "body": "# Alpha\nCombat only."}


# ---------------------------------------------------------------- the registry


def test_no_tool_can_edit_delete_or_act_outside_booski(owner: TestClient) -> None:
    assert {t.kind for t in TOOLS.values()} == {"read", "propose"}
    for name in TOOLS:
        assert not name.startswith(FORBIDDEN_ACTIONS), name
    listed = {t["name"]: t for t in owner.get(f"{B}/tools").json()}
    assert set(listed) == set(TOOLS)
    assert listed["create_tasks"]["kind"] == "propose"
    assert listed["get_document"]["input_schema"]["type"] == "object"


# ---------------------------------------------------------------- a run with tools


def test_reads_and_proposals_flow_through_review(
    developer: TestClient,
    owner: TestClient,
    studio: Studio,
    db: Session,
    fake_ai: FakeProvider,
    work: Callable[[], None],
) -> None:
    fake_ai.responder = tool_script(
        [
            [("list_projects", {}), ("search_knowledge", {"query": "controller design"})],
            [("create_tasks", TASKS), ("create_document", DOC)],
        ],
        final="Proposed two tasks and a scope document.",
    )
    run_id = _start(developer)
    work()

    run = developer.get(f"{B}/agent-runs/{run_id}").json()
    assert run["status"] == "succeeded" and run["tool_calls_used"] == 4
    # The step's tools were offered to the model, and the results went back in one turn per round.
    step_calls = [c for c in fake_ai.calls if c.tools]
    assert {t.name for t in step_calls[0].tools} == set(TOOLS)  # the Producer has every tool
    assert any("horizon: Project Horizon" in r for r in _tool_results(step_calls[1]))
    assert all("applied only if a person approves" in r for r in _tool_results(step_calls[2]))

    calls = _calls(developer, run_id)
    assert [(c["tool"], c["status"], c["kind"]) for c in calls] == [
        ("list_projects", "succeeded", "read"),
        ("search_knowledge", "succeeded", "read"),
        ("create_tasks", "succeeded", "propose"),
        ("create_document", "succeeded", "propose"),
    ]
    changes = _changes(developer, run_id)
    assert [(c["seq"], c["tool"], c["status"]) for c in changes] == [
        (1, "create_tasks", "proposed"),
        (2, "create_document", "proposed"),
    ]

    # Nothing has been written yet.
    assert db.scalar(select(func.count()).select_from(Task).where(Task.title == "Combat prototype")) == 0
    approval = owner.get(f"{B}/approvals/{run['approval_id']}").json()
    assert (
        "## Proposed changes" in approval["description"]
        and "Create 2 task(s) in Project Horizon" in approval["description"]
    )

    assert (
        owner.post(f"{B}/approvals/{run['approval_id']}/reviews", json={"action": "approve"}).status_code
        == 201
    )
    db.expire_all()
    tasks = db.scalars(select(Task).where(Task.title.in_(["Combat prototype", "Enemy AI pass"]))).all()
    assert len(tasks) == 2 and {t.created_by_user_id for t in tasks} == {studio.members[Role.DEVELOPER].id}
    assert all(t.project_id == studio.project_id for t in tasks)
    document = db.scalars(select(Document).where(Document.title == "Alpha scope")).one()
    assert (
        db.scalars(select(DocumentRevision.body).where(DocumentRevision.document_id == document.id)).one()
        == "# Alpha\nCombat only."
    )
    assert [c["status"] for c in _changes(developer, run_id)] == ["applied", "applied"]
    assert len(_changes(developer, run_id)[0]["applied_ids"]) == 2
    events = [e["type"] for e in developer.get(f"{B}/agent-runs/{run_id}/events").json()]
    assert events[-1] == "changes_applied"
    assert (
        db.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.verb == "task.created"))
        == 2
    )


def test_rejecting_the_review_applies_nothing(
    developer: TestClient, owner: TestClient, db: Session, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    fake_ai.responder = tool_script(
        [[("propose_decision", {"title": "Cut co-op", "outcome": "Single player only"})]]
    )
    run_id = _start(developer)
    work()
    approval_id = developer.get(f"{B}/agent-runs/{run_id}").json()["approval_id"]
    owner.post(f"{B}/approvals/{approval_id}/reviews", json={"action": "reject", "comment": "Not yet"})
    assert [c["status"] for c in _changes(developer, run_id)] == ["rejected"]
    assert db.scalar(select(func.count()).select_from(Decision).where(Decision.title == "Cut co-op")) == 0


def test_approval_rechecks_permissions_and_applies_all_or_nothing(
    developer: TestClient,
    owner: TestClient,
    studio: Studio,
    db: Session,
    fake_ai: FakeProvider,
    work: Callable[[], None],
) -> None:
    fake_ai.responder = tool_script([[("create_document", DOC), ("create_tasks", TASKS)]])
    run_id = _start(developer)
    work()
    # The developer is made a collaborator before review: they may still create tasks, but not documents.
    membership = db.scalars(
        select(Membership).where(
            Membership.workspace_id == studio.workspace_id,
            Membership.user_id == studio.members[Role.DEVELOPER].id,
        )
    ).one()
    membership.role = "collaborator"
    db.commit()
    approval_id = developer.get(f"{B}/agent-runs/{run_id}").json()["approval_id"]
    assert owner.post(f"{B}/approvals/{approval_id}/reviews", json={"action": "approve"}).status_code == 201
    changes = _changes(owner, run_id)
    assert [c["status"] for c in changes] == ["failed", "failed"]
    assert "allow" in (changes[0]["error"] or "")
    db.expire_all()
    assert (
        db.scalar(select(func.count()).select_from(Task).where(Task.title == "Combat prototype")) == 0
    )  # all or nothing


# ---------------------------------------------------------------- permissions, validation and limits


def test_tools_run_with_the_starters_permissions(
    db: Session, signed_in: SignedIn, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    s = build_studio(db, project_visibility="restricted")
    db.add(WorkspaceAiSettings(workspace_id=s.workspace_id, enabled=True))
    db.commit()
    developer = signed_in(s.members[Role.DEVELOPER])
    fake_ai.responder = tool_script(
        [[("list_tasks", {"project": "horizon"}), ("search_knowledge", {"query": "controller"})]]
    )
    run_id = _start(developer)
    work()
    calls = _calls(developer, run_id)
    assert (calls[0]["status"], calls[0]["error"]) == ("denied", "Project not found.")
    assert (
        "Controller design" not in calls[1]["result_preview"]
    )  # the restricted project's document stays hidden


@pytest.mark.parametrize(
    ("tool", "args", "status", "message"),
    [
        ("delete_everything", {}, "denied", "isn't available"),
        ("get_task", {"id": "not-a-uuid"}, "failed", "Invalid input"),
        ("create_tasks", {"project": "horizon", "tasks": []}, "failed", "Invalid input"),
        ("get_document", {"id": "00000000-0000-7000-8000-000000000000"}, "denied", "not found"),
    ],
)
def test_bad_tool_calls_return_errors_to_the_model(
    developer: TestClient,
    fake_ai: FakeProvider,
    work: Callable[[], None],
    tool: str,
    args: dict[str, Any],
    status: str,
    message: str,
) -> None:
    fake_ai.responder = tool_script([[(tool, args)]])
    run_id = _start(developer)
    work()
    [call] = _calls(developer, run_id)
    assert call["status"] == status and message in call["result_preview"]
    assert developer.get(f"{B}/agent-runs/{run_id}").json()["status"] == "succeeded"  # the run carries on


def test_tool_call_limits(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    owner.patch(f"{B}/agents/producer", json={"max_tool_calls_per_step": 2, "max_changes_per_run": 3})
    fake_ai.responder = tool_script(
        [
            [("list_projects", {}), ("list_projects", {}), ("list_projects", {})],
            [("create_tasks", {"project": "horizon", "tasks": [{"title": f"T{i}"} for i in range(5)]})],
        ]
    )
    run_id = _start(developer)
    work()
    statuses = [c["status"] for c in _calls(developer, run_id)]
    assert statuses == ["succeeded", "succeeded", "limit_reached", "limit_reached"]
    assert _changes(developer, run_id) == []


def test_the_change_limit_counts_records(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    owner.patch(f"{B}/agents/producer", json={"max_changes_per_run": 3})
    fake_ai.responder = tool_script(
        [[("create_tasks", {"project": "horizon", "tasks": [{"title": f"T{i}"} for i in range(4)]})]]
    )
    run_id = _start(developer)
    work()
    assert _calls(developer, run_id)[0]["status"] == "limit_reached"


def test_assist_agents_only_get_read_tools(
    owner: TestClient, developer: TestClient, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    owner.patch(f"{B}/agents/qa-lead", json={"autonomy": "assist"})
    fake_ai.responder = tool_script([[("create_document", DOC)]])
    run_id = _start(developer, agent="qa-lead")
    work()
    offered = {t.name for c in fake_ai.calls if c.tools for t in c.tools}
    assert offered and all(TOOLS[name].kind == "read" for name in offered)
    assert _calls(developer, run_id)[0]["status"] == "denied"


def test_long_reads_are_shortened(
    developer: TestClient, studio: Studio, db: Session, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    document = db.get(Document, studio.document_id)
    assert document is not None
    db.add(
        DocumentRevision(
            workspace_id=studio.workspace_id,
            document_id=document.id,
            revision_no=2,
            title=document.title,
            body="word " * 10_000,
        )
    )
    document.current_revision = 2
    db.commit()
    fake_ai.responder = tool_script([[("get_document", {"id": str(studio.document_id)})]])
    _start(developer)
    work()
    step_calls = [c for c in fake_ai.calls if c.tools]
    [result] = _tool_results(step_calls[1])
    assert "shortened" in result and len(result) < 13_000


# ---------------------------------------------------------------- lifecycle and history


def test_cancelled_runs_discard_their_proposals(
    developer: TestClient, sessions: sessionmaker[Session], fake_ai: FakeProvider
) -> None:
    run_id = _start(developer)

    def respond_then_cancel(call: AiCall) -> AiResult:
        if call.tools and not any(isinstance(m, ToolResultsTurn) for m in call.messages):
            return AiResult(
                text="",
                stop_reason="tool_use",
                tool_calls=(ToolCall(id="c1", name="create_document", input=DOC),),
                assistant_turn=AssistantTurn(raw=[]),
            )
        if call.tools:
            developer.post(f"{B}/agent-runs/{run_id}/cancel")
        return tool_script([])(call)

    fake_ai.responder = respond_then_cancel
    worker.run_once(sessions, {"anthropic": fake_ai}, worker="test", sleep=lambda _: None)
    assert developer.get(f"{B}/agent-runs/{run_id}").json()["status"] == "cancelled"
    assert [c["status"] for c in _changes(developer, run_id)] == ["discarded"]


def test_the_tool_call_log_is_append_only(
    developer: TestClient, db: Session, fake_ai: FakeProvider, work: Callable[[], None]
) -> None:
    fake_ai.responder = tool_script([[("list_projects", {})]])
    _start(developer)
    work()
    call_id = db.scalars(select(AgentToolCall.id)).first()
    for statement in (
        "UPDATE agent_tool_calls SET status = 'failed' WHERE id = :id",
        "DELETE FROM agent_tool_calls WHERE id = :id",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement), {"id": call_id})
        db.rollback()


def test_agents_can_only_be_given_known_tools(owner: TestClient) -> None:
    assert owner.patch(f"{B}/agents/qa-lead", json={"tools": ["launch_missiles"]}).status_code == 422
    agent = owner.patch(f"{B}/agents/qa-lead", json={"tools": ["list_tasks", "list_tasks"]}).json()
    assert agent["tools"] == ["list_tasks"]
