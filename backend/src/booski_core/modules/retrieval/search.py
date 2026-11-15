"""Full-text search across memory, documents and decisions, scoped to what the caller may see.

* Workspace: only this workspace's records.
* Projects: ``project_scope`` (restricted projects only for owners, admins and their access list).
* Archived memory entries and documents are never returned.
* Scope filters: a project (or department) returns that project's records **and** studio-wide ones, because
  both apply to work in that project.

Ranking: PostgreSQL ``ts_rank_cd`` (normalised to 0..1), then most recently updated. Memory entries are
curated, so they rank a little higher (``MEMORY_BOOST``).
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, func, literal_column, or_, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import project_scope
from booski_core.core.errors import ProblemError
from booski_core.modules.decisions.models import Decision
from booski_core.modules.knowledge.models import Document, DocumentRevision
from booski_core.modules.memory.models import Memory
from booski_core.modules.projects.models import Project
from booski_core.vocab import SourceType

ENGLISH: Any = literal_column("'english'::regconfig")
RANK_NORMALISATION = 32  # rank / (rank + 1): comparable 0..1 scores across record types
MEMORY_BOOST = 1.5
TITLE_PREVIEW = 80

_SNIPPET_OPTIONS = "MaxFragments=2, MaxWords=25, MinWords=8, StartSel=«, StopSel=», FragmentDelimiter=' … '"
_CONTEXT_OPTIONS = (
    "MaxFragments=3, MaxWords=60, MinWords=20, StartSel='', StopSel='', FragmentDelimiter=' … '"
)


@dataclass(frozen=True)
class Hit:
    """One search result, with everything needed to cite it."""

    type: SourceType
    id: uuid.UUID
    title: str
    snippet: str  # a short highlighted extract, for people
    text: str  # the relevant content, for AI context
    rank: float
    project_id: uuid.UUID | None
    department_id: uuid.UUID | None
    updated_at: datetime
    version: int
    revision: int | None = None  # documents: the revision the text came from
    kind: str | None = None  # memory kind or document kind
    status: str | None = None  # decisions
    path: str = ""  # the API path of the source record


MAX_ANY_WORDS = 30


def _tsquery(query: str) -> Any:
    return func.websearch_to_tsquery(ENGLISH, query)


def _any_words_tsquery(query: str) -> Any:
    """Matches records containing ANY of the query's words (stemmed; stop words dropped by PostgreSQL),
    ranked by how well they match. For natural-language questions, where requiring every word would
    find almost nothing. Only letters and digits reach ``to_tsquery``, so the input can't break it."""
    words = list(dict.fromkeys(w.lower() for w in re.findall(r"[^\W_]+", query)))[:MAX_ANY_WORDS]
    if not words:
        raise ProblemError(400, "Enter something to search for.")
    return func.to_tsquery(ENGLISH, " | ".join(words))


def _rank(vector: Any, tsq: Any) -> Any:
    return func.ts_rank_cd(vector, tsq, RANK_NORMALISATION)


