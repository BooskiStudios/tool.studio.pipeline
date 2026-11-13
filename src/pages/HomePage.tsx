import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronDown, ChevronRight, Circle, Gamepad2, Plus } from "lucide-react";
import { ResourceView } from "../components/common";
import { Icon } from "../components/Icon";
import { useProjects } from "../context/ProjectContext";
import { useTasks } from "../context/TasksContext";
import { useResource } from "../hooks/useResource";
import { paths } from "../routes";
import { studioApi } from "../services";
import type { CommandCentreData, Department, Project } from "../types";

const PERIODS = ["This Month", "This Week", "This Year"];

function DepartmentCards({ departments }: { departments: Department[] }) {
  const navigate = useNavigate();
  return (
    <section className="department-grid" aria-label="Departments">
      {departments.map((d) => (
        <button
          type="button"
          key={d.slug}
          className={`department-card ${d.color}`}
          style={{ backgroundImage: `linear-gradient(90deg,rgba(3,10,20,.94),rgba(3,10,20,.55) 60%,rgba(3,10,20,.1)),url(${d.image})` }}
          onClick={() => navigate(paths.department(d.slug))}
        >
          <div className="department-icon"><Icon name={d.icon} size={27} /></div>
          <div className="department-copy">
            <b>{d.name}</b>
            <p>{d.desc}</p>
          </div>
          <span className="department-arrow"><ArrowRight size={22} aria-hidden="true" /></span>
        </button>
      ))}
    </section>
  );
}

function ProjectOverview({ project, projects, milestones }: { project: Project; projects: Project[]; milestones: CommandCentreData["milestones"] }) {
  const navigate = useNavigate();
  const { selectProject } = useProjects();
  const [menuOpen, setMenuOpen] = useState(false);

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
                  key={p.slug}
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
        <img src={project.image} alt="" />
        <div className="summary-copy">
          <b>{project.name}</b>
          <div className="tags">
            <span>{project.status}</span>
            <span>{project.type}</span>
            <span>{project.engine}</span>
          </div>
          <p>{project.description}</p>
          <div className="progress-line"><span style={{ width: `${project.progress}%` }} /></div>
        </div>
        <strong>{project.progress}%</strong>
      </div>
      <div className="milestones">
        {milestones.map((m, i) => (
          <div key={m.id}>
            <span className={`milestone-dot m${i}`}><Check size={13} aria-hidden="true" /></span>
            <span>{m.label}</span>
            <small>{m.progress}</small>
          </div>
        ))}
      </div>
      <button type="button" className="inline-link" onClick={() => navigate(paths.project(project.slug))}>
        Open full project workspace <ArrowUpRight size={14} aria-hidden="true" />
      </button>
    </article>
  );
}

function CurrentFocus({ focus }: { focus: CommandCentreData["focus"] }) {
  const navigate = useNavigate();
  const { tasks = [], toggleTask, openTaskForm } = useTasks();
  const done = tasks.filter((t) => t.done).length;
  const pct = Math.round((done / Math.max(tasks.length, 1)) * 100);

  return (
    <article className="panel focus-panel">
      <div className="panel-title">
        <h2>Current Focus</h2>
        <button type="button" onClick={() => navigate(paths.tasks)}>View Tasks <ArrowUpRight size={14} aria-hidden="true" /></button>
      </div>
      <div className="focus-card">
        <div className="focus-icon"><Gamepad2 size={22} aria-hidden="true" /></div>
        <div className="focus-content">
          <b>{focus.title}</b>
          <div>
            <span>{focus.department}</span>
            <span className="priority">{focus.label}</span>
          </div>
          <small>{done}/{tasks.length} demo tasks completed</small>
        </div>
        <div className="progress-ring" style={{ background: `conic-gradient(#4bc8ec ${pct}%,#243447 0)` }} role="img" aria-label={`${pct}% of demo tasks completed`}>
          <span>{pct}%</span>
        </div>
      </div>
      <div className="task-list">
        {tasks.slice(0, 5).map((t) => (
          <button type="button" key={t.id} onClick={() => toggleTask(t.id)} aria-pressed={t.done}>
            {t.done ? <CheckCircle2 className="task-done" size={18} aria-hidden="true" /> : <Circle className="task-open" size={18} aria-hidden="true" />}
            <span className={t.done ? "done" : ""}>{t.title}</span>
          </button>
        ))}
      </div>
      <button type="button" className="inline-add" onClick={openTaskForm}><Plus size={14} aria-hidden="true" /> Add task</button>
    </article>
  );
}

