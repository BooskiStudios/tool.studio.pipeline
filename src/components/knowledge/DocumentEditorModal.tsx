import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { isApiError } from "../../api/client";
import * as core from "../../api/core";
import { useDepartments, useProjectList, useWorkspaceMutation } from "../../api/hooks";
import type { DocumentInput, DocumentKind, StudioDocument } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { DOCUMENT_KIND } from "../../lib/format";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { MarkdownView } from "../MarkdownView";
import { Modal } from "../Modal";
import { ConflictNotice, Field, FormError } from "../ui";

const MAX_BODY_BYTES = 1_000_000; // Booski Core's limit for document text

export interface DocumentDefaults {
  kind?: DocumentKind;
  project_id?: string | null;
  department_id?: string | null;
  title?: string;
  body?: string;
}

/**
 * Create or edit a knowledge document. Documents are Markdown text; every saved change becomes a new,
 * permanent revision. Files and attachments are not supported yet.
 */
export function DocumentEditorModal({ document, defaults = {}, onClose, onSaved }: {
  /** Omit to create a new document. */
  document?: StudioDocument;
  defaults?: DocumentDefaults;
  onClose: () => void;
  onSaved?: (saved: StudioDocument) => void;
}) {
  const { slug } = useWorkspace();
  const queryClient = useQueryClient();
  const notify = useToast();
  const projects = useProjectList();
  const departments = useDepartments();
  const [kind, setKind] = useState<DocumentKind>(document?.kind ?? defaults.kind ?? "note");
  const [title, setTitle] = useState(document?.title ?? defaults.title ?? "");
  const [summary, setSummary] = useState(document?.summary ?? "");
  const [body, setBody] = useState(document?.body ?? defaults.body ?? "");
  const [tags, setTags] = useState((document?.tags ?? []).join(", "));
  const [projectId, setProjectId] = useState(document?.project_id ?? defaults.project_id ?? "");
  const [departmentId, setDepartmentId] = useState(document?.department_id ?? defaults.department_id ?? "");
  const [changeNote, setChangeNote] = useState("");
  const [preview, setPreview] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const save = useWorkspaceMutation((ws, input: DocumentInput) =>
    document ? core.documents.update(ws, document.id, input) : core.documents.create(ws, input),
  );
  const conflict = isApiError(save.error, "conflict");
  const writableProjects = (projects.data ?? []).filter((p) => p.capabilities.includes("documents.write") || p.id === projectId);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return setLocalError("Give the document a title.");
    if (new TextEncoder().encode(body).length > MAX_BODY_BYTES) {
      return setLocalError("The document is longer than 1 MB of text. Split it into several documents.");
    }
    setLocalError(null);
    const input: DocumentInput = {
      kind,
      title: title.trim(),
      summary: summary.trim(),
      body,
      tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      project_id: projectId || null,
      department_id: departmentId || null,
    };
    save.mutate(document ? { ...input, change_note: changeNote.trim(), version: document.version } : input, {
      onSuccess: (saved) => {
        notify(document ? `Saved revision ${saved.current_revision} of “${saved.title}”.` : `Document created: ${saved.title}`);
        onSaved?.(saved);
        onClose();
      },
    });
  };

  return (
    <Modal
      eyebrow="KNOWLEDGE BASE"
      title={document ? "Edit document" : "New document"}
      description="Write in Markdown. Each save keeps the previous version in the revision history. File uploads are not supported yet."
      onClose={onClose}
      size="wide"
    >
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <Field label="Title" className="span-2">
            {(props) => <input {...props} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} data-autofocus />}
          </Field>
          <Field label="Type">
            {(props) => (
              <select {...props} value={kind} onChange={(e) => setKind(e.target.value as DocumentKind)}>
                {(Object.keys(DOCUMENT_KIND) as DocumentKind[]).map((k) => <option key={k} value={k}>{DOCUMENT_KIND[k]}</option>)}
              </select>
            )}
          </Field>
          <Field label="Tags" hint="Comma-separated, e.g. movement, controls">
            {(props) => <input {...props} value={tags} onChange={(e) => setTags(e.target.value)} />}
          </Field>
          <Field label="Project">
            {(props) => (
              <select {...props} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">Studio-wide (no project)</option>
                {writableProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Department">
            {(props) => (
              <select {...props} value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                <option value="">No department</option>
                {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Summary" className="span-2">
            {(props) => <input {...props} value={summary} onChange={(e) => setSummary(e.target.value)} maxLength={1000} />}
          </Field>
          <div className="form-field span-2">
            <div className="editor-toolbar">
              <label htmlFor="document-body">Content (Markdown)</label>
              <button type="button" className="secondary-btn" onClick={() => setPreview((p) => !p)} aria-pressed={preview}>
                {preview ? "Edit" : "Preview"}
              </button>
            </div>
            {preview ? (
              <div className="markdown-preview"><MarkdownView source={body} /></div>
            ) : (
              <textarea id="document-body" className="document-textarea" rows={14} value={body} onChange={(e) => setBody(e.target.value)} />
            )}
          </div>
          {document && (
            <Field label="What changed?" hint="Optional note shown in the revision history." className="span-2">
              {(props) => <input {...props} value={changeNote} onChange={(e) => setChangeNote(e.target.value)} maxLength={200} />}
            </Field>
          )}
        </div>
        {conflict ? (
          <ConflictNotice
            onRefresh={() => {
              void queryClient.invalidateQueries({ queryKey: ["ws", slug] });
              onClose();
            }}
          />
        ) : (
          <FormError error={localError ?? save.error} />
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={save.isPending || conflict}>
            {save.isPending ? "Saving…" : document ? "Save new revision" : "Create document"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
