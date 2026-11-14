"""Search for people, and a preview of the context an AI request would be given (PR 3.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from booski_core.access.dependencies import MemberContext, WorkspaceContext, require
from booski_core.access.projects import get_project
from booski_core.access.roles import Capability
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.dependencies import DbSession
from booski_core.modules.retrieval.context import assemble_context
from booski_core.modules.retrieval.schemas import (
    ContextItemOut,
    ContextOut,
    ContextRequest,
    SearchOut,
    SearchResultOut,
    SourceOut,
)
from booski_core.modules.retrieval.search import Hit, search
from booski_core.vocab import SourceType

search_router = APIRouter(prefix="/w/{workspace_slug}/search", tags=["search"])
context_router = APIRouter(prefix="/w/{workspace_slug}/ai/context", tags=["ai"])

UseAi = Annotated[WorkspaceContext, Depends(require(Capability.AI_USE))]


def _source(hit: Hit) -> SourceOut:
    return SourceOut(
        type=hit.type,
        id=hit.id,
        title=hit.title,
        path=hit.path,
        project_id=hit.project_id,
        department_id=hit.department_id,
        updated_at=hit.updated_at,
        version=hit.version,
        revision=hit.revision,
        kind=hit.kind,
        status=hit.status,
    )


@search_router.get("", response_model=SearchOut)
def search_knowledge(
    ctx: MemberContext,
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=500, description='Words, "a phrase", or -excluded.')],
    project: Annotated[
        str | None, Query(description="Project slug: its records plus studio-wide ones.")
    ] = None,
    department: Annotated[str | None, Query(description="Department slug.")] = None,
    type: Annotated[list[SourceType] | None, Query(description="memory, document, decision.")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchOut:
    """Full-text search across memory, knowledge documents and the Decision Log.

    Only returns records you can see."""
    hits = search(
        db,
        ctx,
        q,
        project=get_project(db, ctx, slug=project) if project else None,
        department_id=get_department(db, ctx, slug=department).id if department else None,
        types=list(type) if type else None,
        limit=limit,
    )
    return SearchOut(
        query=q,
        results=[SearchResultOut(source=_source(h), snippet=h.snippet, rank=h.rank) for h in hits],
    )


@context_router.post("", response_model=ContextOut)
def preview_context(body: ContextRequest, ctx: UseAi, db: DbSession) -> ContextOut:
    """The knowledge an AI request about ``query`` would be given, within the token budget. Nothing is
    sent to an AI provider; this shows exactly what would be."""
    pack = assemble_context(
        db,
        ctx,
        body.query,
        project=get_project(db, ctx, slug=body.project) if body.project else None,
        department_id=get_department(db, ctx, slug=body.department).id if body.department else None,
        budget_tokens=body.budget_tokens,
    )
    return ContextOut(
        query=pack.query,
        budget_tokens=pack.budget_tokens,
        total_tokens=pack.total_tokens,
        omitted=pack.omitted,
        items=[
            ContextItemOut(
                source=_source(item.hit),
                text=item.block,
                tokens=item.tokens,
                truncated=item.truncated,
            )
            for item in pack.items
        ],
        rendered=pack.render(),
    )