function StudioInsights({ data }: { data: CommandCentreData }) {
  const [period, setPeriod] = useState(PERIODS[0]);
  return (
    <article className="panel insights-panel">
      <div className="panel-title">
        <h2>Studio Insights</h2>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} aria-label="Insights period">
          {PERIODS.map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>
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

function CommandCentre({ data, departments }: { data: CommandCentreData; departments: Department[] }) {
  const navigate = useNavigate();
  const { projects, currentProject } = useProjects();

  return (
    <>
      <div className="command-centre-heading">
        <div>
          <span className="eyebrow">BOOSKI STUDIOS / COMMAND CENTRE</span>
          <h1>Studio Command Centre</h1>
          <p>Your studio at a glance. Coordinate projects, AI workers, decisions and approvals from one place.</p>
        </div>
        <span className="demo-chip">FRONTEND PREVIEW · DEMO DATA</span>
      </div>

      <section className="command-metrics" aria-label="Studio metrics">
        {data.metrics.map((m) => (
          <div className="panel command-metric" key={m.id}>
            <span className={`metric-icon ${m.tone}`}><Icon name={m.icon} size={18} /></span>
            <small>{m.label}</small>
            <b>{m.value}</b>
            <em>{m.note}</em>
          </div>
        ))}
      </section>

      <section className="command-overview-grid">
        <article className="panel command-workforce">
          <div className="panel-title">
            <div>
              <h2>AI Workforce</h2>
              <small>Specialist agents across the studio</small>
            </div>
            <button type="button" onClick={() => navigate(paths.agents)}>Manage agents <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          <div className="workforce-strip">
            {data.workforce.map((w) => (
              <div className="workforce-person" key={w.name}>
                <span><Icon name={w.icon} size={17} /></span>
                <b>{w.name}</b>
                <small>{w.status}</small>
              </div>
            ))}
          </div>
        </article>
        <article className="panel command-approvals">
          <div className="panel-title">
            <h2>Needs your attention</h2>
            <button type="button" onClick={() => navigate(paths.approvals)}>View all <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          {data.attention.map((a) => (
            <div className="attention-row" key={a.id}>
              <span className="attention-dot" aria-hidden="true" />
              <div>
                <b>{a.title}</b>
                <small>{a.agent} · {a.department}</small>
              </div>
              <ChevronRight size={15} aria-hidden="true" />
            </div>
          ))}
        </article>
      </section>

      <DepartmentCards departments={departments} />

      <section className="dashboard-grid top-grid">
        {currentProject && projects ? (
          <ProjectOverview project={currentProject} projects={projects} milestones={data.milestones} />
        ) : (
          <article className="panel project-overview"><div className="resource-state" role="status">Loading projects…</div></article>
        )}
        <CurrentFocus focus={data.focus} />
        <StudioInsights data={data} />
      </section>

      <section className="dashboard-grid bottom-grid">
        <article className="panel">
          <div className="panel-title">
            <h2>Recent Activity</h2>
            <button type="button" onClick={() => navigate(paths.tasks)}>See all <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          {data.activity.map((a) => (
            <div className="activity-row" key={a.id}>
              <span className="activity-icon blue"><Icon name={a.icon} size={16} /></span>
              <span>{a.title}</span>
              <small>{a.time}</small>
            </div>
          ))}
        </article>
        <article className="panel">
          <div className="panel-title">
            <h2>Post-Launch Feedback</h2>
            <button type="button" onClick={() => navigate(paths.department("post-launch-intelligence"))}>View Details <ArrowUpRight size={14} aria-hidden="true" /></button>
          </div>
          <div className="feedback-stats">
            {data.feedbackStats.map((s) => (
              <div key={s.label}>
                <b className={`${s.tone}-text`}>{s.value}</b>
                <small>{s.label}</small>
              </div>
            ))}
          </div>
          {data.feedbackIssues.map((f) => (
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
          <div className="asset-grid">
            {data.latestAssets.map((a) => (
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

/** `/` — Studio Command Centre. */
export function HomePage() {
  const page = useResource(
    () => Promise.all([studioApi.getCommandCentre(), studioApi.listDepartments()]),
    [],
  );
  return (
    <ResourceView resource={page} label="the Command Centre">
      {([data, departments]) => <CommandCentre data={data} departments={departments} />}
    </ResourceView>
  );
}
