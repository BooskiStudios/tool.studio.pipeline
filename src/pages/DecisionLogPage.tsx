import { PageHeading } from "../components/common";
import { DecisionLogList } from "../components/DecisionLogList";

/** `/decisions` — the central Decision Log. */
export function DecisionLogPage() {
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / GOVERNANCE"
        title="Decision Log"
        description="A searchable record of important decisions, who made or recommended them, the context and the reasoning behind them."
      />
      <DecisionLogList />
      <p className="small-note">Sample entries illustrate the intended structure. Future records will distinguish AI recommendations, human approvals and final studio decisions.</p>
    </div>
  );
}
