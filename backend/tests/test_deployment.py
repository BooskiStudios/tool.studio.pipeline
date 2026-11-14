"""Deployment hardening without a database: security headers, serving the web app, production settings
and the server options."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from booski_core import cli
from booski_core.config import Environment, Settings
from booski_core.core.frontend import FrontendNotBuiltError
from booski_core.main import create_app
from conftest import UNREACHABLE_DB_URL

PRODUCTION_URL = "postgresql+psycopg://booski:a-strong-password@db.internal:5432/booski"


# ---------------------------------------------------------------- security headers


def test_api_responses_forbid_framing_sniffing_and_caching(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "Strict-Transport-Security" not in response.headers  # development is plain http


def test_error_responses_get_the_same_headers(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/w/someone/projects")  # 401
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_production_adds_hsts_and_hides_docs() -> None:
    settings = Settings(
        environment=Environment.PRODUCTION,
        database_url=PRODUCTION_URL,
        allowed_origins=["https://studio.example.com"],
        database_connect_timeout_seconds=1,
    )
    client = TestClient(create_app(settings))
    response = client.get("/api/v1/health/live")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")
    assert client.get("/api/docs").status_code == 404


# ---------------------------------------------------------------- serving the web app


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Booski</title>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "robots.txt").write_text("User-agent: *", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("outside dist", encoding="utf-8")
    return tmp_path


@pytest.fixture
def web_client(dist: Path) -> TestClient:
    settings = Settings(
        environment=Environment.TEST,
        database_url=UNREACHABLE_DB_URL,
        database_connect_timeout_seconds=1,
        frontend_dist=dist,
    )
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_web_app_is_served_with_an_app_csp(web_client: TestClient) -> None:
    response = web_client.get("/")
    assert response.status_code == 200
    assert "<title>Booski</title>" in response.text
    csp = response.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "connect-src 'self'" in csp
    assert response.headers["Cache-Control"] == "no-cache"


def test_deep_links_fall_back_to_index(web_client: TestClient) -> None:
    for path in ("/projects/horizon", "/tasks", "/login"):
        response = web_client.get(path)
        assert response.status_code == 200
        assert "<title>Booski</title>" in response.text


def test_hashed_assets_are_cached_for_a_year(web_client: TestClient) -> None:
    response = web_client.get("/assets/index-abc123.js")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert web_client.get("/robots.txt").text == "User-agent: *"


def test_missing_files_are_404_not_html(web_client: TestClient) -> None:
    response = web_client.get("/assets/index-old999.js")
    assert response.status_code == 404
    assert "<title>" not in response.text


def test_files_outside_dist_are_never_served(web_client: TestClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = web_client.get(path)
        assert "outside dist" not in response.text


def test_api_paths_are_never_answered_with_the_web_app(web_client: TestClient) -> None:
    response = web_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert web_client.get("/api/v1/health/live").json() == {"status": "ok"}


def test_missing_build_is_reported_at_startup(tmp_path: Path) -> None:
    settings = Settings(environment=Environment.TEST, database_url=UNREACHABLE_DB_URL, frontend_dist=tmp_path)
    with pytest.raises(FrontendNotBuiltError, match="npm run build"):
        create_app(settings)


# ---------------------------------------------------------------- production settings


def test_production_rejects_development_origins() -> None:
    with pytest.raises(ValidationError, match="only list https:// origins"):
        Settings(environment=Environment.PRODUCTION, database_url=PRODUCTION_URL)


def test_production_requires_a_database_password() -> None:
    with pytest.raises(ValidationError, match="must include a password"):
        Settings(
            environment=Environment.PRODUCTION,
            database_url="postgresql+psycopg://booski@db.internal:5432/booski",
            allowed_origins=["https://studio.example.com"],
        )


def test_valid_production_settings_are_accepted() -> None:
    settings = Settings(
        environment=Environment.PRODUCTION,
        database_url=PRODUCTION_URL,
        allowed_origins=["https://studio.example.com"],
    )
    assert settings.is_production


def test_development_settings_are_unaffected() -> None:
    assert Settings(environment=Environment.DEVELOPMENT, database_url=UNREACHABLE_DB_URL).allowed_origins


# ---------------------------------------------------------------- server options


def _captured_serve(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> dict[str, Any]:
    import uvicorn

    captured: dict[str, Any] = {}
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: captured.update(kwargs))
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    assert cli.main(["serve"]) == 0
    return captured


def test_serve_hides_the_server_header_and_ignores_forwarded_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    options = _captured_serve(monkeypatch, Settings(database_url=UNREACHABLE_DB_URL))
    assert options["host"] == "127.0.0.1"
    assert options["server_header"] is False
    assert options["proxy_headers"] is False
    assert options["forwarded_allow_ips"] is None
    assert options["timeout_graceful_shutdown"] == 10
    assert options["log_level"] == "info"


def test_serve_trusts_forwarded_headers_only_from_configured_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(database_url=UNREACHABLE_DB_URL, trusted_proxies=["10.0.0.5", "10.0.0.6"])
    options = _captured_serve(monkeypatch, settings)
    assert options["proxy_headers"] is True
    assert options["forwarded_allow_ips"] == "10.0.0.5,10.0.0.6"
