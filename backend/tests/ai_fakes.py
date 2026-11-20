"""A scriptable stand-in for an AI provider. Tests never call a real provider."""

from collections.abc import Callable
from dataclasses import dataclass, field

from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import AiCall, AiResult, ChatMessage, ProviderError

DEFAULT_RESULT = AiResult(
    text="OK",
    stop_reason="end_turn",
    usage=TokenUsage(input_tokens=12, output_tokens=4),
    provider_request_id="req_fake",
)


@dataclass
class FakeProvider:
    name: str = "anthropic"
    result: AiResult = DEFAULT_RESULT
    error: ProviderError | None = None
    calls: list[AiCall] = field(default_factory=list)
    # Optional scripting: errors raised first, one per call, then ``responder`` builds each result.
    errors: list[ProviderError] = field(default_factory=list)
    responder: Callable[[AiCall], AiResult] | None = None

    def complete(self, call: AiCall) -> AiResult:
        self.calls.append(call)
        if self.error is not None:
            raise self.error
        if self.errors:
            raise self.errors.pop(0)
        if self.responder is not None:
            return self.responder(call)
        return self.result


def prompt_of(call: AiCall) -> str:
    """The first user message of a call: the prompt Booski wrote (later messages may be tool turns)."""
    return next(m.content for m in call.messages if isinstance(m, ChatMessage))
