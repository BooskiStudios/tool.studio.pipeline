"""Shared fixtures.

Tests marked ``db`` need a real PostgreSQL 18 database whose name ends in ``_test``, given by
``BOOSKI_TEST_DATABASE_URL`` in the environment or in ``backend/.env`` (``booski devdb setup`` writes it).

Without it they are skipped locally. CI sets ``BOOSKI_REQUIRE_DB=1`` so that a missing database
fails the run instead of silently skipping.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from ai_fakes import FakeProvider
from booski_core.config import Environment, Settings
from booski_core.main import create_app
from booski_core.migrations_config import alembic_config, database_revisions, migration_heads
from booski_core.models import Base
from booski_core.modules.ai.catalog import seed_default_catalog
from booski_core.security import passwords
from helpers import Account, sign_in

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


# ---------------------------------------------------------------- fast password hashing


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production argon2 parameters take ~100 ms per hash; tests use cheap ones. test_security.py checks
    that the production hasher keeps its real parameters."""
    monkeypatch.setattr(passwords, "_hasher", PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1))
    passwords._dummy_hash.cache_clear()


# ---------------------------------------------------------------- migrated database + clients


@pytest.fixture
def migrated_db(test_database_url: str) -> Iterator[Engine]:
    """The test database at the latest migration, with every table emptied."""
    engine = create_engine(test_database_url)
    if database_revisions(engine) != migration_heads():
        command.upgrade(alembic_config(test_database_url), "head")
    with engine.begin() as connection:
        # DELETE is ~1000x faster than TRUNCATE for near-empty tables (TRUNCATE recreates every table's
        # files). Triggers (append-only guards, foreign keys) are switched off for this transaction only,
        # which needs a superuser: true for `booski devdb` and the CI database.
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    # The AI catalogue is seeded by migration 0004; the wipe above removed it, so put it back.
    with Session(engine) as session:
        seed_default_catalog(session)
        session.commit()
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def fake_ai() -> FakeProvider:
    """The AI provider every test app uses: no test ever calls a real provider."""
    return FakeProvider()


@pytest.fixture
def app(migrated_db: Engine, db_settings: Settings, fake_ai: FakeProvider) -> Iterator[FastAPI]:
    application = create_app(db_settings)
    application.state.ai_providers = {"anthropic": fake_ai}
    try:
        yield application
    finally:
        application.state.engine.dispose()  # clients aren't context-managed, so lifespan cleanup doesn't run


ClientFactory = Callable[..., TestClient]


@pytest.fixture
def make_client(app: FastAPI) -> ClientFactory:
    """A fresh browser: its own cookie jar. HTTPS so that Secure cookies are sent back, as in a browser."""

    def factory(ip: str = "198.51.100.10") -> TestClient:
        return TestClient(
            app, base_url="https://testserver", client=(ip, 50000), raise_server_exceptions=True
        )

    return factory


@pytest.fixture
def client(make_client: ClientFactory) -> TestClient:
    return make_client()


@pytest.fixture
def db(migrated_db: Engine) -> Iterator[Session]:
    """A separate database session for arranging data and inspecting results."""
    with Session(migrated_db) as session:
        yield session


@pytest.fixture
def signed_in(make_client: ClientFactory) -> Callable[[Account], TestClient]:
    return lambda account: sign_in(make_client(), account)
