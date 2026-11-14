import { ShieldCheck } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

/** `/approvals` — actions waiting for your permission (demo only; nothing is executed). */
export function ApprovalsCentrePage() {
  const notify = useToast();
  const approvals = useResource(() => studioApi.listApprovals(), []);
  return (
    <div className="workspace-page">
      <PageHeading eyebrow="BOOSKI AI CORE / GOVERNANCE" title="Approvals Centre" description="A single review queue for actions that need your permission before an agent proceeds." />
      <div className="panel approvals-list">
        <ResourceView resource={approvals} label="approvals">
          {(rows) =>
            rows.map((a) => (
              <div className="approval-row" key={a.id}>
                <span className="work-icon"><ShieldCheck size={19} aria-hidden="true" /></span>
                <div>
                  <b>{a.title}</b>
                  <small>{a.agent} · {a.department} · {a.kind}</small>
                </div>
                <button type="button" className="secondary-btn" onClick={() => notify("Approval details are demo-only until workflow execution is connected.")}>Review</button>
              </div>
            ))
          }
        </ResourceView>
      </div>
      <p className="small-note">No action is actually approved or executed in this frontend preview.</p>
    </div>
  );
}
