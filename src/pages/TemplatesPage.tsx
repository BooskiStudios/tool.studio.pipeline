import { useState } from "react";
import { FileText, Layers, SearchX, Upload } from "lucide-react";
import { EmptyState, matchesQuery, ResourceView, SearchField } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/templates` — reusable studio document templates. */
export function TemplatesPage() {
  const notify = useToast();
  const templates = useResource(() => studioApi.listTemplates(), []);
  const [query, setQuery] = useState("");

  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">SHARED KNOWLEDGE / TEMPLATES</span>
        <h1>Template Library</h1>
        <p>Reusable studio documents that Booski can duplicate and populate when starting new work.</p>
      </div>
      <div className="template-toolbar">
        <SearchField value={query} onChange={setQuery} placeholder="Search templates..." />
        <button type="button" className="secondary-btn" onClick={() => notify("Adding custom templates will be supported by the file library.")}>
          <Upload size={14} aria-hidden="true" /> Add template
        </button>
      </div>
      <ResourceView resource={templates} label="templates">
        {(rows) => {
          const visible = rows.filter((t) => matchesQuery(query, t.name, t.description, t.category));
          if (visible.length === 0) {
            return <EmptyState icon={SearchX} title="No templates found">No templates match “{query}”.</EmptyState>;
          }
          return (
            <div className="template-grid">
              {visible.map((t) => (
                <article className="panel template-card" key={t.id}>
                  <div className="template-card-top">
                    <span className="work-icon"><FileText size={19} aria-hidden="true" /></span>
                    <span className="template-category">{t.category}</span>
                  </div>
                  <b>{t.name}</b>
                  <p>{t.description}</p>
                  <div>
                    <button type="button" className="secondary-btn" onClick={() => notify(`Previewing ${t.name} template.`)}>Preview</button>
                    <button type="button" className="primary-btn" onClick={() => notify(`Booski would duplicate ${t.name} and use the copy as a working document.`)}>
                      <Layers size={14} aria-hidden="true" /> Use template
                    </button>
                  </div>
                </article>
              ))}
            </div>
          );
        }}
      </ResourceView>
    </div>
  );
}
