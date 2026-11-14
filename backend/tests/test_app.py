"""Behaviour that needs no database: health liveness, error format, request ids, docs exposure."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from booski_core.config import Environment, Settings
from booski_core.core.errors import PROBLEM_JSON
from booski_core.main import create_app


def test_live_reports_ok(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_unreachable_database_without_leaking_details(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable", "migrations": "unknown"}
    assert "not-a-real-password" not in response.text
    assert "127.0.0.1" not in response.text


def test_every_response_gets_a_request_id(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/live")
    assert len(response.headers["X-Request-ID"]) == 32


def test_valid_incoming_request_id_is_kept(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_unsafe_incoming_request_id_is_replaced(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/health/live", headers={"X-Request-ID": "<script>x</script>"})
    assert response.headers["X-Request-ID"] != "<script>x</script>"


def test_unknown_route_returns_problem_json(offline_client: TestClient) -> None:
    response = offline_client.get("/api/v1/nope", headers={"X-Request-ID": "req-1"})
    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "request_id": "req-1",
    }


def test_wrong_method_returns_problem_json(offline_client: TestClient) -> None:
    response = offline_client.post("/api/v1/health/live")
    assert response.status_code == 405
    assert response.json()["title"] == "Method Not Allowed"


def _app_with_test_routes(settings: Settings) -> FastAPI:
    app = create_app(settings)

    class Payload(BaseModel):
        password: str
        count: int

    @app.post("/api/v1/_test/validate")
    def validate(payload: Payload) -> dict[str, int]:
        return {"count": payload.count}

    @app.get("/api/v1/_test/crash")
    def crash() -> None:
        raise RuntimeError("internal secret detail")

    return app


def test_validation_errors_never_echo_submitted_values(offline_settings: Settings) -> None:
    with TestClient(_app_with_test_routes(offline_settings)) as client:
        response = client.post("/api/v1/_test/validate", json={"password": "hunter2", "count": "lots"})
    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["errors"] == [
        {
            "loc": ["body", "count"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert "hunter2" not in response.text
    assert "lots" not in response.text


def test_unhandled_errors_return_generic_500(offline_settings: Settings) -> None:
    with TestClient(_app_with_test_routes(offline_settings), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_test/crash", headers={"X-Request-ID": "crash-1"})
    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["request_id"] == "crash-1"
    assert "internal secret detail" not in response.text


def test_docs_are_served_outside_production(offline_client: TestClient) -> None:
    assert offline_client.get("/api/docs").status_code == 200
    assert offline_client.get("/api/openapi.json").status_code == 200


def test_docs_are_hidden_in_production(offline_settings: Settings) -> None:
    settings = offline_settings.model_copy(update={"environment": Environment.PRODUCTION})
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404
