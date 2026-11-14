import { useState } from "react";
import { FileText, Plus, Upload } from "lucide-react";
import { PageHeading, SearchField } from "../components/common";
import { DocumentEditorModal } from "../components/knowledge/DocumentEditorModal";
import { DocumentList } from "../components/knowledge/DocumentList";
import { DocumentViewerModal } from "../components/knowledge/DocumentViewerModal";
import { useToast } from "../context/ToastContext";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { useDocumentParam } from "./StudioKnowledgePage";

/**
 * `/research` — research documents (knowledge documents of type "Research"). Uploading files such as
 * PDFs needs file storage, which arrives in a later phase; until then research is written as text.
 */
export function ResearchPage() {
  const notify = useToast();
  const { can } = useWorkspace();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useDocumentParam();

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="SHARED KNOWLEDGE / RESEARCH"
        title="Research Library"
        description="Market research, competitor notes and source material, stored as research documents in the knowledge base."
        source="live"
      />
      <div className="research-actions">
        {can("documents.write") && (
          <button type="button" className="primary-btn" onClick={() => setCreating(true)}>
            <Plus size={14} aria-hidden="true" /> New research document
          </button>
        )}
        <button
          type="button"
          className="upload-button"
          onClick={() => notify("File uploads (PDF, DOCX, spreadsheets…) arrive with file storage in a later phase. Nothing was uploaded.")}
        >
          <Upload size={16} aria-hidden="true" /> Upload files
        </button>
        <span>File uploads: planned for a later phase</span>
      </div>
      <div className="panel knowledge-doc-list">
        <div className="filter-bar" role="search" aria-label="Search research">
          <SearchField value={q} onChange={setQ} placeholder="Search research titles…" />
          <FileText size={16} className="muted-text" aria-hidden="true" />
        </div>
        <DocumentList
          filters={{ kind: ["research"], q: q.trim() || undefined, sort: "updated_at" }}
          onOpen={(d) => setOpenId(d.id)}
          emptyTitle="No research yet"
          emptyText="Research documents you write will appear here."
        />
      </div>
      {creating && <DocumentEditorModal defaults={{ kind: "research" }} onClose={() => setCreating(false)} onSaved={(d) => setOpenId(d.id)} />}
      {openId && <DocumentViewerModal key={openId} documentId={openId} onClose={() => setOpenId(null)} />}
    </div>
  );
}
