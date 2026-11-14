import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from booski_core.access.dependencies import MemberContext
from booski_core.access.projects import get_project
from booski_core.core.pagination import Cursor, Limit, Page
from booski_core.modules.departments.service import get_department
from booski_core.modules.identity.dependencies import DbSession, Meta
from booski_core.modules.knowledge import service
from booski_core.modules.knowledge.schemas import (
    DocumentCreate,
    DocumentOut,
    DocumentSort,
    DocumentSummaryOut,
    DocumentUpdate,
    RevisionOut,
    RevisionSummaryOut,
)
from booski_core.vocab import DocumentKind

router = APIRouter(prefix="/w/{workspace_slug}/documents", tags=["knowledge"])


@router.get("", response_model=Page[DocumentSummaryOut])
def list_documents(
    ctx: MemberContext,
    db: DbSession,
    kind: Annotated[list[DocumentKind] | None, Query()] = None,
    project: Annotated[str | None, Query(description="Project slug.")] = None,
    studio_wide: Annotated[bool, Query(description="Only documents not tied to a project.")] = False,
    department: Annotated[str | None, Query(description="Department slug.")] = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    q: Annotated[str | None, Query(max_length=100, description="Search in titles.")] = None,
    archived: bool = False,
    sort: DocumentSort = "updated_at",
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[DocumentSummaryOut]:
    """Knowledge documents you can see (research, templates, guides, references, …), without their text."""
    rows, next_cursor = service.list_documents(
        db,
        ctx,
        kinds=list(kind) if kind else None,
        project=get_project(db, ctx, slug=project) if project else None,
        studio_wide=studio_wide,
        department_id=get_department(db, ctx, slug=department).id if department else None,
        tag=tag,
        q=q,
        archived=archived,
        sort=sort,
        limit=limit,
        cursor=cursor,
    )
    return Page(items=[DocumentSummaryOut.model_validate(d) for d in rows], next_cursor=next_cursor)


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentCreate, ctx: MemberContext, db: DbSession, meta: Meta) -> DocumentOut:
    document = service.create_document(db, ctx, body, meta)
    db.commit()
    db.refresh(document)
    return service.to_out(db, ctx, document)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> DocumentOut:
    """The document with the text of its current revision."""
    return service.to_out(db, ctx, service.get_document(db, ctx, document_id))


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: uuid.UUID, body: DocumentUpdate, ctx: MemberContext, db: DbSession, meta: Meta
) -> DocumentOut:
    document = service.update_document(db, ctx, service.get_document(db, ctx, document_id), body, meta)
    db.commit()
    db.refresh(document)
    return service.to_out(db, ctx, document)


@router.get("/{document_id}/revisions", response_model=list[RevisionSummaryOut])
def list_revisions(document_id: uuid.UUID, ctx: MemberContext, db: DbSession) -> list[RevisionSummaryOut]:
    """Every saved revision, newest first."""
    document = service.get_document(db, ctx, document_id)
    return [RevisionSummaryOut.model_validate(r) for r in service.list_revisions(db, document)]


@router.get("/{document_id}/revisions/{revision_no}", response_model=RevisionOut)
def get_revision(document_id: uuid.UUID, revision_no: int, ctx: MemberContext, db: DbSession) -> RevisionOut:
    document = service.get_document(db, ctx, document_id)
    return RevisionOut.model_validate(service.get_revision(db, document, revision_no))
