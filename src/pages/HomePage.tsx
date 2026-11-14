import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronDown, ChevronRight, Circle, Gamepad2, Plus } from "lucide-react";
import { useMe } from "../auth/AuthProvider";
import { useActivity, useApprovalList, useDepartments, useMilestones, useTaskList } from "../api/hooks";
import type { Department, Project, TaskStatus } from "../api/types";
import { ActivityList } from "../components/ActivityList";
import { EmptyState, ResourceView } from "../components/common";
import { Icon } from "../components/Icon";
import { ErrorState, LoadingState, ProgressBar, QueryView, SourceChip } from "../components/ui";
import { useTaskLabels, useToggleTask } from "../components/tasks/useTaskHelpers";
import { departmentPresentation, NAV_HIDDEN_DEPARTMENTS } from "../config/departments";
import { useProjects } from "../context/ProjectContext";
import { useTasks } from "../context/TasksContext";
import { useResource } from "../hooks/useResource";
import { MILESTONE_STATUS, PROJECT_STATUS, projectImage } from "../lib/format";
import { paths, recordLinks } from "../routes";
import { studioApi } from "../services";
import type { CommandCentrePreview } from "../types";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const PERIODS = ["This Month", "This Week", "This Year"];
const OPEN: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "blocked"];

function PreviewLabel() {
  return <span className="demo-label">PREVIEW · LATER PHASE</span>;
}

function DepartmentCards({ departments }: { departments: Department[] }) {
  const navigate = useNavigate();
  const visible = departments.filter((d) => !NAV_HIDDEN_DEPARTMENTS.has(d.slug));
  return (
    <section className={`department-grid count-${visible.length}`} aria-label="Departments">
      {visible.map((d) => (
        <button
          type="button"
          key={d.id}
          className={`department-card ${d.accent_color}`}
          style={{ backgroundImage: `linear-gradient(90deg,rgba(3,10,20,.94),rgba(3,10,20,.55) 60%,rgba(3,10,20,.1)),url(${departmentPresentation(d.slug).image})` }}
          onClick={() => navigate(paths.department(d.slug))}
        >
          <div className="department-icon"><Icon name={d.icon_key} size={27} /></div>
          <div className="department-copy">
            <b>{d.name}</b>
            <p>{d.description}</p>
          </div>
          <span className="department-arrow"><ArrowRight size={22} aria-hidden="true" /></span>
        </button>
      ))}
    </section>
  );
}

