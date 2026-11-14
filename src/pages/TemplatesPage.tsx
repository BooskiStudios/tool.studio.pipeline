import { useState } from "react";
import { FileText, Layers, Plus, SearchX } from "lucide-react";
import { errorMessage } from "../api/client";
import * as core from "../api/core";
import { useDocumentList } from "../api/hooks";
import type { DocumentSummary } from "../api/types";
import { EmptyState, PageHeading, SearchField } from "../components/common";
import { DocumentEditorModal, type DocumentDefaults } from "../components/knowledge/DocumentEditorModal";
import { DocumentViewerModal } from "../components/knowledge/DocumentViewerModal";
import { LoadMore, QueryView } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { useDocumentParam } from "./StudioKnowledgePage";

/**
 * `/templates` — reusable documents (knowledge documents of type "Template"). "Use template" starts a
 * new document from a copy of the template's text; the template itself is never changed.
 */
export function TemplatesPage() {
  const notify = useToast();
  const { slug, can } = useWorkspace();
  const [q, setQ] = useState("");
  const templates = useDocumentList({ kind: ["template"], q: q.trim() || undefined, sort: "title" });
  const [openId, setOpenId] = useDocumentParam();
  const [editorDefaults, setEditorDefaults] = useState<DocumentDefaults | null>(null);
  const canWrite = can("documents.write");

  const startFromTemplate = async (template: DocumentSummary) => {
    try {
      const full = await core.documents.get(slug, template.id);
      setEditorDefaults({ kind: "note", title: `${template.title} — copy`, body: full.body, project_id: template.project_id });
    } catch (error) {
      notify(errorMessage(error));
    }
  };

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="SHARED KNOWLEDGE / TEMPLATES"
        title="Template Library"
        description="Reusable studio documents. Start new work from a copy, so the template stays intact."
        source="live"
      />
      <div className="template-toolbar">
        <SearchField value={q} onChange={setQ} placeholder="Search templates..." />
        {canWrite && (
          <button type="button" className="secondary-btn" onClick={() => setEditorDefaults({ kind: "template" })}>
            <Plus size={14} aria-hidden="true" /> Add template
          </button>
        )}
      </div>
      <QueryView query={templates} label="templates">
        {() =>
          templates.items.length === 0 ? (
            <EmptyState icon={SearchX} title={q ? "No templates found" : "No templates yet"}>
              {q ? `No templates match “${q}”.` : "Templates you add will appear here."}
            </EmptyState>
          ) : (
            <>
              <div className="template-grid">
                {templates.items.map((t) => (
                  <article className="panel template-card" key={t.id}>
                    <div className="template-card-top">
                      <span className="work-icon"><FileText size={19} aria-hidden="true" /></span>
                      <span className="template-category">{t.tags[0] ?? "Template"}</span>
                    </div>
                    <b>{t.title}</b>
                    <p>{t.summary || "No summary."}</p>
                    <div>
                      <button type="button" className="secondary-btn" onClick={() => setOpenId(t.id)}>Preview</button>
                      {canWrite && (
                        <button type="button" className="primary-btn" onClick={() => void startFromTemplate(t)}>
                          <Layers size={14} aria-hidden="true" /> Use template
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
              <LoadMore {...templates} />
            </>
          )
        }
      </QueryView>
      {editorDefaults && (
        <DocumentEditorModal defaults={editorDefaults} onClose={() => setEditorDefaults(null)} onSaved={(d) => setOpenId(d.id)} />
      )}
      {openId && <DocumentViewerModal key={openId} documentId={openId} onClose={() => setOpenId(null)} />}
    </div>
  );
}
