import { Network } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/integrations` — external tools and platforms (none connected yet). */
export function IntegrationsHubPage() {
  const notify = useToast();
  const integrations = useResource(() => studioApi.listIntegrations(), []);
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / CONNECTIONS"
        title="Integrations Hub"
        description="Connect the tools and platforms used across the studio, then control which agents can access each connection."
        source="planned"
      />
      <ResourceView resource={integrations} label="integrations">
        {(rows) => (
          <div className="integration-grid">
            {rows.map((i) => (
              <article className="panel integration-card" key={i.id}>
                <div className="integration-mark"><Network size={19} aria-hidden="true" /></div>
                <div>
                  <b>{i.name}</b>
                  <small>{i.category}</small>
                </div>
                <span>{i.status}</span>
                <button type="button" className="secondary-btn" onClick={() => notify(`${i.name} connection setup will be handled in the integration phase.`)}>
                  {i.status === "Planned" ? "Planned" : "Configure"}
                </button>
              </article>
            ))}
          </div>
        )}
      </ResourceView>
    </div>
  );
}
