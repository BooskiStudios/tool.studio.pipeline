"""Migration and readiness checks against a real PostgreSQL database."""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, text

from booski_core.config import Settings
from booski_core.main import create_app
from booski_core.migrations_config import alembic_config, database_revisions, migration_heads
from booski_core.models import Base

pytestmark = pytest.mark.db


def test_migration_history_has_a_single_head() -> None:
    assert len(migration_heads()) == 1


def test_ready_reports_behind_before_migrations(empty_database: Engine, db_settings: Settings) -> None:
    with TestClient(create_app(db_settings)) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "ok", "migrations": "behind"}


def test_upgrade_to_head_makes_api_ready(
    empty_database: Engine, db_settings: Settings, test_database_url: str
) -> None:
    command.upgrade(alembic_config(test_database_url), "head")
    assert database_revisions(empty_database) == migration_heads()

    with TestClient(create_app(db_settings)) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "migrations": "head"}


def test_downgrade_to_base_and_upgrade_again(empty_database: Engine, test_database_url: str) -> None:
    config = alembic_config(test_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert database_revisions(empty_database) == set()
    command.upgrade(config, "head")
    assert database_revisions(empty_database) == migration_heads()


IDENTITY_TABLES = {
    "users",
    "sessions",
    "login_attempts",
    "workspaces",
    "workspace_memberships",
    "invitations",
    "activity_events",
}


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_identity_migration_rolls_back_cleanly(empty_database: Engine, test_database_url: str) -> None:
    config = alembic_config(test_database_url)
    command.upgrade(config, "head")
    assert _tables(empty_database) >= IDENTITY_TABLES

    command.downgrade(config, "0001")
    assert _tables(empty_database) == set()
    with empty_database.connect() as connection:
        leftover = connection.scalar(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'activity_events_reject_change'")
        )
    assert leftover == 0

    command.upgrade(config, "head")
    assert _tables(empty_database) >= IDENTITY_TABLES


def test_models_and_migrations_agree(empty_database: Engine, test_database_url: str) -> None:
    """Fails when a model changes without a matching migration (`booski db revision -m …`)."""
    command.upgrade(alembic_config(test_database_url), "head")
    with empty_database.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []


STUDIO_TABLES = {
    "departments",
    "projects",
    "project_members",
    "workstreams",
    "milestones",
    "tasks",
    "task_comments",
    "documents",
    "document_revisions",
    "decisions",
    "decision_documents",
    "approvals",
    "approval_reviews",
}


def _seed_pr22_data(engine: Engine) -> None:
    """A user, a workspace, a membership and an activity event, as PR 2.2 would have left them."""
    with engine.begin() as connection:
        user_id = connection.scalar(
            text("INSERT INTO users (email, display_name) VALUES ('owner@booski.test', 'Owner') RETURNING id")
        )
        workspace_id = connection.scalar(
            text(
                "INSERT INTO workspaces (slug, name, created_by_user_id)"
                " VALUES ('booski', 'Booski', :u) RETURNING id"
            ),
            {"u": user_id},
        )
        connection.execute(
            text("INSERT INTO workspace_memberships (workspace_id, user_id, role) VALUES (:w, :u, 'owner')"),
            {"w": workspace_id, "u": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO activity_events"
                " (workspace_id, actor_type, actor_user_id, verb, entity_type, summary)"
                " VALUES (:w, 'user', :u, 'workspace.created', 'workspace', 'Created')"
            ),
            {"w": workspace_id, "u": user_id},
        )


def _count(engine: Engine, sql: str) -> int:
    with engine.connect() as connection:
        return int(connection.scalar(text(sql)) or 0)


def test_studio_migration_keeps_existing_data_and_rolls_back_cleanly(
    empty_database: Engine, test_database_url: str
) -> None:
    config = alembic_config(test_database_url)
    command.upgrade(config, "0002")
    _seed_pr22_data(empty_database)

    command.upgrade(config, "0003")
    assert _tables(empty_database) >= STUDIO_TABLES
    assert _count(empty_database, "SELECT count(*) FROM users") == 1
    assert _count(empty_database, "SELECT count(*) FROM workspace_memberships") == 1
    assert _count(empty_database, "SELECT count(*) FROM activity_events WHERE project_id IS NULL") == 1
    # The existing workspace received the seven default departments.
    assert _count(empty_database, "SELECT count(*) FROM departments") == 7

    command.downgrade(config, "0002")
    assert not (_tables(empty_database) & STUDIO_TABLES)
    columns = {c["name"] for c in inspect(empty_database).get_columns("activity_events")}
    assert "project_id" not in columns
    assert _count(empty_database, "SELECT count(*) FROM pg_proc WHERE proname = 'booski_reject_change'") == 0
    # PR 2.2 data is untouched by the rollback.
    assert _count(empty_database, "SELECT count(*) FROM users") == 1
    assert _count(empty_database, "SELECT count(*) FROM activity_events") == 1

    command.upgrade(config, "head")
    assert _count(empty_database, "SELECT count(*) FROM departments") == 7
