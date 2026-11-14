"""Context assembly: the knowledge an AI request should see, within a token budget.

``assemble_context`` searches what the caller may see, then adds the best items in rank order until the
budget is used. An item that doesn't fit is shortened if a useful amount of room is left, otherwise left
out. Every item keeps its source, so answers can cite where facts came from.

Token counts are a conservative estimate (one token per ``CHARS_PER_TOKEN`` characters, rounded up), so
the real count is at or below the estimate and the assembled context never exceeds the budget. Counting
exactly would need a call to the provider for every candidate (D-P3-13).
"""

import math
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.modules.projects.models import Project
from booski_core.modules.retrieval.search import Hit, search

CHARS_PER_TOKEN = 3  # English text averages about 4 characters per token; 3 over-estimates on purpose
DEFAULT_BUDGET_TOKENS = 4_000
MIN_BUDGET_TOKENS = 100
MAX_BUDGET_TOKENS = 50_000
MIN_PARTIAL_TOKENS = 40  # don't add a fragment smaller than this
CANDIDATES = 30


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


@dataclass(frozen=True)
class ContextItem:
    hit: Hit
    block: str  # the text as it appears in the context, including its source line
    tokens: int
    truncated: bool


@dataclass(frozen=True)
class ContextPack:
    query: str
    items: list[ContextItem]
    budget_tokens: int
    omitted: int  # matching items that didn't fit

    @property
    def total_tokens(self) -> int:
        return sum(item.tokens for item in self.items)

    def render(self) -> str:
        """The context as one block of text for a prompt."""
        return "\n\n".join(item.block for item in self.items)


def _header(number: int, hit: Hit) -> str:
    label = {"memory": "Memory", "document": "Document", "decision": "Decision"}[hit.type]
    details = [d for d in (hit.kind, hit.status, f"revision {hit.revision}" if hit.revision else None) if d]
    suffix = f" ({', '.join(details)})" if details else ""
    return f"[{number}] {label}{suffix}: {hit.title}\nSource: {hit.path}\n"


def _shorten(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def assemble_context(
    db: Session,
    ctx: WorkspaceContext,
    query: str,
    *,
    project: Project | None = None,
    department_id: uuid.UUID | None = None,
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
) -> ContextPack:
    budget = max(MIN_BUDGET_TOKENS, min(budget_tokens, MAX_BUDGET_TOKENS))
    hits = search(db, ctx, query, project=project, department_id=department_id, limit=CANDIDATES)
    items: list[ContextItem] = []
    used = 0
    omitted = 0
    for hit in hits:
        header = _header(len(items) + 1, hit)
        block = header + hit.text
        tokens = estimate_tokens(block)
        truncated = False
        remaining = budget - used
        if tokens > remaining:
            if (
                remaining < MIN_PARTIAL_TOKENS
                or estimate_tokens(header) + MIN_PARTIAL_TOKENS // 2 > remaining
            ):
                omitted += 1
                continue
            room = remaining * CHARS_PER_TOKEN - len(header)
            block = header + _shorten(hit.text, room)
            tokens = estimate_tokens(block)
            truncated = True
        items.append(ContextItem(hit=hit, block=block, tokens=tokens, truncated=truncated))
        used += tokens
    return ContextPack(query=query, items=items, budget_tokens=budget, omitted=omitted)
