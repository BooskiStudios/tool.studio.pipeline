import { ArrowUpRight, BookOpen } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/knowledge` — studio-wide and project-specific knowledge. */
export function StudioKnowledgePage() {
  const notify = useToast();
  const docs = useResource(() => studioApi.listKnowledgeDocs(), []);
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / KNOWLEDGE"
        title="Studio Knowledge Base"
        description="Shared studio knowledge alongside project-specific documentation. Agents retrieve relevant context without mixing unrelated project decisions."
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
          <p>Game-specific designs, decisions, references, architecture and production notes.</p>
        </article>
      </div>
      <div className="panel knowledge-doc-list">
        <ResourceView resource={docs} label="knowledge documents">
          {(rows) =>
            rows.map((d) => (
              <div className="knowledge-doc" key={d.id}>
                <span className="work-icon"><BookOpen size={18} aria-hidden="true" /></span>
                <div>
                  <b>{d.title}</b>
                  <small>{d.detail}</small>
                </div>
                <span>{d.scope}</span>
                <button type="button" onClick={() => notify(`Opening ${d.title} requires the connected knowledge store.`)} aria-label={`Open ${d.title}`}>
                  <ArrowUpRight size={15} aria-hidden="true" />
                </button>
              </div>
            ))
          }
        </ResourceView>
      </div>
    </div>
  );
}
