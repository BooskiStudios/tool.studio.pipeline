"""AI providers. Each provider adapts one vendor's API to ``base.AiProvider``; nothing outside this package
imports a vendor SDK, so adding a provider (for example OpenAI) never changes the callers (D-P3-4)."""

from booski_core.config import Settings
from booski_core.modules.ai.providers.base import AiProvider


def build_providers(settings: Settings) -> dict[str, AiProvider]:
    """The providers this server is configured for, keyed by provider name. Empty when no key is set."""
    providers: dict[str, AiProvider] = {}
    if settings.anthropic_api_key is not None:
        from booski_core.modules.ai.providers.anthropic import AnthropicProvider

        providers["anthropic"] = AnthropicProvider(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout_seconds=settings.ai_request_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )
    return providers
