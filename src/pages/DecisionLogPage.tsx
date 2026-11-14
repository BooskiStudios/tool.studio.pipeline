import { PageHeading } from "../components/common";
import { DecisionLogList } from "../components/DecisionLogList";

/** `/decisions` — the central Decision Log (`?decision=<id>` opens one). */
export function DecisionLogPage() {
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI STUDIOS / GOVERNANCE"
        title="Decision Log"
        description="A permanent record of important decisions: the context, the options considered, the outcome and the reasoning."
        source="live"
      />
      <DecisionLogList />
      <p className="small-note">Decisions are never deleted. To change course, supersede a decision so its history stays intact.</p>
    </div>
  );
}
