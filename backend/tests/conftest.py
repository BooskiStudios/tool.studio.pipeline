"""Shared fixtures.

Tests marked ``db`` need a real PostgreSQL 18 database whose name ends in ``_test``, given by
``BOOSKI_TEST_DATABASE_URL`` in the environment or in ``backend/.env`` (``booski devdb setup`` writes it).

Without it they are skipped locally. CI sets ``BOOSKI_REQUIRE_DB=1`` so that a missing database
fails the run instead of silently skipping.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, make_url, text

from booski_core.config import Environment, Settings
from booski_core.main import create_app

TEST_DB_ENV = "BOOSKI_TEST_DATABASE_URL"
REQUIRE_DB_ENV = "BOOSKI_REQUIRE_DB"
UNREACHABLE_DB_URL = "postgresql+psycopg://booski:not-a-real-password@127.0.0.1:1/booski_unreachable"


class _TestEnvironment(BaseSettings):
    """Reads the test database URL from the environment, or from backend/.env (see `booski devdb setup`)."""

    model_config = SettingsConfigDict(
        env_prefix="BOOSKI_", env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore"
    )
    test_database_url: str | None = None


_TEST_DATABASE_URL = _TestEnvironment().test_database_url


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _TEST_DATABASE_URL:
        return
    if os.environ.get(REQUIRE_DB_ENV) == "1":
        raise pytest.UsageError(f"{REQUIRE_DB_ENV}=1 but {TEST_DB_ENV} is not set.")
    skip = pytest.mark.skip(reason=f"{TEST_DB_ENV} is not set (run `uv run booski devdb setup`).")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def offline_settings() -> Settings:
    """Settings pointing at a port where nothing listens, for tests that must not touch a database."""
    return Settings(
        environment=Environment.TEST,
        database_url=UNREACHABLE_DB_URL,
        database_connect_timeout_seconds=1,
    )


@pytest.fixture
def offline_client(offline_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(offline_settings), raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = _TEST_DATABASE_URL or ""
    database = make_url(url).database or ""
    # The schema is wiped between tests: refuse to run against anything that isn't clearly a test database.
    if not database.endswith("_test"):
        raise pytest.UsageError(f"{TEST_DB_ENV} must name a database ending in '_test' (got {database!r}).")
    return url


@pytest.fixture
def empty_database(test_database_url: str) -> Iterator[Engine]:
    """An engine for the test database with an empty ``public`` schema (no tables, no migrations applied)."""
    engine = create_engine(test_database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_settings(test_database_url: str) -> Settings:
    return Settings(environment=Environment.TEST, database_url=test_database_url)
