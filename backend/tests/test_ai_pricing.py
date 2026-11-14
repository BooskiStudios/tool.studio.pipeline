"""Model prices and request cost (no database needed)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from booski_core.modules.ai.catalog import DEFAULT_MODELS
from booski_core.modules.ai.pricing import Pricing, TokenUsage, cost_usd


def _pricing(model_key: str) -> Pricing:
    seed = next(m for m in DEFAULT_MODELS if m.model_key == model_key)
    return Pricing.model_validate(seed.pricing)


def test_cost_is_exact_per_million_tokens() -> None:
    # Sonnet 5.5: $2 input, $10 output per million.
    usage = TokenUsage(input_tokens=1_000, output_tokens=500)
    assert cost_usd(_pricing("claude-sonnet-5-5"), usage) == Decimal("0.007")


def test_cache_reads_and_writes_use_their_own_rates() -> None:
    # Opus 5.5: cache write 5m $5, 1h $8, cache read $0.20 per million.
    usage = TokenUsage(
        cache_write_5m_tokens=1_000_000, cache_write_1h_tokens=1_000_000, cache_read_tokens=1_000_000
    )
    assert cost_usd(_pricing("claude-opus-5-5"), usage) == Decimal("13.20")


def test_haiku_long_prompts_use_the_higher_band() -> None:
    haiku = _pricing("claude-haiku-5-5")
    short = TokenUsage(input_tokens=100_000, output_tokens=1_000_000)
    assert cost_usd(haiku, short) == Decimal("0.01") + Decimal("0.50")
    # Over 100,000 prompt tokens (cache reads count towards the length) every token is priced higher.
    long = TokenUsage(input_tokens=90_000, cache_read_tokens=20_000, output_tokens=1_000_000)
    expected = Decimal("0.045") + Decimal("0.001") + Decimal("2.50")  # $0.50, $0.05 and $2.50 per million
    assert cost_usd(haiku, long) == expected


def test_zero_usage_costs_nothing() -> None:
    assert cost_usd(_pricing("claude-opus-5-5"), TokenUsage()) == 0


@pytest.mark.parametrize(
    "bands",
    [
        [
            {
                "max_prompt_tokens": 100,
                "input": 1,
                "output": 1,
                "cache_write_5m": 1,
                "cache_write_1h": 1,
                "cache_read": 1,
            }
        ],
        [
            {
                "max_prompt_tokens": None,
                "input": 1,
                "output": 1,
                "cache_write_5m": 1,
                "cache_write_1h": 1,
                "cache_read": 1,
            },
            {
                "max_prompt_tokens": None,
                "input": 1,
                "output": 1,
                "cache_write_5m": 1,
                "cache_write_1h": 1,
                "cache_read": 1,
            },
        ],
        [
            {
                "max_prompt_tokens": None,
                "input": -1,
                "output": 1,
                "cache_write_5m": 1,
                "cache_write_1h": 1,
                "cache_read": 1,
            }
        ],
    ],
    ids=["last-band-bounded", "two-unbounded", "negative-price"],
)
def test_invalid_pricing_is_rejected(bands: list[dict[str, object]]) -> None:
    with pytest.raises(ValidationError):
        Pricing.model_validate({"bands": bands})


def test_every_default_model_has_valid_pricing() -> None:
    for seed in DEFAULT_MODELS:
        Pricing.model_validate(seed.pricing)