def _scope_filters(
    column_project: Any, column_department: Any, project: Project | None, department_id: uuid.UUID | None
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if project is not None:
        filters.append(or_(column_project == project.id, column_project.is_(None)))
    if department_id is not None:
        filters.append(or_(column_department == department_id, column_department.is_(None)))
    return filters


def _preview(text: str, limit: int = TITLE_PREVIEW) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _memories(
    db: Session, ctx: WorkspaceContext, tsq: Any, scope: list[ColumnElement[bool]], limit: int
) -> list[Hit]:
    rank = _rank(Memory.search_vector, tsq)
    rows = db.execute(
        select(Memory, rank.label("rank"))
        .where(
            Memory.workspace_id == ctx.workspace.id,
            project_scope(ctx, Memory.project_id),
            Memory.archived_at.is_(None),
            Memory.search_vector.op("@@")(tsq),
            *scope,
        )
        .order_by(rank.desc(), Memory.updated_at.desc())
        .limit(limit)
    ).all()
    slug = ctx.workspace.slug
    return [
        Hit(
            type="memory",
            id=m.id,
            title=f"{m.kind.capitalize()}: {_preview(m.content)}",
            snippet=_preview(m.content, 200),
            text=m.content,
            rank=float(r) * MEMORY_BOOST,
            project_id=m.project_id,
            department_id=m.department_id,
            updated_at=m.updated_at,
            version=m.version,
            kind=m.kind,
            path=f"/api/v1/w/{slug}/memories/{m.id}",
        )
        for m, r in rows
    ]


def _documents(
    db: Session,
    ctx: WorkspaceContext,
    tsq: Any,
    scope: list[ColumnElement[bool]],
    limit: int,
) -> list[Hit]:
    revision = DocumentRevision
    vector = revision.search_vector.op("||")(Document.search_vector)
    rank = _rank(vector, tsq)
    snippet = func.ts_headline(ENGLISH, revision.body, tsq, _SNIPPET_OPTIONS)
    context = func.ts_headline(ENGLISH, revision.body, tsq, _CONTEXT_OPTIONS)
    rows = db.execute(
        select(
            Document, revision.revision_no, rank.label("rank"), snippet.label("snippet"), context.label("ctx")
        )
        .join(
            revision,
            and_(revision.document_id == Document.id, revision.revision_no == Document.current_revision),
        )
        .where(
            Document.workspace_id == ctx.workspace.id,
            project_scope(ctx, Document.project_id),
            Document.archived_at.is_(None),
            or_(revision.search_vector.op("@@")(tsq), Document.search_vector.op("@@")(tsq)),
            *scope,
        )
        .order_by(rank.desc(), Document.updated_at.desc())
        .limit(limit)
    ).all()
    slug = ctx.workspace.slug
    hits = []
    for document, revision_no, r, snip, extract in rows:
        text = "\n".join(part for part in (document.summary, extract) if part)
        hits.append(
            Hit(
                type="document",
                id=document.id,
                title=document.title,
                snippet=snip or _preview(document.summary, 200),
                text=text or document.title,
                rank=float(r),
                project_id=document.project_id,
                department_id=document.department_id,
                updated_at=document.updated_at,
                version=document.version,
                revision=revision_no,
                kind=document.kind,
                path=f"/api/v1/w/{slug}/documents/{document.id}/revisions/{revision_no}",
            )
        )
    return hits


def _decisions(
    db: Session, ctx: WorkspaceContext, tsq: Any, scope: list[ColumnElement[bool]], limit: int
) -> list[Hit]:
    rank = _rank(Decision.search_vector, tsq)
    body = Decision.outcome + " " + Decision.rationale + " " + Decision.context
    snippet = func.ts_headline(ENGLISH, body, tsq, _SNIPPET_OPTIONS)
    rows = db.execute(
        select(Decision, rank.label("rank"), snippet.label("snippet"))
        .where(
            Decision.workspace_id == ctx.workspace.id,
            project_scope(ctx, Decision.project_id),
            Decision.search_vector.op("@@")(tsq),
            *scope,
        )
        .order_by(rank.desc(), Decision.updated_at.desc())
        .limit(limit)
    ).all()
    slug = ctx.workspace.slug
    hits = []
    for decision, r, snip in rows:
        parts = [
            f"Outcome: {decision.outcome}" if decision.outcome else "",
            f"Rationale: {decision.rationale}" if decision.rationale else "",
            f"Context: {decision.context}" if decision.context and not decision.outcome else "",
        ]
        hits.append(
            Hit(
                type="decision",
                id=decision.id,
                title=decision.title,
                snippet=snip or decision.title,
                text="\n".join(p for p in parts if p) or decision.title,
                rank=float(r),
                project_id=decision.project_id,
                department_id=decision.department_id,
                updated_at=decision.updated_at,
                version=decision.version,
                status=decision.status,
                path=f"/api/v1/w/{slug}/decisions/{decision.id}",
            )
        )
    return hits


Searcher = Callable[[Session, WorkspaceContext, Any, list[ColumnElement[bool]], int], list[Hit]]
SEARCHERS: dict[SourceType, tuple[Searcher, Any]] = {
    "memory": (_memories, Memory),
    "document": (_documents, Document),
    "decision": (_decisions, Decision),
}


def search(
    db: Session,
    ctx: WorkspaceContext,
    query: str,
    *,
    project: Project | None = None,
    department_id: uuid.UUID | None = None,
    types: list[SourceType] | None = None,
    limit: int = 20,
    match_any: bool = False,
) -> list[Hit]:
    """The best matches across the chosen record types, highest rank first.

    ``match_any``: match any word of the query (for questions), instead of web-search syntax where every
    word must match (for people searching)."""
    if not query.strip():
        raise ProblemError(400, "Enter something to search for.")
    tsq = _any_words_tsquery(query) if match_any else _tsquery(query)
    hits: list[Hit] = []
    for source in types or list(SEARCHERS):
        searcher, model = SEARCHERS[source]
        scope = _scope_filters(model.project_id, model.department_id, project, department_id)
        hits.extend(searcher(db, ctx, tsq, scope, limit))
    hits.sort(key=lambda h: (h.rank, h.updated_at), reverse=True)
    return [replace(h, rank=round(h.rank, 6)) for h in hits[:limit]]
