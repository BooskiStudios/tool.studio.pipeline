"""A scriptable stand-in for an AI provider. Tests never call a real provider."""

from dataclasses import dataclass, field

from booski_core.modules.ai.pricing import TokenUsage
from booski_core.modules.ai.providers.base import AiCall, AiResult, ProviderError

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

    def complete(self, call: AiCall) -> AiResult:
        self.calls.append(call)
        if self.error is not None:
            raise self.error
        return self.result
