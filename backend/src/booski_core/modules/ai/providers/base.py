"""The provider-neutral interface every AI provider implements."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol

from booski_core.modules.ai.pricing import TokenUsage


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class AiCall:
    """One request, already routed: the gateway has chosen the model, effort and output limit."""

    model_key: str
    messages: tuple[ChatMessage, ...]
    max_tokens: int
    system: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class AiResult:
    text: str
    stop_reason: str | None
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider_request_id: str | None = None
    refusal_category: str | None = None

    @property
    def refused(self) -> bool:
        return self.stop_reason == "refusal"


class ProviderErrorKind(StrEnum):
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "provider_unavailable"  # the provider's servers failed or are overloaded
    AUTHENTICATION = "authentication_failed"  # the server's API key is missing, wrong or lacks access
    INVALID_REQUEST = "invalid_request"
    OTHER = "provider_error"


class ProviderError(Exception):
    """A provider call failed after the provider's own retries. The message never contains secrets."""

    def __init__(
        self, kind: ProviderErrorKind, message: str, *, provider_request_id: str | None = None
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.provider_request_id = provider_request_id


class AiProvider(Protocol):
    name: str

    def complete(self, call: AiCall) -> AiResult:
        """Runs one request. Raises ``ProviderError`` on failure; a refusal is a result, not an error."""
        ...
