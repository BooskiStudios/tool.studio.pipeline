"""The Anthropic adapter against a simulated Anthropic API (httpx2 mock transport): request shape,
usage mapping, refusals, retries, timeouts and error mapping. Nothing here reaches the network."""

import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from booski_core.modules.ai.providers.anthropic import AnthropicProvider
from booski_core.modules.ai.providers.base import AiCall, ChatMessage, ProviderError, ProviderErrorKind

KEY = "sk-ant-test-not-a-real-key"
CALL = AiCall(
    model_key="claude-haiku-5-5",
    messages=(ChatMessage(role="user", content="Reply with OK."),),
    max_tokens=1024,
    system="Be brief.",
    effort="low",
)


def _message(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": "OK"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 12,
            "output_tokens": 4,
            "cache_creation_input_tokens": 100,
            "cache_read_input_tokens": 50,
            "cache_creation": {"ephemeral_5m_input_tokens": 60, "ephemeral_1h_input_tokens": 40},
        },
    }
    body.update(overrides)
    return body


Handler = Callable[[httpx2.Request], httpx2.Response]


def _provider(handler: Handler, *, max_retries: int = 0, timeout: float = 5) -> AnthropicProvider:
    return AnthropicProvider(
        api_key=KEY,
        timeout_seconds=timeout,
        max_retries=max_retries,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        base_url="https://api.test.invalid",
    )


def _error(status: int, kind: str = "api_error") -> httpx2.Response:
    # retry-after-ms keeps retry tests fast.
    return httpx2.Response(
        status,
        json={"type": "error", "error": {"type": kind, "message": "simulated"}},
        headers={"request-id": "req_err", "retry-after-ms": "1"},
    )


def test_sends_the_routed_request_with_the_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-environment")  # must be ignored
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=_message(), headers={"request-id": "req_123"})

    result = _provider(handler).complete(CALL)

    request = seen[0]
    assert request.url.path == "/v1/messages"
    credentials = request.headers.get("x-api-key", "") + request.headers.get("authorization", "")
    assert KEY in credentials
    assert "sk-ant-from-environment" not in str(dict(request.headers))
    body = json.loads(request.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == 1024
    assert body["system"] == "Be brief."
    assert body["output_config"] == {"effort": "low"}
    assert body["messages"] == [{"role": "user", "content": "Reply with OK."}]
    assert "thinking" not in body  # current models think adaptively by default

    assert result.text == "OK"
    assert result.stop_reason == "end_turn"
    assert result.provider_request_id == "req_123"
    assert result.usage.input_tokens == 12
    assert result.usage.output_tokens == 4
    assert result.usage.cache_write_5m_tokens == 60
    assert result.usage.cache_write_1h_tokens == 40
    assert result.usage.cache_read_tokens == 50
    assert not result.refused


def test_cache_writes_without_a_breakdown_count_as_five_minute_writes() -> None:
    usage = {
        "input_tokens": 1,
        "output_tokens": 1,
        "cache_creation_input_tokens": 30,
        "cache_read_input_tokens": 0,
    }
    result = _provider(lambda r: httpx2.Response(200, json=_message(usage=usage))).complete(CALL)
    assert (result.usage.cache_write_5m_tokens, result.usage.cache_write_1h_tokens) == (30, 0)


def test_a_refusal_is_a_result_not_an_error() -> None:
    body = _message(
        content=[],
        stop_reason="refusal",
        stop_details={"type": "refusal", "category": "cyber", "explanation": "declined"},
    )
    result = _provider(lambda r: httpx2.Response(200, json=body)).complete(CALL)
    assert result.refused
    assert result.refusal_category == "cyber"
    assert result.text == ""


def test_rate_limits_and_server_errors_are_retried() -> None:
    responses = iter(
        [
            _error(429, "rate_limit_error"),
            _error(529, "overloaded_error"),
            httpx2.Response(200, json=_message()),
        ]
    )
    attempts: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        attempts.append(1)
        return next(responses)

    result = _provider(handler, max_retries=2).complete(CALL)
    assert result.text == "OK"
    assert len(attempts) == 3


@pytest.mark.parametrize(
    ("status", "error_type", "kind"),
    [
        (429, "rate_limit_error", ProviderErrorKind.RATE_LIMITED),
        (500, "api_error", ProviderErrorKind.UNAVAILABLE),
        (529, "overloaded_error", ProviderErrorKind.UNAVAILABLE),
        (401, "authentication_error", ProviderErrorKind.AUTHENTICATION),
        (403, "permission_error", ProviderErrorKind.AUTHENTICATION),
        (400, "invalid_request_error", ProviderErrorKind.INVALID_REQUEST),
        (404, "not_found_error", ProviderErrorKind.INVALID_REQUEST),
    ],
)
def test_errors_after_retries_are_mapped(status: int, error_type: str, kind: ProviderErrorKind) -> None:
    attempts: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        attempts.append(1)
        return _error(status, error_type)

    with pytest.raises(ProviderError) as caught:
        _provider(handler, max_retries=1).complete(CALL)
    assert caught.value.kind is kind
    assert caught.value.provider_request_id == "req_err"
    assert KEY not in str(caught.value)
    retried = status in {429, 500, 529}
    assert len(attempts) == (2 if retried else 1)


def test_timeouts_are_retried_then_reported() -> None:
    attempts: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        attempts.append(1)
        raise httpx2.ReadTimeout("simulated timeout", request=request)

    with pytest.raises(ProviderError) as caught:
        _provider(handler, max_retries=1).complete(CALL)
    assert caught.value.kind is ProviderErrorKind.TIMEOUT
    assert len(attempts) == 2


def test_connection_failures_are_reported() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("simulated", request=request)

    with pytest.raises(ProviderError) as caught:
        _provider(handler).complete(CALL)
    assert caught.value.kind is ProviderErrorKind.CONNECTION
