import { useState } from "react";
import { useSearchParams } from "react-router";
import { Plus } from "lucide-react";
import { ApprovalList } from "../components/approvals/ApprovalList";
import { ApprovalDetailModal, ApprovalRequestModal } from "../components/approvals/ApprovalModals";
import { PageHeading } from "../components/common";
import { useWorkspace } from "../workspace/WorkspaceProvider";

type View = "waiting" | "mine" | "open" | "resolved";

const VIEWS: { id: View; label: string }[] = [
  { id: "waiting", label: "Waiting for you" },
  { id: "mine", label: "Submitted by you" },
  { id: "open", label: "All open" },
  { id: "resolved", label: "Resolved" },
];

const LISTS = {
  waiting: {
    filters: { status: ["pending"] },
    only: (a: { can_decide: boolean }) => a.can_decide,
    emptyTitle: "Nothing waiting for you",
    emptyText: "Requests you can approve, reject or send back appear here.",
  },
  mine: {
    filters: { requested_by: "me" },
    only: undefined,
    emptyTitle: "You haven't requested any approvals",
    emptyText: "Requests you submit, and their outcome, appear here.",
  },
  open: {
    filters: { status: ["pending", "changes_requested"] },
    only: undefined,
    emptyTitle: "No open requests",
    emptyText: "Requests waiting for review or for changes appear here.",
  },
  resolved: {
    filters: { status: ["approved", "rejected", "cancelled"] },
    only: undefined,
    emptyTitle: "No resolved requests",
    emptyText: "Approved, rejected and cancelled requests appear here.",
  },
} as const;

/** `/approvals` — the review queue (`?approval=<id>` opens one). */
export function ApprovalsCentrePage() {
  const { can } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<View>("waiting");
  const [requesting, setRequesting] = useState(false);
  const openId = params.get("approval");
  const setOpen = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set("approval", id);
    else next.delete("approval");
    setParams(next, { replace: !id });
  };
  const list = LISTS[view];

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI STUDIOS / GOVERNANCE"
        title="Approvals Centre"
        description="A single review queue for work that needs someone's permission before it goes ahead."
        source="live"
        actions={
          can("approvals.request") && (
            <button type="button" className="primary-btn" onClick={() => setRequesting(true)}>
              <Plus size={14} aria-hidden="true" /> Request approval
            </button>
          )
        }
      />
      <div className="workspace-tabs" role="group" aria-label="Approval views">
        {VIEWS.map((v) => (
          <button type="button" key={v.id} aria-pressed={view === v.id} className={view === v.id ? "active-tab" : ""} onClick={() => setView(v.id)}>
            {v.label}
          </button>
        ))}
      </div>
      <div className="panel approvals-list">
        <ApprovalList key={view} filters={list.filters} only={list.only} onOpen={(a) => setOpen(a.id)} emptyTitle={list.emptyTitle} emptyText={list.emptyText} />
      </div>
      <p className="small-note">
        Approving a request records the decision. It doesn't execute, publish or spend anything automatically; that arrives with AI orchestration in Phase 3.
      </p>
      {requesting && <ApprovalRequestModal onClose={() => setRequesting(false)} />}
      {openId && <ApprovalDetailModal key={openId} approvalId={openId} onClose={() => setOpen(null)} />}
    </div>
  );
}
