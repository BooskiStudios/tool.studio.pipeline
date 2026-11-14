import { Clock3 } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/activity` — chronological agent activity and audit trail (illustrative). */
export function ActivityAuditPage() {
  const events = useResource(() => studioApi.listAuditEvents(), []);
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / TRACEABILITY"
        title="Activity & Audit"
        description="A chronological record of agent activity, task changes, file operations and approvals. This is the foundation for investigating and recovering from problems."
      />
      <div className="panel audit-list">
        <ResourceView resource={events} label="activity">
          {(rows) =>
            rows.map((e) => (
              <div className="audit-row" key={e.id}>
                <span className="audit-mark"><Clock3 size={16} aria-hidden="true" /></span>
                <div>
                  <b>{e.action}</b>
                  <small>{e.agent} · {e.department}</small>
                </div>
                <time>{e.time}</time>
              </div>
            ))
          }
        </ResourceView>
      </div>
      <p className="small-note">Illustrative records only. Live audit events will be written by Booski Core and retained according to configurable policies.</p>
    </div>
  );
}
