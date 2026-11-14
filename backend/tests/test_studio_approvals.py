"""The Approvals Centre: who may request, review and decide, and the audit trail."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
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


def _review(client: TestClient, approval_id: object, action: str, comment: str = "") -> int:
    return client.post(
        f"{B}/approvals/{approval_id}/reviews", json={"action": action, "comment": comment}
    ).status_code


def test_request_with_subject_infers_the_project(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    created = developer.post(
        f"{B}/approvals",
        json={
            "kind": "ai_output",
            "title": "Approve generated level layout",
            "subject_type": "task",
            "subject_id": str(studio.task_id),
            "payload": {"model": "claude", "files": 3},
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["project_id"] == str(studio.project_id)
    assert body["status"] == "pending" and body["can_decide"] is False  # can't decide your own


def test_subjects_and_reviewers_are_validated(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])

    def post(**body: object) -> int:
        return developer.post(f"{B}/approvals", json={"title": "x", **body}).status_code

    assert post(subject_type="task", subject_id=str(studio.other_task_id)) == 422
    assert post(subject_type="task") == 422
    assert post(reviewer_user_id=str(studio.members[Role.DEVELOPER].id)) == 422  # yourself
    assert post(reviewer_user_id=str(studio.members[Role.VIEWER].id)) == 422  # role can't decide
    assert post(reviewer_user_id=str(studio.outsider.id)) == 422
    assert post(payload={"blob": "x" * 70_000}) == 422
    assert (
        signed_in(studio.members[Role.COLLABORATOR]).post(f"{B}/approvals", json={"title": "x"}).status_code
        == 403
    )


def test_nobody_decides_their_own_request_not_even_an_admin(signed_in: SignedIn, studio: Studio) -> None:
    admin = signed_in(studio.members[Role.ADMIN])
    own = admin.post(f"{B}/approvals", json={"title": "Admin's own request"}).json()
    assert own["can_decide"] is False
    assert _review(admin, own["id"], "approve") == 403
    assert _review(signed_in(studio.members[Role.OWNER]), own["id"], "approve") == 201


def test_assigned_developer_reviewer_can_decide_but_other_developers_cannot(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    requester = signed_in(studio.requester)
    reviewer = signed_in(studio.members[Role.DEVELOPER])
    approval = requester.post(
        f"{B}/approvals",
        json={"title": "Merge PR", "reviewer_user_id": str(studio.members[Role.DEVELOPER].id)},
    ).json()
    assert reviewer.get(f"{B}/approvals/{approval['id']}").json()["can_decide"] is True
    unassigned = signed_in(studio.target)  # a viewer, and not the reviewer
    assert _review(unassigned, approval["id"], "approve") == 403
    assert _review(reviewer, approval["id"], "approve", "Ship it") == 201
    resolved = requester.get(f"{B}/approvals/{approval['id']}").json()
    assert resolved["status"] == "approved"
    assert resolved["resolved_by_user_id"] == str(studio.members[Role.DEVELOPER].id)
    assert resolved["resolution_comment"] == "Ship it"
    assert _review(reviewer, approval["id"], "reject", "Too late") == 409  # already decided


def test_changes_requested_then_resubmitted_then_approved(signed_in: SignedIn, studio: Studio) -> None:
    requester = signed_in(studio.requester)
    admin = signed_in(studio.members[Role.ADMIN])
    approval_id = studio.approval_id
    assert _review(admin, approval_id, "request_changes") == 422  # needs a reason
    assert _review(admin, approval_id, "request_changes", "Add tests") == 201
    assert _review(admin, approval_id, "approve") == 409  # waiting on the requester
    assert (
        admin.post(f"{B}/approvals/{approval_id}/resubmit", json={}).status_code == 403
    )  # not the requester
    resubmitted = requester.post(
        f"{B}/approvals/{approval_id}/resubmit", json={"comment": "Tests added", "payload": {"tests": 12}}
    )
    assert resubmitted.json()["status"] == "pending"
    assert _review(requester, approval_id, "comment", "Ready when you are") == 201
    assert _review(admin, approval_id, "approve") == 201

    actions = [r["action"] for r in admin.get(f"{B}/approvals/{approval_id}/reviews").json()]
    assert actions == ["changes_requested", "resubmitted", "commented", "approved"]


def test_cancel_and_reassign(signed_in: SignedIn, studio: Studio) -> None:
    requester = signed_in(studio.requester)
    developer = signed_in(studio.members[Role.DEVELOPER])
    reassigned = requester.patch(
        f"{B}/approvals/{studio.approval_id}",
        json={"reviewer_user_id": str(studio.members[Role.DEVELOPER].id)},
    )
    assert reassigned.json()["reviewer_user_id"] == str(studio.members[Role.DEVELOPER].id)
    assert developer.post(f"{B}/approvals/{studio.approval_id}/cancel", json={}).status_code == 403
    cancelled = requester.post(
        f"{B}/approvals/{studio.approval_id}/cancel", json={"comment": "No longer needed"}
    )
    assert cancelled.json()["status"] == "cancelled"
    assert requester.post(f"{B}/approvals/{studio.approval_id}/cancel", json={}).status_code == 409


def test_viewer_project_access_blocks_assigned_review(signed_in: SignedIn, studio: Studio) -> None:
    owner = signed_in(studio.members[Role.OWNER])
    developer_id = studio.members[Role.DEVELOPER].id
    owner.put(f"{B}/projects/horizon/members/{developer_id}", json={"access": "viewer"})
    requester = signed_in(studio.requester)
    response = requester.patch(
        f"{B}/approvals/{studio.approval_id}", json={"reviewer_user_id": str(developer_id)}
    )
    assert response.status_code == 422


def test_filters(signed_in: SignedIn, studio: Studio) -> None:
    requester = signed_in(studio.requester)
    requester.post(
        f"{B}/approvals",
        json={
            "title": "Spend on assets",
            "kind": "spending",
            "reviewer_user_id": str(studio.members[Role.DEVELOPER].id),
        },
    )

    def titles(client: TestClient, query: str) -> list[str]:
        return [a["title"] for a in client.get(f"{B}/approvals?{query}").json()["items"]]

    assert titles(requester, "kind=spending") == ["Spend on assets"]
    assert sorted(titles(requester, "requested_by=me")) == ["Merge controller refactor", "Spend on assets"]
    assert titles(signed_in(studio.members[Role.DEVELOPER]), "reviewer=me") == ["Spend on assets"]
    assert titles(requester, "status=approved") == []


def test_audit_trail(signed_in: SignedIn, studio: Studio, db: Session) -> None:
    _review(signed_in(studio.members[Role.ADMIN]), studio.approval_id, "reject", "Out of scope")
    event = db.scalars(select(ActivityEvent).where(ActivityEvent.verb == "approval.rejected")).one()
    assert event.project_id == studio.project_id
    assert event.changes == {"status": "rejected", "comment": "Out of scope"}
    for statement in ("UPDATE approval_reviews SET comment = 'x'", "DELETE FROM approval_reviews"):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement))
        db.rollback()
