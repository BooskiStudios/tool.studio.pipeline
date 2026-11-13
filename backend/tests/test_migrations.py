"""Migration and readiness checks against a real PostgreSQL database."""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import Engine

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


def test_models_and_migrations_agree(empty_database: Engine, test_database_url: str) -> None:
    """Fails when a model changes without a matching migration (`booski db revision -m …`)."""
    command.upgrade(alembic_config(test_database_url), "head")
    with empty_database.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []
