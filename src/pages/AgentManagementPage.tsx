import { ArrowUpRight, Bot } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/agents` — the specialist AI workforce. */
export function AgentManagementPage() {
  const notify = useToast();
  const agents = useResource(() => studioApi.listAgents(), []);
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / WORKFORCE"
        title="Agent Management"
        description="Manage the specialist AI workforce, review responsibilities and understand which tools and permissions each agent can use."
      />
      <ResourceView resource={agents} label="agents">
        {(rows) => (
          <div className="agent-management-grid">
            {rows.map((a) => (
              <article className="panel managed-agent" key={a.name}>
                <div className="managed-agent-top">
                  <span className="work-icon"><Bot size={20} aria-hidden="true" /></span>
                  <span className={`agent-status ${a.status.toLowerCase()}`}>{a.status}</span>
                </div>
                <h3>{a.name}</h3>
                <p>{a.role}</p>
                <div className="agent-meta">
                  <small>Department</small>
                  <b>{a.department}</b>
                  <small>Assigned work</small>
                  <span>{a.work}</span>
                  <small>Model</small>
                  <b>{a.model}</b>
                  <small>Permissions</small>
                  <span>{a.permissions}</span>
                </div>
                <button type="button" className="secondary-btn" onClick={() => notify(`${a.name} configuration will be editable when the agent registry is connected.`)}>
                  Configure agent <ArrowUpRight size={14} aria-hidden="true" />
                </button>
              </article>
            ))}
          </div>
        )}
      </ResourceView>
    </div>
  );
}
