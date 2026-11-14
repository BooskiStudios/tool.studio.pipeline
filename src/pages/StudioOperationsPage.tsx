import { useSearchParams } from "react-router";
import { CalendarDays, ChevronRight, Compass, FolderKanban, ListTodo, Workflow, type LucideIcon } from "lucide-react";
import { AgentWorkflowCanvas } from "../components/AgentWorkflowCanvas";
import { EmptyState, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

const VIEWS: { label: string; icon: LucideIcon }[] = [
  { label: "Overview", icon: Compass },
  { label: "Projects & Roadmaps", icon: FolderKanban },
  { label: "Tasks & Milestones", icon: ListTodo },
  { label: "Studio Calendar", icon: CalendarDays },
];

/** `/operations` (`?view=…` selects a management area) — studio management and the agent workflow canvas. */
export function StudioOperationsPage() {
  const notify = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("view");
  const selected = VIEWS.some((v) => v.label === requested) ? requested! : VIEWS[0].label;
  const agents = useResource(() => studioApi.listAgentNodes(), []);

  const selectView = (label: string) => setSearchParams(label === VIEWS[0].label ? {} : { view: label });

  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">BOOSKI STUDIOS / MANAGEMENT</span>
        <h1>Studio Operations</h1>
        <p>Manage studio priorities, projects and schedules, and see how AI capabilities coordinate work across departments.</p>
      </div>
      <div className="operations-layout">
        <aside className="panel operations-menu">
          <div className="panel-title"><h2>Studio management</h2></div>
          {VIEWS.map(({ label, icon: ViewIcon }) => (
            <button type="button" key={label} className={selected === label ? "ops-active" : ""} onClick={() => selectView(label)} aria-pressed={selected === label}>
              <span><ViewIcon size={16} aria-hidden="true" /></span>
              {label}
              <ChevronRight size={14} aria-hidden="true" />
            </button>
          ))}
          <div className="side-divider" />
          <div className="status-line"><span>Agents registered</span><b>6 demo agents</b></div>
          <div className="status-line"><span>Running tasks</span><b className="green-text">5 demo tasks</b></div>
        </aside>
        <section className="panel operations-canvas-panel">
          <div className="panel-title">
            <div>
              <h2>{selected === "Overview" ? "AI Workforce & Live Workflow" : selected}</h2>
              <small className="canvas-subtitle">Illustrative agent activity · Not connected to live execution</small>
            </div>
            <span className="live-pill"><i aria-hidden="true" /> DEMO LIVE VIEW</span>
          </div>
          {selected === "Overview" ? (
            <ResourceView resource={agents} label="agents">
              {(nodes) => <AgentWorkflowCanvas agents={nodes} />}
            </ResourceView>
          ) : (
            <div className="ops-detail">
              <EmptyState
                icon={Workflow}
                title={selected}
                action={<button type="button" className="secondary-btn" onClick={() => notify(`${selected} workspace is prepared for backend integration.`)}>Open workspace</button>}
              >
                This management area will display live studio records once the Booski Core database and workflows are connected.
              </EmptyState>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