function ProjectOverview({ project, projects }: { project: Project; projects: Project[] }) {
  const navigate = useNavigate();
  const { selectProject } = useProjects();
  const [menuOpen, setMenuOpen] = useState(false);
  const milestones = useMilestones(project.slug);

  return (
    <article className="panel project-overview">
      <div className="panel-title">
        <h2>Project Overview</h2>
        <div className="overview-select">
          <button type="button" onClick={() => setMenuOpen((o) => !o)} aria-expanded={menuOpen} aria-label={`Selected project: ${project.name}. Change project`}>
            {project.name}
            <ChevronDown size={14} aria-hidden="true" />
          </button>
          {menuOpen && (
            <div className="overview-menu">
              {projects.map((p) => (
                <button
                  type="button"
                  key={p.id}
                  aria-current={p.slug === project.slug ? "true" : undefined}
                  onClick={() => {
                    selectProject(p.slug);
                    setMenuOpen(false);
                  }}
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="project-summary">
        <img src={projectImage(project)} alt="" />
        <div className="summary-copy">
          <b>{project.name}</b>
          <div className="tags">
            <span>{PROJECT_STATUS[project.status]}</span>
            {project.project_type && <span>{project.project_type}</span>}
            {project.engine && <span>{project.engine}</span>}
          </div>
          <p>{project.description || "No description yet."}</p>
          <ProgressBar percent={project.progress.percent} label={`${project.name} progress`} />
        </div>
        <strong>{project.progress.percent}%</strong>
      </div>
      <div className="milestones">
        {milestones.isPending && <small className="muted-text">Loading milestones…</small>}
        {milestones.data?.length === 0 && <small className="muted-text">No milestones yet.</small>}
        {milestones.data?.slice(0, 4).map((m, i) => (
          <div key={m.id}>
            <span className={`milestone-dot m${i}`}><Check size={13} aria-hidden="true" /></span>
            <span>{m.name}</span>
            <small>{m.status === "completed" ? MILESTONE_STATUS.completed : `${m.progress.percent}%`}</small>
          </div>
        ))}
      </div>
      <button type="button" className="inline-link" onClick={() => navigate(paths.project(project.slug))}>
        Open full project workspace <ArrowUpRight size={14} aria-hidden="true" />
      </button>
    </article>
  );
}

function CurrentFocus() {
  const navigate = useNavigate();
  const { can } = useWorkspace();
  const { openTaskForm } = useTasks();
  const mine = useTaskList({ assignee: "me", status: [...OPEN, "done"], sort: "due_date", limit: 100 });
  const { toggle, pendingId } = useToggleTask();
  const labels = useTaskLabels();
  const done = mine.items.filter((t) => t.status === "done").length;
  const open = mine.items.filter((t) => t.status !== "done");
  const pct = Math.round((done / Math.max(mine.items.length, 1)) * 100);
  const next = open[0];

  return (
    <article className="panel focus-panel">
      <div className="panel-title">
        <h2>Current Focus</h2>
        <button type="button" onClick={() => navigate(paths.tasks)}>View Tasks <ArrowUpRight size={14} aria-hidden="true" /></button>
      </div>
      <QueryView query={mine} label="your tasks">
        {() => (
          <>
            <div className="focus-card">
              <div className="focus-icon"><Gamepad2 size={22} aria-hidden="true" /></div>
              <div className="focus-content">
                <b>{next ? next.title : "Nothing assigned to you"}</b>
                <div>
                  {next && <span>{labels(next).projectName ?? "Studio-wide"}</span>}
                  {next && <span className="priority">{next.priority.toUpperCase()}</span>}
                </div>
                <small>{done}/{mine.items.length} of your tasks completed</small>
              </div>
              <div className="progress-ring" style={{ background: `conic-gradient(#4bc8ec ${pct}%,#243447 0)` }} role="img" aria-label={`${pct}% of your tasks completed`}>
                <span>{pct}%</span>
              </div>
            </div>
            <div className="task-list">
              {open.slice(0, 5).map((t) => (
                <button type="button" key={t.id} onClick={() => toggle(t)} aria-pressed={false} disabled={!t.can_edit || pendingId === t.id}>
                  <Circle className="task-open" size={18} aria-hidden="true" />
                  <span>{t.title}</span>
                </button>
              ))}
              {mine.items.filter((t) => t.status === "done").slice(0, Math.max(0, 5 - open.length)).map((t) => (
                <button type="button" key={t.id} onClick={() => toggle(t)} aria-pressed disabled={!t.can_edit || pendingId === t.id}>
                  <CheckCircle2 className="task-done" size={18} aria-hidden="true" />
                  <span className="done">{t.title}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </QueryView>
      {can("tasks.create") && (
        <button type="button" className="inline-add" onClick={() => openTaskForm()}><Plus size={14} aria-hidden="true" /> Add task</button>
      )}
    </article>
  );
}

function StudioInsights({ data }: { data: CommandCentrePreview }) {
  const [period, setPeriod] = useState(PERIODS[0]);
  return (
    <article className="panel insights-panel">
      <div className="panel-title">
        <h2>Studio Insights</h2>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} aria-label="Insights period">
          {PERIODS.map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>
      <PreviewLabel />
      <div className="stats-grid">
        {data.insights.map((s) => (
          <div className="stat" key={s.label}>
            <small>{s.label}</small>
            <b>{s.value}</b>
            <em>↑ {s.change}</em>
          </div>
        ))}
      </div>
      <div className="chart-heading">Overall productivity <b>{data.productivityChange}</b></div>
      <svg className="sparkline" viewBox="0 0 360 64" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 51 C20 48 25 57 42 49 S68 39 83 46 S108 37 126 42 S151 24 169 34 S194 19 211 31 S236 12 253 23 S275 9 292 19 S321 9 337 17 S350 10 360 14" fill="none" stroke="#ff238c" strokeWidth="2.5" />
      </svg>
    </article>
  );
}

function Metrics() {
  const me = useMe();
  const { projects } = useProjects();
  const openTasks = useTaskList({ status: OPEN, limit: 200 });
  const mineOpen = openTasks.items.filter((t) => t.assignee_user_id === me.user.id).length;
  const waiting = useApprovalList({ status: ["pending"], limit: 200 });
  const toReview = waiting.items.filter((a) => a.can_decide).length;
  const more = (hasMore: boolean) => (hasMore ? "+" : "");
  const metrics = [
    { id: "projects", label: "Active projects", value: projects ? String(projects.length) : "…", note: "Visible to you", icon: "folder", tone: "cyan" },
    { id: "tasks", label: "Open tasks", value: openTasks.isPending ? "…" : `${openTasks.items.length}${more(openTasks.hasNextPage)}`, note: `${mineOpen} assigned to you`, icon: "file-text", tone: "pink" },
    { id: "review", label: "Awaiting your review", value: waiting.isPending ? "…" : String(toReview), note: "Approval requests", icon: "shield", tone: "orange" },
    { id: "pending", label: "Open approval requests", value: waiting.isPending ? "…" : `${waiting.items.length}${more(waiting.hasNextPage)}`, note: "Across the workspace", icon: "workflow", tone: "green" },
  ] as const;
  return (
    <section className="command-metrics" aria-label="Studio metrics">
      {metrics.map((m) => (
        <div className="panel command-metric" key={m.id}>
          <span className={`metric-icon ${m.tone}`}><Icon name={m.icon} size={18} /></span>
          <small>{m.label}</small>
          <b>{m.value}</b>
          <em>{m.note}</em>
        </div>
      ))}
    </section>
  );
}

function NeedsAttention() {
  const navigate = useNavigate();
  const pending = useApprovalList({ status: ["pending"], limit: 50 });
  const mine = pending.items.filter((a) => a.can_decide).slice(0, 4);
  return (
    <article className="panel command-approvals">
      <div className="panel-title">
        <h2>Needs your attention</h2>
        <button type="button" onClick={() => navigate(paths.approvals)}>View all <ArrowUpRight size={14} aria-hidden="true" /></button>
      </div>
      <QueryView query={pending} label="approvals">
        {() =>
          mine.length === 0 ? (
            <p className="muted-text">Nothing is waiting for your review.</p>
          ) : (
            mine.map((a) => (
              <button type="button" className="attention-row" key={a.id} onClick={() => navigate(recordLinks.approval(a.id))}>
                <span className="attention-dot" aria-hidden="true" />
                <div>
                  <b>{a.title}</b>
                  <small>Approval request · {a.kind.replace("_", " ")}</small>
                </div>
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            ))
          )
        }
      </QueryView>
    </article>
  );
}

function RecentActivity() {
  const navigate = useNavigate();
  const activity = useActivity({ limit: 6 });
  return (
    <article className="panel">
      <div className="panel-title">
        <h2>Recent Activity</h2>
        <button type="button" onClick={() => navigate(paths.activity)}>See all <ArrowUpRight size={14} aria-hidden="true" /></button>
      </div>
      <QueryView query={activity} label="activity">
        {() => <ActivityList events={activity.items.slice(0, 6)} emptyText="Activity appears here as your team works." />}
      </QueryView>
    </article>
  );
}

function CommandCentre({ preview }: { preview: CommandCentrePreview }) {
  const navigate = useNavigate();
  const { name } = useWorkspace();
  const { projects, currentProject, error, refetch } = useProjects();
  const departments = useDepartments();

  return (
    <>
      <div className="command-centre-heading">
        <div>
          <span className="eyebrow">BOOSKI STUDIOS / {name.toUpperCase()} / COMMAND CENTRE</span>
          <h1>Studio Command Centre</h1>
          <p>Your studio at a glance. Coordinate projects, tasks, decisions and approvals from one place.</p>
        </div>
        <SourceChip source="live" />
      </div>

      <Metrics />

      <section className="command-overview-grid">
        <article className="panel command-workforce">
          <div className="panel-title">
            <div>
              <h2>AI Workforce</h2>
              <small>Specialist agents arrive with AI orchestration in Phase 3</small>
            </div>
            <button type="button" onClick={() => navigate(paths.agents)}>Preview agents <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          <PreviewLabel />
          <div className="workforce-strip">
            {preview.workforce.map((w) => (
              <div className="workforce-person" key={w.name}>
                <span><Icon name={w.icon} size={17} /></span>
                <b>{w.name}</b>
                <small>{w.status}</small>
              </div>
            ))}
          </div>
        </article>
        <NeedsAttention />
      </section>

      {departments.isPending ? (
        <LoadingState label="departments" />
      ) : departments.isError ? (
        <ErrorState error={departments.error} label="departments" onRetry={departments.refetch} />
      ) : (
        <DepartmentCards departments={departments.data} />
      )}

      <section className="dashboard-grid top-grid">
        {error ? (
          <article className="panel project-overview"><ErrorState error={error} label="projects" onRetry={refetch} /></article>
        ) : !projects ? (
          <article className="panel project-overview"><LoadingState label="projects" /></article>
        ) : currentProject ? (
          <ProjectOverview project={currentProject} projects={projects} />
        ) : (
          <article className="panel project-overview">
            <div className="panel-title"><h2>Project Overview</h2></div>
            <EmptyState icon={Gamepad2} title="No projects yet">Owners and admins can create a project from the sidebar.</EmptyState>
          </article>
        )}
        <CurrentFocus />
        <StudioInsights data={preview} />
      </section>

      <section className="dashboard-grid bottom-grid">
        <RecentActivity />
        <article className="panel">
          <div className="panel-title">
            <h2>Post-Launch Feedback</h2>
            <button type="button" onClick={() => navigate(paths.department("post-launch-intelligence"))}>View Details <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          <PreviewLabel />
          <div className="feedback-stats">
            {preview.feedbackStats.map((s) => (
              <div key={s.label}>
                <b className={`${s.tone}-text`}>{s.value}</b>
                <small>{s.label}</small>
              </div>
            ))}
          </div>
          {preview.feedbackIssues.map((f) => (
            <div className="feedback-row" key={f.id}>
              <b>{f.title}</b>
              <span className={`severity ${f.severity.toLowerCase()}`}>{f.severity}</span>
              <small>{f.reports} reports</small>
            </div>
          ))}
        </article>
        <article className="panel">
          <div className="panel-title">
            <h2>Latest Assets</h2>
            <button type="button" onClick={() => navigate(paths.department("asset-production"))}>View All <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          <PreviewLabel />
          <div className="asset-grid">
            {preview.latestAssets.map((a) => (
              <div className="asset-card" key={a.id}>
                <img src={a.image} alt="" />
                <b>{a.name}</b>
              </div>
            ))}
          </div>
        </article>
      </section>
    </>
  );
}

/** `/` — Studio Command Centre: live studio data, plus clearly marked previews of later phases. */
export function HomePage() {
  const preview = useResource(() => studioApi.getCommandCentrePreview(), []);
  return (
    <ResourceView resource={preview} label="the Command Centre">
      {(data) => <CommandCentre preview={data} />}
    </ResourceView>
  );
}
