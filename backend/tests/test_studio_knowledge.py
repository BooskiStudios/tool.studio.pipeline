"""Knowledge documents with revision history, and the Decision Log."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from helpers import Account
from studio import Studio, build_studio

pytestmark = pytest.mark.db

SignedIn = Callable[[Account], TestClient]
B = "/api/v1/w/booski"


@pytest.fixture
def studio(db: Session) -> Studio:
    return build_studio(db)


# ---------------------------------------------------------------- documents


def test_document_revisions_preserve_every_change(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    created = developer.post(
        f"{B}/documents",
        json={"kind": "guide", "title": "Unity Standards", "body": "# v1", "tags": ["Unity", "code"]},
    ).json()
    assert created["current_revision"] == 1 and created["body"] == "# v1"
    assert created["tags"] == ["unity", "code"]
    doc = f"{B}/documents/{created['id']}"

    edited = developer.patch(doc, json={"body": "# v2", "change_note": "Naming rules"}).json()
    assert edited["current_revision"] == 2
    retitled = developer.patch(doc, json={"title": "Unity Coding Standards"}).json()
    assert retitled["current_revision"] == 3 and retitled["body"] == "# v2"
    metadata_only = developer.patch(doc, json={"summary": "How we write C#", "tags": ["unity"]}).json()
    assert metadata_only["current_revision"] == 3  # no new revision without a title or body change

    revisions = developer.get(f"{doc}/revisions").json()
    assert [(r["revision_no"], r["title"]) for r in revisions] == [
        (3, "Unity Coding Standards"),
        (2, "Unity Standards"),
        (1, "Unity Standards"),
    ]
    assert developer.get(f"{doc}/revisions/1").json()["body"] == "# v1"
    assert developer.get(f"{doc}/revisions/9").status_code == 404


def test_revisions_are_immutable_in_the_database(studio: Studio, db: Session) -> None:
    for statement in ("UPDATE document_revisions SET body = 'tampered'", "DELETE FROM document_revisions"):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement))
        db.rollback()


def test_document_listing_filters(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    developer.post(f"{B}/documents", json={"kind": "research", "title": "Horror market", "tags": ["market"]})
    developer.post(f"{B}/documents", json={"kind": "template", "title": "GDD template"})

    def titles(query: str) -> list[str]:
        return [d["title"] for d in developer.get(f"{B}/documents?{query}").json()["items"]]

    assert titles("kind=research") == ["Horror market"]
    assert titles("tag=market") == ["Horror market"]
    assert sorted(titles("studio_wide=true")) == ["GDD template", "Horror market"]
    assert titles("project=horizon") == ["Controller design"]
    assert titles("sort=title") == ["Controller design", "GDD template", "Horror market"]
    assert "body" not in developer.get(f"{B}/documents").json()["items"][0]


def test_document_limits_and_permissions(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    too_big = developer.post(
        f"{B}/documents", json={"kind": "note", "title": "Huge", "body": "x" * 1_000_001}
    )
    assert too_big.status_code == 422
    assert (
        developer.post(f"{B}/documents", json={"kind": "spreadsheet", "title": "Bad kind"}).status_code == 422
    )
    collaborator = signed_in(studio.members[Role.COLLABORATOR])
    assert collaborator.post(f"{B}/documents", json={"kind": "note", "title": "Nope"}).status_code == 403
    assert collaborator.get(f"{B}/documents/{studio.document_id}").json()["can_edit"] is False
    cross = developer.post(
        f"{B}/documents", json={"kind": "note", "title": "X", "project_id": str(studio.other_project_id)}
    )
    assert cross.status_code == 404


# ---------------------------------------------------------------- decisions


def test_record_a_decision_with_options_and_supporting_documents(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    response = developer.post(
        f"{B}/decisions",
        json={
            "title": "Unity is the first supported engine",
            "context": "We need one engine first.",
            "options": [{"title": "Unity", "summary": "Team experience"}, {"title": "Unreal"}],
            "outcome": "Unity",
            "rationale": "Existing workflow.",
            "status": "accepted",
            "project_id": str(studio.project_id),
            "department_id": str(studio.department_id),
            "document_ids": [str(studio.document_id)],
        },
    )
    assert response.status_code == 201, response.text
    decision = response.json()
    assert decision["decided_at"] is not None
    assert [o["title"] for o in decision["options"]] == ["Unity", "Unreal"]
    assert decision["document_ids"] == [str(studio.document_id)]
    assert decision["author_user_id"] == str(studio.members[Role.DEVELOPER].id)


def test_supporting_documents_must_be_in_this_workspace(
    signed_in: SignedIn, studio: Studio, db: Session
) -> None:
    outsider = signed_in(studio.outsider)
    foreign_doc = outsider.post(
        "/api/v1/w/other-studio/documents", json={"kind": "note", "title": "Theirs"}
    ).json()
    developer = signed_in(studio.members[Role.DEVELOPER])
    response = developer.post(f"{B}/decisions", json={"title": "X", "document_ids": [foreign_doc["id"]]})
    assert response.status_code == 422


def test_superseding_a_decision(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    replacement = developer.post(
        f"{B}/decisions",
        json={"title": "Support Unreal too", "supersedes_decision_id": str(studio.decision_id)},
    ).json()
    assert (
        developer.get(f"{B}/decisions/{studio.decision_id}").json()["status"] == "accepted"
    )  # still proposed
    developer.patch(f"{B}/decisions/{replacement['id']}", json={"status": "accepted"})
    original = developer.get(f"{B}/decisions/{studio.decision_id}").json()
    assert original["status"] == "superseded"
    assert original["superseded_by_decision_id"] == replacement["id"]
    verbs = [e["verb"] for e in developer.get(f"{B}/decisions/{studio.decision_id}/history").json()["items"]]
    assert verbs == ["decision.superseded"]


def test_decision_filters_and_permissions(signed_in: SignedIn, studio: Studio) -> None:
    developer = signed_in(studio.members[Role.DEVELOPER])
    developer.post(f"{B}/decisions", json={"title": "Studio-wide tooling", "status": "proposed"})

    def titles(query: str) -> list[str]:
        return [d["title"] for d in developer.get(f"{B}/decisions?{query}").json()["items"]]

    assert titles("status=proposed") == ["Studio-wide tooling"]
    assert titles("project=horizon") == ["Use Unity"]
    assert (
        signed_in(studio.members[Role.COLLABORATOR]).post(f"{B}/decisions", json={"title": "x"}).status_code
        == 403
    )
