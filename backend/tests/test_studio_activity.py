"""The activity feed: events from every module, filtering, pagination and visibility."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.models import ActivityEvent
from helpers import Account
from studio import Studio, build_studio

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]
B = "/api/v1/w/booski"


@pytest.fixture
def studio(db: Session) -> Studio:
    return build_studio(db)


def _verbs(client: TestClient, query: str = "") -> list[str]:
    return [e["verb"] for e in client.get(f"{B}/activity?{query}").json()["items"]]


def test_every_module_records_events_with_actor_workspace_and_entity(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    owner_account = studio.members[Role.OWNER]
    owner = signed_in(owner_account)
    project = owner.post(f"{B}/projects", json={"slug": "new-game", "name": "New Game"}).json()
    task = owner.post(f"{B}/tasks", json={"title": "Prototype", "project_id": project["id"]}).json()
    owner.patch(f"{B}/tasks/{task['id']}", json={"assignee_user_id": str(owner_account.id)})
    owner.patch(f"{B}/tasks/{task['id']}", json={"status": "done"})
    milestone = owner.post(f"{B}/projects/new-game/milestones", json={"name": "Alpha"}).json()
    owner.patch(f"{B}/milestones/{milestone['id']}", json={"status": "completed"})
    document = owner.post(f"{B}/documents", json={"kind": "note", "title": "Notes"}).json()
    owner.patch(f"{B}/documents/{document['id']}", json={"body": "Updated"})
    owner.post(f"{B}/decisions", json={"title": "Go"})
    approval = owner.post(f"{B}/approvals", json={"title": "Publish"}).json()
    owner.patch(f"{B}/projects/new-game", json={"archived": True})

    assert _verbs(owner) == [
        "project.archived",
        "approval.requested",
        "decision.recorded",
        "document.updated",
        "document.created",
        "milestone.completed",
        "milestone.created",
        "task.completed",
        "task.assigned",
        "task.created",
        "project.created",
    ]
    rows = db.scalars(select(ActivityEvent).where(ActivityEvent.workspace_id == studio.workspace_id)).all()
    assert all(e.actor_user_id == owner_account.id and e.entity_id is not None and e.request_id for e in rows)
    project_events = db.scalar(
        select(func.count()).select_from(ActivityEvent).where(ActivityEvent.project_id == project["id"])
    )
    # project: created + archived; task: created + assigned + completed; milestone: created + completed.
    # The document, decision and approval are studio-wide, so they carry no project.
    assert project_events == 7
    assert approval["project_id"] is None


def test_filters_and_pagination(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    for i in range(5):
        owner.post(f"{B}/tasks", json={"title": f"Task {i}", "project_id": str(studio.project_id)})
    owner.post(f"{B}/documents", json={"kind": "note", "title": "Studio note"})

    assert _verbs(owner, "entity_type=document") == ["document.created"]
    assert _verbs(owner, "verb=task.created") == ["task.created"] * 5
    assert _verbs(owner, "project=horizon") == ["task.created"] * 5
    assert _verbs(owner, f"actor={studio.members[Role.ADMIN].id}") == []

    page1 = owner.get(f"{B}/activity?limit=4").json()
    page2 = owner.get(f"{B}/activity?limit=4&cursor={page1['next_cursor']}").json()
    ids = [e["id"] for e in page1["items"] + page2["items"]]
    assert len(ids) == 6 and len(set(ids)) == 6
    assert page2["next_cursor"] is None
    assert owner.get(f"{B}/activity?since=2100-01-01T00:00:00Z").json()["items"] == []


def test_restricted_project_history_is_private(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    owner.patch(f"{B}/projects/horizon", json={"visibility": "restricted"})
    owner.post(f"{B}/tasks", json={"title": "Secret", "project_id": str(studio.project_id)})
    owner.post(f"{B}/tasks", json={"title": "Public"})
    developer = signed_in(studio.members[Role.DEVELOPER])
    summaries = [e["summary"] for e in developer.get(f"{B}/activity?entity_type=task").json()["items"]]
    assert summaries == ["Created task Public"]
    assert (
        signed_in(studio.target).get(f"{B}/activity?entity_type=task").json()["items"][0]["summary"]
        == "Created task Public"
    )
    assert len(signed_in(studio.target).get(f"{B}/activity?entity_type=task").json()["items"]) == 2


def test_invitation_events_are_for_owners_and_admins_only(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    owner.post(f"{B}/invitations", json={"email": "new.hire@example.com", "role": "developer"})
    assert "invitation.created" in _verbs(signed_in(studio.members[Role.ADMIN]))
    developer_view = signed_in(studio.members[Role.DEVELOPER]).get(f"{B}/activity").text
    assert "invitation.created" not in developer_view
    assert "new.hire@example.com" not in developer_view


def test_other_workspaces_activity_is_never_visible(signed_in: SignedIn, studio: Studio) -> None:
    outsider = signed_in(studio.outsider)
    outsider.post("/api/v1/w/other-studio/tasks", json={"title": "Rival work"})
    assert "Rival work" not in signed_in(studio.members[Role.OWNER]).get(f"{B}/activity").text
    assert outsider.get(f"{B}/activity").status_code == 404
