"""AI memory, permission-aware search and context assembly (PR 3.3), against a real database.

The studio's "horizon" project is **restricted**: owners and admins see it, and so does the target viewer
(who has contributor access to it); the developer, collaborator and viewer members do not.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.models import ActivityEvent, Decision, Document, DocumentRevision, Memory, ProjectMember
from studio import Studio, build_studio

pytestmark = pytest.mark.db

B = "/api/v1/w/booski"
SignedIn = Callable[..., TestClient]


@pytest.fixture
def studio(db: Session) -> Studio:
    s = build_studio(db, project_visibility="restricted")
    owner = s.members[Role.OWNER].id
    db.add_all(
        [
            Memory(
                workspace_id=s.workspace_id,
                kind="lesson",
                content="Friday playtests get the best turnout from the community.",
                created_by_user_id=owner,
            ),
            Memory(
                workspace_id=s.workspace_id,
                project_id=s.project_id,
                kind="convention",
                content="Horizon prefabs use the PF_ prefix and live in Assets/Prefabs.",
                created_by_user_id=owner,
            ),
            Decision(
                workspace_id=s.workspace_id,
                title="Target 60 fps on Steam Deck",
                outcome="Performance budget is 16 ms per frame.",
                rationale="Handheld players are a large share of the audience.",
                author_user_id=owner,
                status="accepted",
            ),
            Document(
                workspace_id=s.workspace_id,
                kind="guide",
                title="Playtest checklist",
                summary="How we run community playtests.",
                created_by_user_id=owner,
                updated_by_user_id=owner,
            ),
        ]
    )
    db.flush()
    guide = db.scalars(select(Document).where(Document.title == "Playtest checklist")).one()
    db.add(
        DocumentRevision(
            workspace_id=s.workspace_id,
            document_id=guide.id,
            revision_no=1,
            title=guide.title,
            body="Book the room. Invite testers a week ahead. Record every session.",
            created_by_user_id=owner,
        )
    )
    db.commit()
    return s


@pytest.fixture
def owner(studio: Studio, signed_in: SignedIn) -> TestClient:
    return signed_in(studio.members[Role.OWNER])


@pytest.fixture
def developer(studio: Studio, signed_in: SignedIn) -> TestClient:
    return signed_in(studio.members[Role.DEVELOPER])


def _search(client: TestClient, q: str, **params: Any) -> list[dict[str, Any]]:
    response = client.get(f"{B}/search", params={"q": q, **params})
    assert response.status_code == 200, response.text
    results: list[dict[str, Any]] = response.json()["results"]
    return results


def _titles(results: list[dict[str, Any]]) -> list[str]:
    return [r["source"]["title"] for r in results]


# ---------------------------------------------------------------- memory entries


def test_memory_lifecycle_is_recorded_with_provenance(
    developer: TestClient, studio: Studio, db: Session
) -> None:
    studio_wide_decision = db.scalars(
        select(Decision).where(Decision.title.startswith("Target 60 fps"))
    ).one()
    created = developer.post(
        f"{B}/memories",
        json={
            "kind": "preference",
            "content": "  Keep UI text short.  ",
            "source_decision_id": str(studio_wide_decision.id),
        },
    )
    assert created.status_code == 201, created.text
    memory = created.json()
    assert memory["content"] == "Keep UI text short."
    assert memory["created_by_user_id"] == str(studio.members[Role.DEVELOPER].id)
    assert memory["source_decision_id"] == str(studio_wide_decision.id)
    assert memory["can_edit"] is True

    stale = developer.patch(f"{B}/memories/{memory['id']}", json={"content": "x", "version": 99})
    assert stale.status_code == 409

    updated = developer.patch(
        f"{B}/memories/{memory['id']}", json={"content": "Keep UI text very short.", "version": 1}
    ).json()
    assert updated["version"] == 2
    archived = developer.patch(f"{B}/memories/{memory['id']}", json={"archived": True}).json()
    assert archived["archived_at"] is not None

    verbs = [e["verb"] for e in developer.get(f"{B}/memories/{memory['id']}/history").json()["items"]]
    assert verbs == ["memory.archived", "memory.updated", "memory.created"]
    event = db.scalars(select(ActivityEvent).where(ActivityEvent.verb == "memory.updated")).one()
    assert event.changes["content"]["to"] == "Keep UI text very short."

    listed = developer.get(f"{B}/memories").json()["items"]
    assert memory["id"] not in [m["id"] for m in listed]  # archived entries are hidden by default
    assert memory["id"] in [
        m["id"] for m in developer.get(f"{B}/memories", params={"archived": True}).json()["items"]
    ]


def test_the_restricted_decision_cannot_be_cited_by_someone_who_cannot_see_it(
    developer: TestClient, studio: Studio
) -> None:
    # The studio's decision belongs to the restricted project, which the developer can't see.
    response = developer.post(
        f"{B}/memories",
        json={"kind": "fact", "content": "Unity it is.", "source_decision_id": str(studio.decision_id)},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "fact", "content": ""},
        {"kind": "rumour", "content": "x"},
        {"kind": "fact", "content": "x" * 2001},
    ],
)
def test_invalid_memories_are_rejected(developer: TestClient, body: dict[str, object]) -> None:
    assert developer.post(f"{B}/memories", json=body).status_code == 422


def test_project_memory_needs_write_access_to_that_project(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    body = {"kind": "fact", "content": "Horizon ships in spring.", "project_id": str(studio.project_id)}
    assert developer.post(f"{B}/memories", json=body).status_code == 404  # can't see the restricted project
    db.add(
        ProjectMember(
            project_id=studio.project_id,
            user_id=studio.members[Role.DEVELOPER].id,
            workspace_id=studio.workspace_id,
            access="viewer",
        )
    )
    db.commit()
    assert developer.post(f"{B}/memories", json=body).status_code == 403  # read-only project access


# ---------------------------------------------------------------- search


def test_search_spans_memory_documents_and_decisions_with_sources(owner: TestClient) -> None:
    results = _search(owner, "playtesting")  # stemming: matches "playtests" and "playtest"
    types = {r["source"]["type"] for r in results}
    assert types == {"memory", "document"}
    document = next(r for r in results if r["source"]["type"] == "document")
    assert document["source"]["revision"] == 1
    assert document["source"]["path"].endswith(f"/documents/{document['source']['id']}/revisions/1")
    assert document["source"]["kind"] == "guide"
    memory = next(r for r in results if r["source"]["type"] == "memory")
    assert memory["source"]["path"].startswith(f"{B}/memories/")
    assert memory["source"]["kind"] == "lesson"

    decision = _search(owner, "frame budget handheld")[0]
    assert decision["source"]["type"] == "decision"
    assert decision["source"]["status"] == "accepted"
    assert "«" in decision["snippet"]


def test_search_only_returns_what_the_caller_can_see(
    owner: TestClient, developer: TestClient, signed_in: SignedIn, studio: Studio
) -> None:
    # The restricted project's memory, document ("Controller design") and decision ("Use Unity").
    for query in ("prefabs", "controller", "unity"):
        assert _search(owner, query), query
        assert _search(developer, query) == [], query
    # The target viewer has access to the restricted project, so they see it.
    target = signed_in(studio.target)
    assert _titles(_search(target, "prefabs")) == [
        "Convention: Horizon prefabs use the PF_ prefix and live in Assets/Prefabs."
    ]


def test_other_workspaces_are_never_searched(signed_in: SignedIn, studio: Studio) -> None:
    rival = signed_in(studio.outsider)
    assert rival.get(f"{B}/search", params={"q": "playtests"}).status_code == 404
    assert rival.get("/api/v1/w/other-studio/search", params={"q": "playtests"}).json()["results"] == []


def test_archived_and_superseded_text_is_not_returned(owner: TestClient, studio: Studio, db: Session) -> None:
    memory = db.scalars(select(Memory).where(Memory.kind == "lesson")).one()
    owner.patch(f"{B}/memories/{memory.id}", json={"archived": True})
    assert "memory" not in {r["source"]["type"] for r in _search(owner, "playtests")}

    # Only the current revision of a document is searched.
    guide = db.scalars(select(Document).where(Document.title == "Playtest checklist")).one()
    owner.patch(f"{B}/documents/{guide.id}", json={"body": "Use the new booking system."})
    assert _search(owner, "invite testers") == []
    assert _titles(_search(owner, "booking system")) == ["Playtest checklist"]

    owner.patch(f"{B}/documents/{guide.id}", json={"archived": True})
    assert _search(owner, "booking system") == []


def test_project_filter_includes_studio_wide_records(owner: TestClient) -> None:
    titles = _titles(_search(owner, "prefabs OR playtests", project="horizon", type=["memory"]))
    assert len(titles) == 2  # the project's convention and the studio-wide lesson


def test_type_filter_and_limit(owner: TestClient) -> None:
    assert {r["source"]["type"] for r in _search(owner, "playtests", type=["document"])} == {"document"}
    assert len(_search(owner, "playtests OR prefabs OR unity OR controller", limit=2)) == 2
    assert owner.get(f"{B}/search", params={"q": ""}).status_code == 422


# ---------------------------------------------------------------- context assembly


def _context(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post(f"{B}/ai/context", json=body)
    assert response.status_code == 200, response.text
    context: dict[str, Any] = response.json()
    return context


def test_context_cites_every_source_and_stays_within_budget(owner: TestClient) -> None:
    context = _context(owner, query="playtests OR prefabs OR unity OR controller", budget_tokens=4000)
    assert context["items"]
    assert context["total_tokens"] <= context["budget_tokens"] == 4000
    for item in context["items"]:
        assert f"Source: {item['source']['path']}" in item["text"]
        assert item["text"] in context["rendered"]
    assert sum(i["tokens"] for i in context["items"]) == context["total_tokens"]


@pytest.mark.parametrize("budget", [100, 120, 150, 250])
def test_small_budgets_shorten_or_leave_out_items(
    owner: TestClient, studio: Studio, db: Session, budget: int
) -> None:
    db.add(
        Memory(
            workspace_id=studio.workspace_id,
            kind="fact",
            content="Playtests " + "are recorded and reviewed by the whole team every week. " * 30,
        )
    )
    db.commit()
    context = _context(owner, query="playtests", budget_tokens=budget)
    assert context["total_tokens"] <= budget
    assert context["omitted"] > 0 or any(i["truncated"] for i in context["items"])
    # The estimate is conservative: about 3 characters per token, rounded up.
    for item in context["items"]:
        assert item["tokens"] * 3 >= len(item["text"])


def test_context_is_for_ai_users_only(signed_in: SignedIn, studio: Studio) -> None:
    # Context uses the same permission-aware search; AI use is for developers and above (D50).
    owner = signed_in(studio.members[Role.OWNER])
    assert "Horizon prefabs" in _context(owner, query="prefabs")["rendered"]
    collaborator = signed_in(studio.members[Role.COLLABORATOR])
    assert collaborator.post(f"{B}/ai/context", json={"query": "prefabs"}).status_code == 403


@pytest.mark.parametrize("budget", [99, 50_001])
def test_context_budget_limits(owner: TestClient, budget: int) -> None:
    assert owner.post(f"{B}/ai/context", json={"query": "x", "budget_tokens": budget}).status_code == 422


def test_existing_records_are_searchable_without_any_extra_step(
    owner: TestClient, studio: Studio, db: Session
) -> None:
    # The search columns are generated by PostgreSQL, so rows written by any code path are indexed at once.
    db.add(Decision(workspace_id=studio.workspace_id, title="Ship a demo for Next Fest", author_user_id=None))
    db.commit()
    assert _titles(_search(owner, "next fest demo")) == ["Ship a demo for Next Fest"]
