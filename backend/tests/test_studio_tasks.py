"""Tasks: creation rules, links that must stay inside the workspace and project, collaborators, subtasks,
filtering and pagination, comments and history."""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.models import Task
from helpers import Account
from studio import Studio, build_studio

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]
B = "/api/v1/w/booski"


@pytest.fixture
def studio(db: Session) -> Studio:
    return build_studio(db)


def _task(client: TestClient, **body: object) -> dict[str, object]:
    response = client.post(
        f"{B}/tasks",
        json={"title": "A task", **{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in body.items()}},
    )
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


def test_create_task_with_full_structure(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    task = _task(
        developer,
        title="Tune sprint stamina",
        project_id=studio.project_id,
        workstream_id=studio.workstream_id,
        milestone_id=studio.milestone_id,
        assignee_user_id=studio.members[Role.DEVELOPER].id,
        priority="high",
        start_date="2026-11-16",
        due_date="2026-11-20",
    )
    assert task["department_id"] == str(studio.department_id)  # taken from the workstream
    assert task["created_by_user_id"] == str(studio.members[Role.DEVELOPER].id)
    assert task["can_edit"] is True
    assert task["position"] == 2.0  # after the existing task


def test_completing_and_reopening_sets_completed_at(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    done = owner.patch(f"{B}/tasks/{studio.task_id}", json={"status": "done"}).json()
    assert done["completed_at"] is not None
    reopened = owner.patch(f"{B}/tasks/{studio.task_id}", json={"status": "in_progress"}).json()
    assert reopened["completed_at"] is None


def test_links_must_stay_inside_the_workspace_and_project(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    owner = signed_in(studio.members[Role.OWNER])

    def post(**body: object) -> int:
        payload = {"title": "x", **{k: str(v) for k, v in body.items()}}
        return owner.post(f"{B}/tasks", json=payload).status_code

    assert post(project_id=studio.other_project_id) == 404
    assert post(department_id=studio.other_department_id) == 404
    assert post(parent_task_id=studio.other_task_id) == 422
    assert post(assignee_user_id=studio.outsider.id) == 422
    assert post(workstream_id=studio.workstream_id) == 422  # no project
    assert post(milestone_id=studio.milestone_id) == 422  # no project
    other = owner.post(f"{B}/projects", json={"slug": "second", "name": "Second"}).json()
    assert post(project_id=other["id"], workstream_id=studio.workstream_id) == 422
    assert post(project_id=other["id"], milestone_id=studio.milestone_id) == 422
    assert post(project_id=other["id"], parent_task_id=studio.task_id) == 422  # parent in another project
    assert post(project_id=studio.project_id, start_date="2026-12-02", due_date="2026-12-01") == 422


def test_database_rejects_cross_workspace_links_even_without_the_api(studio: Studio, db: Session) -> None:
    db.add(Task(workspace_id=studio.workspace_id, project_id=studio.other_project_id, title="Smuggled"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(Task(workspace_id=studio.workspace_id, assignee_user_id=studio.outsider.id, title="Smuggled"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_collaborators_edit_only_their_own_or_assigned_tasks(signed_in: SignedIn, studio: Studio) -> None:
    collaborator_account = studio.members[Role.COLLABORATOR]
    collaborator = signed_in(collaborator_account)
    mine = _task(collaborator, project_id=studio.project_id)
    assert collaborator.patch(f"{B}/tasks/{mine['id']}", json={"status": "done"}).status_code == 200
    assert collaborator.patch(f"{B}/tasks/{studio.task_id}", json={"status": "done"}).status_code == 403
    # Collaborators may assign to themselves, not to others.
    assert (
        collaborator.patch(
            f"{B}/tasks/{mine['id']}", json={"assignee_user_id": str(studio.target.id)}
        ).status_code
        == 403
    )
    assert (
        collaborator.patch(
            f"{B}/tasks/{mine['id']}", json={"assignee_user_id": str(collaborator_account.id)}
        ).status_code
        == 200
    )
    # Once assigned someone else's task, they can work on it.
    owner = signed_in(studio.members[Role.OWNER])
    owner.patch(f"{B}/tasks/{studio.task_id}", json={"assignee_user_id": str(collaborator_account.id)})
    assert collaborator.patch(f"{B}/tasks/{studio.task_id}", json={"status": "in_review"}).status_code == 200
    assert collaborator.get(f"{B}/tasks/{studio.task_id}").json()["can_edit"] is True


def test_restricted_project_assignees_must_be_on_the_access_list(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    owner.patch(f"{B}/projects/horizon", json={"visibility": "restricted"})
    blocked = owner.patch(
        f"{B}/tasks/{studio.task_id}", json={"assignee_user_id": str(studio.members[Role.DEVELOPER].id)}
    )
    assert blocked.status_code == 422
    allowed = owner.patch(f"{B}/tasks/{studio.task_id}", json={"assignee_user_id": str(studio.target.id)})
    assert allowed.status_code == 200


def test_subtasks_cannot_form_loops(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    child = _task(owner, project_id=studio.project_id, parent_task_id=studio.task_id)
    grandchild = _task(owner, project_id=studio.project_id, parent_task_id=child["id"])
    assert (
        owner.patch(f"{B}/tasks/{studio.task_id}", json={"parent_task_id": grandchild["id"]}).status_code
        == 422
    )
    assert (
        owner.patch(f"{B}/tasks/{studio.task_id}", json={"parent_task_id": str(studio.task_id)}).status_code
        == 422
    )
    children = owner.get(f"{B}/tasks?parent={studio.task_id}").json()["items"]
    assert [c["id"] for c in children] == [child["id"]]
    top_level = owner.get(f"{B}/tasks?parent=none").json()["items"]
    assert [t["id"] for t in top_level] == [str(studio.task_id)]


def test_subtask_depth_is_limited(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    parent = str(studio.task_id)
    for _ in range(4):
        parent = str(_task(owner, project_id=studio.project_id, parent_task_id=parent)["id"])
    too_deep = owner.post(
        f"{B}/tasks", json={"title": "x", "project_id": str(studio.project_id), "parent_task_id": parent}
    )
    assert too_deep.status_code == 422


def test_filtering_sorting_and_pagination(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    me = studio.members[Role.OWNER].id
    _task(owner, title="Due later", due_date="2026-12-20", assignee_user_id=me, priority="low")
    _task(owner, title="Due sooner", due_date="2026-12-01", priority="high")
    _task(owner, title="Blocked one", status="blocked")
    _task(owner, title="Archived one").get("id")
    archived = _task(owner, title="To archive")
    owner.patch(f"{B}/tasks/{archived['id']}", json={"archived": True})

    def titles(query: str) -> list[str]:
        return [t["title"] for t in owner.get(f"{B}/tasks?{query}").json()["items"]]

    assert titles("sort=due_date")[:2] == ["Due sooner", "Due later"]  # undated tasks come last
    assert titles("assignee=me") == ["Due later"]
    assert titles("status=blocked") == ["Blocked one"]
    assert titles("priority=high&sort=priority") == ["Due sooner"]
    assert titles("q=sooner") == ["Due sooner"]
    assert titles("archived=true") == ["To archive"]
    assert titles("project=horizon") == ["Build the FPS controller"]
    assert titles("department=game-development") == ["Build the FPS controller"]

    seen: list[str] = []
    cursor = None
    while True:
        page = owner.get(f"{B}/tasks?limit=2" + (f"&cursor={cursor}" if cursor else "")).json()
        seen += [t["title"] for t in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 and len(set(seen)) == 5  # every live task exactly once


def test_comments_and_history(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    comment = developer.post(f"{B}/tasks/{studio.task_id}/comments", json={"body": "On it"}).json()
    assert (
        developer.patch(f"{B}/comments/{comment['id']}", json={"body": "On it now"}).json()["edited_at"]
        is not None
    )
    assert (
        signed_in(studio.members[Role.VIEWER])
        .post(f"{B}/tasks/{studio.task_id}/comments", json={"body": "x"})
        .status_code
        == 403
    )
    assert developer.patch(f"{B}/comments/{studio.comment_id}", json={"body": "hijack"}).status_code == 403
    assert developer.delete(f"{B}/comments/{comment['id']}").status_code == 204
    comments = developer.get(f"{B}/tasks/{studio.task_id}/comments").json()["items"]
    assert [(c["body"], c["deleted"]) for c in comments] == [("Looks good", False), ("", True)]

    developer.patch(f"{B}/tasks/{studio.task_id}", json={"status": "done"})
    verbs = [e["verb"] for e in developer.get(f"{B}/tasks/{studio.task_id}/history").json()["items"]]
    assert verbs == ["task.completed", "task.comment_deleted", "task.comment_edited", "task.comment_added"]


def test_agents_will_use_the_same_rules(signed_in: SignedIn, studio: Studio) -> None:
    """There is no separate privileged path: an agent acting for a viewer gets the viewer's answer."""
    viewer = signed_in(studio.members[Role.VIEWER])
    assert viewer.post(f"{B}/tasks", json={"title": "Agent-created"}).status_code == 403
