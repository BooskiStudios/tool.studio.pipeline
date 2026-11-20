"""Anthropic (Claude) through the official ``anthropic`` Python SDK.

Timeouts and retries: the SDK retries connection errors, 408, 409, 429 and 5xx with exponential backoff
(``max_retries``), and each attempt is bounded by ``timeout_seconds``. Refusal fallbacks are not enabled
(D37): a declined request comes back as a result with ``stop_reason == "refusal"``.
"""

from typing import Any

import anthropic
import httpx2

from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import (
    AiCall,
    AiResult,
    AssistantTurn,
    Message,
    ProviderError,
    ProviderErrorKind,
    ToolCall,
    ToolResultsTurn,
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        max_retries: int,
        http_client: httpx2.Client | None = None,
        base_url: str | None = None,
    ) -> None:
        # The key is always passed explicitly, so the SDK never falls back to credentials it finds on the
        # machine (ANTHROPIC_API_KEY, `ant auth login` profiles).
        self._client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
            http_client=http_client,
            base_url=base_url,
        )

    def complete(self, call: AiCall) -> AiResult:
        params: dict[str, Any] = {
            "model": call.model_key,
            "max_tokens": call.max_tokens,
            "messages": [_message(m) for m in call.messages],
        }
        if call.system:
            params["system"] = call.system
        if call.effort:
            params["output_config"] = {"effort": call.effort}
        if call.tools:
            # tool_choice stays "auto": forcing a tool is rejected by current models.
            params["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in call.tools
            ]
        try:
            message = self._client.messages.create(**params)
        except anthropic.APITimeoutError:  # a subclass of APIConnectionError, so it comes first
            raise ProviderError(
                ProviderErrorKind.TIMEOUT, "The AI provider did not answer in time."
            ) from None
        except anthropic.APIConnectionError:
            raise ProviderError(ProviderErrorKind.CONNECTION, "Could not reach the AI provider.") from None
        except anthropic.RateLimitError as error:
            raise _status_error(
                ProviderErrorKind.RATE_LIMITED, "The AI provider is rate limiting requests.", error
            ) from None
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as error:
            raise _status_error(
                ProviderErrorKind.AUTHENTICATION, "The server's AI provider key was rejected.", error
            ) from None
        except (anthropic.BadRequestError, anthropic.NotFoundError) as error:
            raise _status_error(
                ProviderErrorKind.INVALID_REQUEST, "The AI provider rejected the request.", error
            ) from None
        except anthropic.APIStatusError as error:
            kind = ProviderErrorKind.UNAVAILABLE if error.status_code >= 500 else ProviderErrorKind.OTHER
            raise _status_error(
                kind, f"The AI provider returned an error ({error.status_code}).", error
            ) from None

        text = "".join(block.text for block in message.content if block.type == "text")
        stop_details = getattr(message, "stop_details", None)
        return AiResult(
            text=text,
            stop_reason=message.stop_reason,
            usage=_usage(message.usage),
            provider_request_id=getattr(message, "_request_id", None),
            refusal_category=getattr(stop_details, "category", None)
            if message.stop_reason == "refusal"
            else None,
            tool_calls=tuple(
                ToolCall(
                    id=block.id, name=block.name, input=block.input if isinstance(block.input, dict) else {}
                )
                for block in message.content
                if block.type == "tool_use"
            ),
            # The full content (thinking, text and tool_use blocks), to send back unchanged.
            assistant_turn=AssistantTurn(raw=message.content),
        )


def _message(message: Message) -> dict[str, Any]:
    if isinstance(message, AssistantTurn):
        return {"role": "assistant", "content": message.raw}
    if isinstance(message, ToolResultsTurn):
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": r.call_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in message.results
            ],
        }
    return {"role": message.role, "content": message.content}


def _status_error(kind: ProviderErrorKind, message: str, error: anthropic.APIStatusError) -> ProviderError:
    return ProviderError(kind, message, provider_request_id=error.request_id)


def _usage(usage: Any) -> TokenUsage:
    cache_write = usage.cache_creation_input_tokens or 0
    breakdown = getattr(usage, "cache_creation", None)
    five_minutes = getattr(breakdown, "ephemeral_5m_input_tokens", None)
    one_hour = getattr(breakdown, "ephemeral_1h_input_tokens", None)
    if five_minutes is None and one_hour is None:
        five_minutes, one_hour = cache_write, 0  # no breakdown: the default cache lifetime is 5 minutes
    return TokenUsage(
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        cache_write_5m_tokens=five_minutes or 0,
        cache_write_1h_tokens=one_hour or 0,
        cache_read_tokens=usage.cache_read_input_tokens or 0,
    )
