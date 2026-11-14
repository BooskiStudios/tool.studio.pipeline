import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { CalendarDays, ChevronRight, Compass, FolderKanban, ListTodo, type LucideIcon } from "lucide-react";
import { useTaskList } from "../api/hooks";
import type { TaskStatus } from "../api/types";
import { AgentWorkflowCanvas } from "../components/AgentWorkflowCanvas";
import { EmptyState, ResourceView } from "../components/common";
import { TaskDetailModal } from "../components/tasks/TaskDetailModal";
import { TaskRecord } from "../components/tasks/TaskRecord";
import { useTaskLabels, useToggleTask } from "../components/tasks/useTaskHelpers";
import { LoadingState, LoadMore, ProgressBar, QueryView } from "../components/ui";
import { useProjects } from "../context/ProjectContext";
import { useResource } from "../hooks/useResource";
import { formatDate, PROJECT_STATUS, projectImage } from "../lib/format";
import { paths } from "../routes";
import { studioApi } from "../services";

const VIEWS: { label: string; icon: LucideIcon }[] = [
  { label: "Overview", icon: Compass },
  { label: "Projects & Roadmaps", icon: FolderKanban },
  { label: "Tasks & Milestones", icon: ListTodo },
  { label: "Studio Calendar", icon: CalendarDays },
];
const OPEN: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "blocked"];

function ProjectsRoadmap() {
  const navigate = useNavigate();
  const { projects } = useProjects();
  if (!projects) return <LoadingState label="projects" />;
  if (projects.length === 0) return <EmptyState icon={FolderKanban} title="No projects yet">Projects appear here with their progress.</EmptyState>;
  return (
    <div className="roadmap-list">
      {projects.map((p) => (
        <button type="button" className="work-item" key={p.id} onClick={() => navigate(paths.project(p.slug))}>
          <span className="work-icon"><img src={projectImage(p)} alt="" className="work-thumb" /></span>
          <span className="work-copy">
            <b>{p.name}</b>
            <small>{PROJECT_STATUS[p.status]} · {p.progress.done}/{p.progress.total} tasks done</small>
            <ProgressBar percent={p.progress.percent} label={`${p.name} progress`} />
          </span>
          <span className="work-status">{p.progress.percent}%</span>
          <ChevronRight size={17} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}

function UpcomingTasks({ dueOnly }: { dueOnly: boolean }) {
  const tasks = useTaskList({ status: OPEN, sort: "due_date" });
  const labels = useTaskLabels();
  const { toggle, pendingId } = useToggleTask();
  const [open, setOpen] = useState<string | null>(null);
  const rows = dueOnly ? tasks.items.filter((t) => t.due_date) : tasks.items;
  return (
    <QueryView query={tasks} label="tasks">
      {() => (
        <>
          {rows.length === 0 ? (
            <EmptyState icon={CalendarDays} title={dueOnly ? "No upcoming deadlines" : "No open tasks"}>
              {dueOnly ? "Tasks with due dates appear here in date order." : "Open tasks appear here, soonest due first."}
            </EmptyState>
          ) : dueOnly ? (
            rows.map((t, i) => (
              <div key={t.id}>
                {(i === 0 || rows[i - 1].due_date !== t.due_date) && <div className="calendar-day">{formatDate(t.due_date)}</div>}
                <TaskRecord task={t} context={labels(t)} onToggle={toggle} onOpen={(x) => setOpen(x.id)} busy={pendingId === t.id} />
              </div>
            ))
          ) : (
            rows.map((t) => <TaskRecord key={t.id} task={t} context={labels(t)} onToggle={toggle} onOpen={(x) => setOpen(x.id)} busy={pendingId === t.id} />)
          )}
          <LoadMore {...tasks} />
          {open && <TaskDetailModal taskId={open} onClose={() => setOpen(null)} />}
        </>
      )}
    </QueryView>
  );
}

/** `/operations` (`?view=…` selects a management area) — studio management and the agent workflow preview. */
export function StudioOperationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("view");
  const selected = VIEWS.some((v) => v.label === requested) ? requested! : VIEWS[0].label;
  const agents = useResource(() => studioApi.listAgentNodes(), []);
  const { projects } = useProjects();
  const selectView = (label: string) => setSearchParams(label === VIEWS[0].label ? {} : { view: label });

  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">BOOSKI STUDIOS / MANAGEMENT</span>
        <h1>Studio Operations</h1>
        <p>Manage studio priorities, projects and schedules, and preview how AI capabilities will coordinate work across departments.</p>
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
          <div className="status-line"><span>Projects</span><b>{projects ? projects.length : "…"}</b></div>
          <div className="status-line"><span>AI agents</span><b className="muted-text">Preview · Phase 3</b></div>
        </aside>
        <section className="panel operations-canvas-panel">
          <div className="panel-title">
            <div>
              <h2>{selected === "Overview" ? "AI Workforce & Live Workflow" : selected}</h2>
              <small className="canvas-subtitle">
                {selected === "Overview" ? "Preview of agent coordination · Not connected to live execution" : "Live data from Booski Core"}
              </small>
            </div>
            {selected === "Overview" ? <span className="live-pill"><i aria-hidden="true" /> PREVIEW</span> : <span className="live-chip">LIVE</span>}
          </div>
          {selected === "Overview" && (
            <ResourceView resource={agents} label="agents">
              {(nodes) => <AgentWorkflowCanvas agents={nodes} />}
            </ResourceView>
          )}
          {selected === "Projects & Roadmaps" && <ProjectsRoadmap />}
          {selected === "Tasks & Milestones" && <UpcomingTasks dueOnly={false} />}
          {selected === "Studio Calendar" && <UpcomingTasks dueOnly />}
        </section>
      </div>
    </div>
  );
}
