"""Model prices and the cost of a request.

Prices are US dollars per million tokens, as Anthropic bills. Some models charge more for long prompts
(Claude Haiku 5.5 above 100,000 prompt tokens), so a model's pricing is a list of bands ordered by
``max_prompt_tokens``; the last band has no upper limit. The prompt length that selects the band counts
every input token, including cache reads and writes.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, model_validator

PER_MILLION = Decimal(1_000_000)


class PriceBand(BaseModel):
    max_prompt_tokens: int | None = Field(
        default=None, ge=1, description="Upper limit; null for the last band."
    )
    input: Decimal = Field(ge=0)
    output: Decimal = Field(ge=0)
    cache_write_5m: Decimal = Field(ge=0)
    cache_write_1h: Decimal = Field(ge=0)
    cache_read: Decimal = Field(ge=0)


class Pricing(BaseModel):
    currency: str = Field(default="USD", pattern="^USD$")
    unit: str = Field(default="per_million_tokens", pattern="^per_million_tokens$")
    bands: list[PriceBand] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered_bands(self) -> Self:
        limits = [band.max_prompt_tokens for band in self.bands]
        if limits[-1] is not None or any(limit is None for limit in limits[:-1]):
            raise ValueError("only the last price band may (and must) have no max_prompt_tokens")
        bounded = [limit for limit in limits if limit is not None]
        if bounded != sorted(bounded) or len(set(bounded)) != len(bounded):
            raise ValueError("price bands must be in increasing max_prompt_tokens order")
        return self

    def band_for(self, prompt_tokens: int) -> PriceBand:
        for band in self.bands:
            if band.max_prompt_tokens is None or prompt_tokens <= band.max_prompt_tokens:
                return band
        raise AssertionError("unreachable: the last band is unbounded")  # pragma: no cover


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by a provider for one request.

    ``input_tokens`` excludes cache reads and writes (as the Anthropic API reports it).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def cache_write_tokens(self) -> int:
        return self.cache_write_5m_tokens + self.cache_write_1h_tokens

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_write_tokens + self.cache_read_tokens


def cost_usd(pricing: Pricing, usage: TokenUsage) -> Decimal:
    """Exact cost in US dollars (no rounding; stored with nine decimal places)."""
    band = pricing.band_for(usage.prompt_tokens)
    total = (
        usage.input_tokens * band.input
        + usage.output_tokens * band.output
        + usage.cache_write_5m_tokens * band.cache_write_5m
        + usage.cache_write_1h_tokens * band.cache_write_1h
        + usage.cache_read_tokens * band.cache_read
    )
    return total / PER_MILLION
