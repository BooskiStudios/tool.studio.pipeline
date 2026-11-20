"""The provider-neutral interface every AI provider implements."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Protocol

from booski_core.modules.ai.pricing import TokenUsage


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call (PR 3.5). ``input_schema`` is a JSON Schema object."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class AssistantTurn:
    """The model's previous reply, exactly as the provider returned it, to send back in a tool loop.

    Opaque on purpose: providers need their own content back unchanged (Anthropic's thinking blocks must
    be replayed as they came), so nothing outside the provider reads or edits ``raw``.
    """

    raw: Any


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ToolResultsTurn:
    """The results of every tool call in the previous reply, sent back together."""

    results: tuple[ToolResult, ...]


Message = ChatMessage | AssistantTurn | ToolResultsTurn


@dataclass(frozen=True)
class AiCall:
    """One request, already routed: the gateway has chosen the model, effort and output limit."""

    model_key: str
    messages: tuple[Message, ...]
    max_tokens: int
    system: str | None = None
    effort: str | None = None
    tools: tuple[ToolSpec, ...] = ()


@dataclass(frozen=True)
class AiResult:
    text: str
    stop_reason: str | None
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider_request_id: str | None = None
    refusal_category: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    assistant_turn: AssistantTurn | None = None  # to send back if the conversation continues

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
