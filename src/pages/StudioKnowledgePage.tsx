import { useState } from "react";
import { useSearchParams } from "react-router";
import { Plus } from "lucide-react";
import { useProjectList } from "../api/hooks";
import type { DocumentKind } from "../api/types";
import { PageHeading, SearchField } from "../components/common";
import { DocumentEditorModal } from "../components/knowledge/DocumentEditorModal";
import { DocumentList } from "../components/knowledge/DocumentList";
import { DocumentViewerModal } from "../components/knowledge/DocumentViewerModal";
import { DOCUMENT_KIND } from "../lib/format";
import { useWorkspace } from "../workspace/WorkspaceProvider";

/** Opens `?document=<id>` in the viewer; shared by the pages that list documents. */
export function useDocumentParam(): [string | null, (id: string | null) => void] {
  const [params, setParams] = useSearchParams();
  const set = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set("document", id);
    else next.delete("document");
    setParams(next, { replace: !id });
  };
  return [params.get("document"), set];
}

/** `/knowledge` — studio-wide and project knowledge (`?document=<id>` opens one). */
export function StudioKnowledgePage() {
  const { can } = useWorkspace();
  const projects = useProjectList();
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<DocumentKind | "">("");
  const [scope, setScope] = useState("");
  const [archived, setArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useDocumentParam();

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI STUDIOS / KNOWLEDGE"
        title="Studio Knowledge Base"
        description="Shared studio knowledge alongside project-specific documentation. Every edit is kept as a revision."
        source="live"
        actions={
          can("documents.write") && (
            <button type="button" className="primary-btn" onClick={() => setCreating(true)}>
              <Plus size={14} aria-hidden="true" /> New document
            </button>
          )
        }
      />
      <div className="knowledge-scope-grid">
        <article className="panel">
          <span className="eyebrow">SHARED KNOWLEDGE</span>
          <h2>Studio-wide foundations</h2>
          <p>Brand identity, working practices, technical standards and reusable lessons.</p>
        </article>
        <article className="panel">
          <span className="eyebrow">PROJECT KNOWLEDGE</span>
          <h2>Isolated project context</h2>
          <p>Game-specific designs, decisions, references and production notes, visible only to people who can see the project.</p>
        </article>
      </div>
      <div className="panel knowledge-doc-list">
        <div className="filter-bar" role="search" aria-label="Filter documents">
          <SearchField value={q} onChange={setQ} placeholder="Search document titles…" />
          <select value={kind} onChange={(e) => setKind(e.target.value as DocumentKind | "")} aria-label="Type">
            <option value="">All types</option>
            {(Object.keys(DOCUMENT_KIND) as DocumentKind[]).map((k) => <option key={k} value={k}>{DOCUMENT_KIND[k]}</option>)}
          </select>
          <select value={scope} onChange={(e) => setScope(e.target.value)} aria-label="Scope">
            <option value="">Everything</option>
            <option value="studio">Studio-wide only</option>
            {(projects.data ?? []).map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
          <label className="check-label">
            <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Archived
          </label>
        </div>
        <DocumentList
          filters={{
            q: q.trim() || undefined,
            kind: kind ? [kind] : undefined,
            studio_wide: scope === "studio" || undefined,
            project: scope && scope !== "studio" ? scope : undefined,
            archived,
            sort: "updated_at",
          }}
          onOpen={(d) => setOpenId(d.id)}
          emptyTitle="No documents match"
          emptyText={can("documents.write") ? "Create a document, or change the filters." : "Nothing here yet."}
        />
      </div>
      <p className="small-note">Documents are Markdown text stored in Booski Core. File uploads and attachments arrive in a later phase.</p>
      {creating && <DocumentEditorModal onClose={() => setCreating(false)} onSaved={(d) => setOpenId(d.id)} />}
      {openId && <DocumentViewerModal key={openId} documentId={openId} onClose={() => setOpenId(null)} />}
    </div>
  );
}
