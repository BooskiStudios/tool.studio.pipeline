"""The default AI catalogue: models with prices, tier defaults and task routes (D33).

Migration 0004 seeds a frozen copy of these values; ``seed_default_catalog`` loads them into an empty
database (tests, and ``booski ai seed-catalog``). Change prices or routes with a migration or the CLI, and
record why in docs/DECISIONS.md.

Prices are Anthropic's published rates in US dollars per million tokens, checked on 14 November 2026
(https://platform.claude.com/docs/en/about-claude/pricing).
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.modules.ai.models import AiModel, AiTask, AiTierRoute
from booski_core.modules.ai.pricing import Pricing


def _band(
    max_prompt_tokens: int | None, input_: str, output: str, cw5: str, cw1h: str, read: str
) -> dict[str, Any]:
    return {
        "max_prompt_tokens": max_prompt_tokens,
        "input": input_,
        "output": output,
        "cache_write_5m": cw5,
        "cache_write_1h": cw1h,
        "cache_read": read,
    }


def _pricing(*bands: dict[str, Any]) -> dict[str, Any]:
    return {"currency": "USD", "unit": "per_million_tokens", "bands": list(bands)}


@dataclass(frozen=True)
class ModelSeed:
    provider: str
    model_key: str
    display_name: str
    pricing: dict[str, Any]


@dataclass(frozen=True)
class TierSeed:
    tier: str
    model_key: str
    effort: str
    max_tokens: int


@dataclass(frozen=True)
class TaskSeed:
    task_key: str
    tier: str
    description: str
    effort: str | None = None
    max_tokens: int | None = None


DEFAULT_MODELS = (
    ModelSeed(
        "anthropic",
        "claude-haiku-5-5",
        "Claude Haiku 5.5",
        _pricing(
            _band(100_000, "0.10", "0.50", "0.125", "0.20", "0.01"),
            _band(None, "0.50", "2.50", "0.625", "1.00", "0.05"),
        ),
    ),
    ModelSeed(
        "anthropic",
        "claude-sonnet-5-5",
        "Claude Sonnet 5.5",
        _pricing(_band(None, "2.00", "10.00", "2.50", "4.00", "0.10")),
    ),
    ModelSeed(
        "anthropic",
        "claude-opus-5-5",
        "Claude Opus 5.5",
        _pricing(_band(None, "4.00", "20.00", "5.00", "8.00", "0.20")),
    ),
)

# The cheapest model that does each tier's work well; effort is the second cost lever.
DEFAULT_TIERS = (
    TierSeed("routine", "claude-haiku-5-5", "low", 4_096),
    TierSeed("standard", "claude-sonnet-5-5", "medium", 16_000),
    TierSeed("deep", "claude-opus-5-5", "high", 16_000),
)

# Starting task types. They are a first guess to be tuned from the cost and outcome log; milestones that
# add AI features add their own tasks.
DEFAULT_TASKS = (
    TaskSeed("connection-check", "routine", "Checks that the AI provider answers.", max_tokens=1_024),
    TaskSeed("classify", "routine", "Sort or label short text into known categories."),
    TaskSeed("extract", "routine", "Pull structured facts out of text."),
    TaskSeed("summarise", "routine", "Summarise a document, thread or set of notes."),
    TaskSeed("draft", "standard", "Write a first draft of a document, description or message."),
    TaskSeed("review", "deep", "Review a design, plan or piece of work and find problems."),
    TaskSeed("plan", "deep", "Break a goal into steps, weighing options and risks."),
)


def seed_default_catalog(db: Session) -> None:
    """Inserts the default catalogue where it is missing. Existing rows are left untouched."""
    models: dict[str, AiModel] = {}
    for seed in DEFAULT_MODELS:
        Pricing.model_validate(seed.pricing)
        model = db.scalar(
            select(AiModel).where(AiModel.provider == seed.provider, AiModel.model_key == seed.model_key)
        )
        if model is None:
            model = AiModel(
                provider=seed.provider,
                model_key=seed.model_key,
                display_name=seed.display_name,
                pricing=seed.pricing,
            )
            db.add(model)
            db.flush()
        models[seed.model_key] = model
    for tier in DEFAULT_TIERS:
        if db.get(AiTierRoute, tier.tier) is None:
            db.add(
                AiTierRoute(
                    tier=tier.tier,
                    model_id=models[tier.model_key].id,
                    effort=tier.effort,
                    max_tokens=tier.max_tokens,
                )
            )
    db.flush()
    for task in DEFAULT_TASKS:
        if db.get(AiTask, task.task_key) is None:
            db.add(
                AiTask(
                    task_key=task.task_key,
                    tier=task.tier,
                    description=task.description,
                    effort=task.effort,
                    max_tokens=task.max_tokens,
                )
            )
    db.flush()
