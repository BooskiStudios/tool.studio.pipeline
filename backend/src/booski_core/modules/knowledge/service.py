"""Knowledge documents. Text lives in PostgreSQL as Markdown revisions; binary files are out of scope
until the file-storage abstraction lands (they must never be stored in the database)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_optional_project, project_capabilities, project_scope
from booski_core.access.roles import Capability
from booski_core.core.concurrency import bump_version, check_version
from booski_core.core.errors import ProblemError
from booski_core.core.pagination import SortKey, paginate
from booski_core.core.request_meta import RequestMeta, utcnow
from booski_core.core.schemas import attributes
from booski_core.modules.activity.service import record_workspace_event
from booski_core.modules.departments.service import get_optional_department
from booski_core.modules.knowledge.models import Document, DocumentRevision
from booski_core.modules.knowledge.schemas import DocumentCreate, DocumentOut, DocumentSort, DocumentUpdate
from booski_core.modules.projects.models import Project

DOCUMENT_NOT_FOUND = "Document not found."
NOT_ALLOWED = "Your role doesn't allow editing documents here."


def _scoped(ctx: WorkspaceContext) -> Select[Document]:
    return select(Document).where(
        Document.workspace_id == ctx.workspace.id, project_scope(ctx, Document.project_id)
    )


def get_document(db: Session, ctx: WorkspaceContext, document_id: uuid.UUID) -> Document:
    document = db.scalars(_scoped(ctx).where(Document.id == document_id)).one_or_none()
    if document is None:
        raise ProblemError(404, DOCUMENT_NOT_FOUND)
    return document


def _project_of(db: Session, document: Document) -> Project | None:
    return db.get(Project, document.project_id) if document.project_id else None


def current_body(db: Session, document: Document) -> str:
    body: str = db.scalars(
        select(DocumentRevision.body).where(
            DocumentRevision.document_id == document.id,
            DocumentRevision.revision_no == document.current_revision,
        )
    ).one()
    return body


def to_out(db: Session, ctx: WorkspaceContext, document: Document) -> DocumentOut:
    can_edit = Capability.DOCUMENTS_WRITE in project_capabilities(db, ctx, _project_of(db, document))
    return DocumentOut.model_validate(
        {**attributes(document, DocumentOut), "body": current_body(db, document), "can_edit": can_edit}
    )


def list_documents(
    db: Session,
    ctx: WorkspaceContext,
    *,
    kinds: list[str] | None,
    project: Project | None,
    studio_wide: bool,
    department_id: uuid.UUID | None,
    tag: str | None,
    q: str | None,
    archived: bool,
    sort: DocumentSort,
    limit: int,
    cursor: str | None,
) -> tuple[list[Document], str | None]:
    filters: list[ColumnElement[bool]] = [
        Document.archived_at.is_not(None) if archived else Document.archived_at.is_(None)
    ]
    if kinds:
        filters.append(Document.kind.in_(kinds))
    if project is not None:
        filters.append(Document.project_id == project.id)
    if studio_wide:
        filters.append(Document.project_id.is_(None))
    if department_id is not None:
        filters.append(Document.department_id == department_id)
    if tag:
        filters.append(Document.tags.contains([tag.lower()]))
    if q:
        filters.append(Document.title.icontains(q, autoescape=True))
    if sort == "title":
        key = SortKey(Document.title, str, "asc")
    else:
        key = SortKey(
            Document.created_at if sort == "created_at" else Document.updated_at, datetime.fromisoformat
        )
    rows, next_cursor = paginate(
        db,
        _scoped(ctx).where(*filters),
        key=key,
        id_column=Document.id,
        limit=limit,
        cursor=cursor,
        sort_value=lambda d: getattr(d, sort),
        row_id=lambda d: d.id,
    )
    return list(rows), next_cursor


def _require_write(db: Session, ctx: WorkspaceContext, project: Project | None) -> None:
    if Capability.DOCUMENTS_WRITE not in project_capabilities(db, ctx, project):
        raise ProblemError(403, NOT_ALLOWED)


def create_document(db: Session, ctx: WorkspaceContext, body: DocumentCreate, meta: RequestMeta) -> Document:
    project = get_optional_project(db, ctx, body.project_id)
    _require_write(db, ctx, project)
    get_optional_department(db, ctx, body.department_id)
    me = ctx.auth.user.id
    document = Document(
        workspace_id=ctx.workspace.id,
        created_by_user_id=me,
        updated_by_user_id=me,
        current_revision=1,
        **body.model_dump(exclude={"body"}),
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentRevision(
            workspace_id=ctx.workspace.id,
            document_id=document.id,
            revision_no=1,
            title=document.title,
            body=body.body,
            created_by_user_id=me,
            change_note="Created",
        )
    )
    record_workspace_event(
        db,
        ctx,
        meta,
        verb="document.created",
        entity_type="document",
        entity_id=document.id,
        project_id=document.project_id,
        summary=f"Created {document.kind.replace('_', ' ')} {document.title}",
    )
    db.flush()
    return document


def update_document(
    db: Session, ctx: WorkspaceContext, document: Document, body: DocumentUpdate, meta: RequestMeta
) -> Document:
    _require_write(db, ctx, _project_of(db, document))
    check_version(document, body.version)
    sent = body.model_dump(exclude_unset=True, exclude={"archived", "version", "change_note", "body"})
    if "project_id" in sent and sent["project_id"] != document.project_id:
        _require_write(db, ctx, get_optional_project(db, ctx, sent["project_id"]))  # must be allowed in both
    if sent.get("department_id") is not None:
        get_optional_department(db, ctx, sent["department_id"])

    diff: dict[str, Any] = {
        k: {"from": getattr(document, k), "to": v} for k, v in sent.items() if getattr(document, k) != v
    }
    for key in diff:
        setattr(document, key, sent[key])
    previous_body = current_body(db, document)
    body_changed = body.body is not None and body.body != previous_body
    if body_changed or "title" in diff:
        document.current_revision += 1
        db.add(
            DocumentRevision(
                workspace_id=ctx.workspace.id,
                document_id=document.id,
                revision_no=document.current_revision,
                title=document.title,
                body=body.body if body_changed and body.body is not None else previous_body,
                created_by_user_id=ctx.auth.user.id,
                change_note=body.change_note,
            )
        )
        if body_changed:
            diff["body"] = {"revision": document.current_revision}
    archive_verb = None
    if body.archived is not None and body.archived != (document.archived_at is not None):
        document.archived_at = utcnow() if body.archived else None
        archive_verb = "document.archived" if body.archived else "document.restored"
    if not diff and archive_verb is None:
        return document
    document.updated_by_user_id = ctx.auth.user.id
    bump_version(document)
    if diff:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb="document.updated",
            entity_type="document",
            entity_id=document.id,
            project_id=document.project_id,
            summary=f"Updated {document.title}",
            changes=diff,
        )
    if archive_verb:
        record_workspace_event(
            db,
            ctx,
            meta,
            verb=archive_verb,
            entity_type="document",
            entity_id=document.id,
            project_id=document.project_id,
            summary=f"{'Archived' if body.archived else 'Restored'} {document.title}",
        )
    db.flush()
    return document


def list_revisions(db: Session, document: Document) -> list[DocumentRevision]:
    return list(
        db.scalars(
            select(DocumentRevision)
            .where(DocumentRevision.document_id == document.id)
            .order_by(DocumentRevision.revision_no.desc())
        )
    )


def get_revision(db: Session, document: Document, revision_no: int) -> DocumentRevision:
    revision = db.scalars(
        select(DocumentRevision).where(
            DocumentRevision.document_id == document.id, DocumentRevision.revision_no == revision_no
        )
    ).one_or_none()
    if revision is None:
        raise ProblemError(404, "Revision not found.")
    return revision
