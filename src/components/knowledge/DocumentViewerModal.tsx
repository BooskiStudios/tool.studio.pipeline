import { useState } from "react";
import { Archive, History, Pencil, RotateCcw } from "lucide-react";
import * as core from "../../api/core";
import { useDepartments, useDocument, useMemberNames, useProjectIndex, useRevision, useRevisions, useWorkspaceMutation } from "../../api/hooks";
import type { StudioDocument } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { DOCUMENT_KIND, formatDateTime } from "../../lib/format";
import { MarkdownView } from "../MarkdownView";
import { Modal } from "../Modal";
import { FormError, QueryView } from "../ui";
import { DocumentEditorModal } from "./DocumentEditorModal";

function RevisionHistory({ document }: { document: StudioDocument }) {
  const revisions = useRevisions(document.id);
  const nameOf = useMemberNames();
  const [selected, setSelected] = useState<number | null>(null);
  const revision = useRevision(document.id, selected);
  return (
    <div className="revision-layout">
      <QueryView query={revisions} label="revisions">
        {(rows) => (
          <ol className="revision-list" aria-label="Revisions, newest first">
            {[...rows].sort((a, b) => b.revision_no - a.revision_no).map((r) => (
              <li key={r.revision_no}>
                <button type="button" aria-pressed={selected === r.revision_no} onClick={() => setSelected(r.revision_no)}>
                  <b>Revision {r.revision_no}{r.revision_no === document.current_revision ? " (current)" : ""}</b>
                  <small>{formatDateTime(r.created_at)} · {nameOf(r.created_by_user_id) ?? "Former member"}</small>
                  {r.change_note && <small>“{r.change_note}”</small>}
                </button>
              </li>
            ))}
          </ol>
        )}
      </QueryView>
      <div className="revision-body">
        {selected === null ? (
          <p className="muted-text">Choose a revision to read it as it was saved. Revisions can't be changed or deleted.</p>
        ) : (
          <QueryView query={revision} label={`revision ${selected}`}>
            {(r) => (
              <>
                <h3>{r.title}</h3>
                <MarkdownView source={r.body} />
              </>
            )}
          </QueryView>
        )}
      </div>
    </div>
  );
}

/** Read a document, see who wrote and last edited it, browse its revisions, edit or archive it. */
export function DocumentViewerModal({ documentId, onClose }: { documentId: string; onClose: () => void }) {
  const document = useDocument(documentId);
  const nameOf = useMemberNames();
  const projects = useProjectIndex();
  const departments = useDepartments();
  const notify = useToast();
  const [view, setView] = useState<"document" | "history">("document");
  const [editing, setEditing] = useState(false);
  const archive = useWorkspaceMutation((ws, vars: { doc: StudioDocument; archived: boolean }) =>
    core.documents.update(ws, vars.doc.id, { archived: vars.archived, version: vars.doc.version }),
  );

  if (editing && document.data) {
    return <DocumentEditorModal document={document.data} onClose={() => setEditing(false)} />;
  }

  return (
    <Modal eyebrow="KNOWLEDGE BASE" title={document.data?.title ?? "Document"} onClose={onClose} size="wide">
      <QueryView query={document} label="this document">
        {(doc) => {
          const project = doc.project_id ? projects.get(doc.project_id) : undefined;
          const department = departments.data?.find((d) => d.id === doc.department_id);
          return (
            <>
              {doc.archived_at && <div className="auth-notice">This document is archived.</div>}
              <div className="tags">
                <span>{DOCUMENT_KIND[doc.kind]}</span>
                <span>{project ? project.name : "Studio-wide"}</span>
                {department && <span>{department.name}</span>}
                {doc.tags.map((t) => <span key={t}>#{t}</span>)}
              </div>
              <p className="document-meta">
                Created by {nameOf(doc.created_by_user_id) ?? "a former member"} · Last edited by{" "}
                {nameOf(doc.updated_by_user_id) ?? "a former member"} {formatDateTime(doc.updated_at)} · Revision {doc.current_revision}
              </p>
              {doc.summary && <p className="detail-text">{doc.summary}</p>}
              <div className="workspace-tabs" role="group" aria-label="Document views">
                <button type="button" aria-pressed={view === "document"} className={view === "document" ? "active-tab" : ""} onClick={() => setView("document")}>
                  Document
                </button>
                <button type="button" aria-pressed={view === "history"} className={view === "history" ? "active-tab" : ""} onClick={() => setView("history")}>
                  <History size={12} aria-hidden="true" /> Revision history
                </button>
              </div>
              {view === "document" ? <MarkdownView source={doc.body} /> : <RevisionHistory document={doc} />}
              <FormError error={archive.error} />
              {doc.can_edit ? (
                <div className="modal-actions">
                  <button
                    type="button"
                    className="secondary-btn"
                    disabled={archive.isPending}
                    onClick={() =>
                      archive.mutate(
                        { doc, archived: !doc.archived_at },
                        { onSuccess: () => notify(doc.archived_at ? "Document restored." : "Document archived.") },
                      )
                    }
                  >
                    {doc.archived_at ? <RotateCcw size={13} aria-hidden="true" /> : <Archive size={13} aria-hidden="true" />}
                    {doc.archived_at ? "Restore" : "Archive"}
                  </button>
                  <button type="button" className="primary-btn" onClick={() => setEditing(true)}>
                    <Pencil size={13} aria-hidden="true" /> Edit
                  </button>
                </div>
              ) : (
                <p className="small-note">You can read this document but not change it.</p>
              )}
            </>
          );
        }}
      </QueryView>
    </Modal>
  );
}
