"""Departments, projects, project access lists, workstreams and milestones."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.models import Department, ProjectMember, Task
from helpers import Account, make_user
from studio import Studio, build_studio

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]
B = "/api/v1/w/booski"


@pytest.fixture
def studio(db: Session) -> Studio:
    return build_studio(db)


# ---------------------------------------------------------------- departments


def test_new_workspaces_get_the_seven_default_departments(signed_in: SignedIn, db: Session) -> None:
    client = signed_in(make_user(db, "ada@example.com"))
    client.post("/api/v1/workspaces", json={"name": "Ada's Studio", "slug": "ada-studio"})
    slugs = [d["slug"] for d in client.get("/api/v1/w/ada-studio/departments").json()]
    assert slugs == [
        "concept-lab",
        "game-development",
        "asset-production",
        "marketing-studio",
        "studio-operations",
        "quality-oversight",
        "post-launch-intelligence",
    ]


def test_departments_are_configurable(signed_in: SignedIn, studio: Studio) -> None:
    admin = signed_in(studio.members[Role.ADMIN])
    created = admin.post(
        f"{B}/departments", json={"slug": "Narrative", "name": "Narrative", "accent_color": "purple"}
    )
    assert created.status_code == 201 and created.json()["slug"] == "narrative"
    assert admin.post(f"{B}/departments", json={"slug": "narrative", "name": "Dup"}).status_code == 409
    renamed = admin.patch(f"{B}/departments/narrative", json={"name": "Story & Narrative", "sort_order": 5})
    assert renamed.json()["name"] == "Story & Narrative"
    assert (
        admin.patch(f"{B}/departments/narrative", json={"archived": True}).json()["archived_at"] is not None
    )
    assert "narrative" not in [d["slug"] for d in admin.get(f"{B}/departments").json()]
    assert "narrative" in [d["slug"] for d in admin.get(f"{B}/departments?include_archived=true").json()]
    assert admin.post(f"{B}/departments", json={"slug": "x", "name": "Bad slug"}).status_code == 422


def test_departments_belong_to_one_workspace(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    outsider = signed_in(studio.outsider)
    assert outsider.get("/api/v1/w/other-studio/departments/game-development").status_code == 200
    # Same slug, other workspace: separate records.
    assert (
        db.scalar(
            select(Department.id).where(
                Department.workspace_id == studio.other_workspace_id, Department.slug == "game-development"
            )
        )
        != studio.department_id
    )


# ---------------------------------------------------------------- projects


def test_create_and_read_a_project_with_computed_progress(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    created = owner.post(
        f"{B}/projects",
        json={
            "slug": "Dead-Frequency",
            "name": "Dead Frequency",
            "project_type": "Psychological Horror",
            "engine": "Unity",
            "status": "pre_production",
            "accent_color": "red",
            "cover_image_url": "https://images.example/cover.jpg",
            "properties": {"target_platform": "PC"},
        },
    )
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["slug"] == "dead-frequency"
    assert project["progress"] == {"total": 0, "done": 0, "percent": 0}
    assert "projects.manage" in project["capabilities"]

    for status in ("done", "done", "todo", "cancelled"):
        owner.post(
            f"{B}/tasks", json={"title": f"Task {status}", "project_id": project["id"], "status": status}
        )
    progress = owner.get(f"{B}/projects/dead-frequency").json()["progress"]
    assert progress == {"total": 3, "done": 2, "percent": 66}  # cancelled tasks don't count


def test_project_validation(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    assert owner.post(f"{B}/projects", json={"slug": "horizon", "name": "Duplicate"}).status_code == 409
    assert (
        owner.post(
            f"{B}/projects", json={"slug": "x2", "name": "N", "cover_image_url": "http://insecure"}
        ).status_code
        == 422
    )
    assert (
        owner.post(f"{B}/projects", json={"slug": "x3", "name": "N", "status": "shipped"}).status_code == 422
    )


def test_list_projects_filters_sorts_and_paginates(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    for i in range(5):
        owner.post(f"{B}/projects", json={"slug": f"game-{i}", "name": f"Game {i}", "status": "concept"})
    owner.patch(f"{B}/projects/game-4", json={"archived": True})

    page1 = owner.get(f"{B}/projects?sort=name&limit=3").json()
    assert [p["name"] for p in page1["items"]] == ["Game 0", "Game 1", "Game 2"]
    page2 = owner.get(f"{B}/projects?sort=name&limit=3&cursor={page1['next_cursor']}").json()
    assert [p["name"] for p in page2["items"]] == ["Game 3", "Project Horizon"]
    assert page2["next_cursor"] is None
    assert [p["slug"] for p in owner.get(f"{B}/projects?archived=true").json()["items"]] == ["game-4"]
    assert [p["slug"] for p in owner.get(f"{B}/projects?status=prototype").json()["items"]] == ["horizon"]
    assert [p["slug"] for p in owner.get(f"{B}/projects?q=horiz").json()["items"]] == ["horizon"]
    assert owner.get(f"{B}/projects?cursor=not-a-cursor").status_code == 400
    assert owner.get(f"{B}/projects?limit=500").status_code == 422


def test_concurrent_edits_are_detected(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    version = owner.get(f"{B}/projects/horizon").json()["version"]
    assert (
        owner.patch(f"{B}/projects/horizon", json={"name": "Horizon", "version": version}).status_code == 200
    )
    stale = owner.patch(f"{B}/projects/horizon", json={"name": "Horizon 2", "version": version})
    assert stale.status_code == 409
    assert stale.json()["current_version"] == version + 1


def test_other_workspaces_projects_are_invisible(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    assert owner.get(f"{B}/projects/rival-game").status_code == 404
    assert "rival-game" not in [p["slug"] for p in owner.get(f"{B}/projects").json()["items"]]


# ---------------------------------------------------------------- restricted projects and access lists


def test_restricted_projects_are_hidden_from_non_members(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    owner.patch(f"{B}/projects/horizon", json={"visibility": "restricted"})
    developer = signed_in(studio.members[Role.DEVELOPER])
    assert developer.get(f"{B}/projects/horizon").status_code == 404
    assert developer.get(f"{B}/projects").json()["items"] == []
    assert developer.get(f"{B}/tasks/{studio.task_id}").status_code == 404
    assert developer.get(f"{B}/documents/{studio.document_id}").status_code == 404
    assert developer.get(f"{B}/decisions/{studio.decision_id}").status_code == 404
    assert developer.get(f"{B}/approvals/{studio.approval_id}").status_code == 404
    assert developer.get(f"{B}/milestones/{studio.milestone_id}").status_code == 404
    assert developer.get(f"{B}/tasks").json()["items"] == []
    # Admins always see everything; listed members see the project.
    assert signed_in(studio.members[Role.ADMIN]).get(f"{B}/projects/horizon").status_code == 200
    assert signed_in(studio.target).get(f"{B}/projects/horizon").status_code == 200

    owner.put(
        f"{B}/projects/horizon/members/{studio.members[Role.DEVELOPER].id}", json={"access": "contributor"}
    )
    assert developer.get(f"{B}/projects/horizon").status_code == 200
    assert developer.get(f"{B}/tasks/{studio.task_id}").status_code == 200


def test_viewer_project_access_narrows_but_never_widens(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    developer_account = studio.members[Role.DEVELOPER]
    owner.put(f"{B}/projects/horizon/members/{developer_account.id}", json={"access": "viewer"})
    developer = signed_in(developer_account)
    project = developer.get(f"{B}/projects/horizon").json()
    assert "tasks.create" not in project["capabilities"]
    assert (
        developer.post(f"{B}/tasks", json={"title": "Nope", "project_id": studio.project_id.hex}).status_code
        == 403
    )
    assert developer.patch(f"{B}/tasks/{studio.task_id}", json={"priority": "high"}).status_code == 403
    # Studio-wide work outside the project is unaffected.
    assert developer.post(f"{B}/tasks", json={"title": "Studio chore"}).status_code == 201

    # "contributor" for a viewer-role member grants nothing extra.
    owner.put(f"{B}/projects/horizon/members/{studio.target.id}", json={"access": "contributor"})
    viewer_on_list = signed_in(studio.target)
    assert (
        viewer_on_list.post(
            f"{B}/tasks", json={"title": "Nope", "project_id": studio.project_id.hex}
        ).status_code
        == 403
    )


def test_access_list_rules(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    admin_id = studio.members[Role.ADMIN].id
    assert owner.put(f"{B}/projects/horizon/members/{admin_id}", json={"access": "viewer"}).status_code == 409
    assert (
        owner.put(f"{B}/projects/horizon/members/{studio.outsider.id}", json={"access": "viewer"}).status_code
        == 404
    )
    members = owner.get(f"{B}/projects/horizon/members").json()
    assert [m["email"] for m in members] == ["target@booski.test"]


def test_leaving_the_workspace_removes_project_access_and_assignments(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    owner.patch(f"{B}/tasks/{studio.task_id}", json={"assignee_user_id": str(studio.target.id)})
    assert owner.delete(f"{B}/members/{studio.target.id}").status_code == 204
    db.expire_all()
    assert db.get(ProjectMember, (studio.project_id, studio.target.id)) is None
    assert db.get_one(Task, studio.task_id).assignee_user_id is None  # ON DELETE SET NULL (assignee_user_id)


# ---------------------------------------------------------------- workstreams


def test_workstreams(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    path = f"{B}/projects/horizon/workstreams"
    created = owner.post(path, json={"department_id": str(studio.department_id), "name": "Audio"})
    assert created.status_code == 201
    assert (
        owner.post(path, json={"department_id": str(studio.department_id), "name": "Audio"}).status_code
        == 409
    )
    foreign = owner.post(path, json={"department_id": str(studio.other_department_id), "name": "Foreign"})
    assert foreign.status_code == 404
    workstream_id = created.json()["id"]
    assert owner.patch(f"{path}/{workstream_id}", json={"archived": True}).json()["archived_at"] is not None
    assert [w["name"] for w in owner.get(path).json()] == ["Core gameplay"]


# ---------------------------------------------------------------- milestones


def test_milestones_track_progress_and_completion(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    created = developer.post(
        f"{B}/projects/horizon/milestones", json={"name": "Alpha", "target_date": "2027-03-01"}
    )
    assert created.status_code == 201
    milestone_id = created.json()["id"]
    for status in ("done", "in_progress"):
        developer.post(
            f"{B}/tasks",
            json={
                "title": status,
                "project_id": str(studio.project_id),
                "milestone_id": milestone_id,
                "status": status,
            },
        )
    assert developer.get(f"{B}/milestones/{milestone_id}").json()["progress"] == {
        "total": 2,
        "done": 1,
        "percent": 50,
    }

    completed = developer.patch(f"{B}/milestones/{milestone_id}", json={"status": "completed"}).json()
    assert completed["completed_at"] is not None
    reopened = developer.patch(f"{B}/milestones/{milestone_id}", json={"status": "in_progress"}).json()
    assert reopened["completed_at"] is None
    names = [m["name"] for m in developer.get(f"{B}/projects/horizon/milestones").json()]
    assert names == ["Vertical slice", "Alpha"]
