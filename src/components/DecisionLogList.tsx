import { useState } from "react";
import { ChevronRight, ClipboardList } from "lucide-react";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";
import { EmptyState, ResourceView } from "./common";
import { departmentNames } from "./layout/navigation";

const ALL = "All departments";
const filterOptions = ["Studio Operations", ...Object.values(departmentNames)];

/**
 * The central Decision Log with a department filter. Used on the Decision Log
 * page (in a panel) and inside each department's "Decision Log" tab (`embedded`).
 */
export function DecisionLogList({ initialDepartment, embedded = false }: { initialDepartment?: string; embedded?: boolean }) {
  const decisions = useResource(() => studioApi.listDecisions(), []);
  const [filter, setFilter] = useState(initialDepartment ?? ALL);

  const content = (
    <ResourceView resource={decisions} label="decisions">
      {(rows) => {
        const visible = filter === ALL ? rows : rows.filter((r) => r.department === filter);
        return (
          <>
            <div className="decision-toolbar">
              <span>{visible.length} recorded {visible.length === 1 ? "decision" : "decisions"}</span>
              <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter decisions by department">
                <option>{ALL}</option>
                {filterOptions.map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            {visible.length === 0 ? (
              <EmptyState icon={ClipboardList} title="No decisions recorded yet">
                {filter === ALL ? "Decisions" : `${filter} decisions`} will appear here once they are recorded. Choose another department to see existing sample entries.
              </EmptyState>
            ) : (
              visible.map((r) => (
                <article className="decision-row" key={r.id}>
                  <div className="decision-date">{r.date}</div>
                  <div className="decision-main">
                    <b>{r.decision}</b>
                    <p>{r.reason}</p>
                    <div className="decision-tags">
                      <span>{r.department}</span>
                      <span>{r.agent}</span>
                      <span>{r.type}</span>
                    </div>
                  </div>
                  <ChevronRight size={16} aria-hidden="true" />
                </article>
              ))
            )}
          </>
        );
      }}
    </ResourceView>
  );

  return <div className={embedded ? "decision-embedded" : "panel decision-panel"}>{content}</div>;
}
