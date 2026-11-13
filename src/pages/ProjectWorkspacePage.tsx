import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft, BookOpen, Database, GitBranch, Monitor, Play, Plus, Search } from "lucide-react";
import { EmptyState } from "../components/common";
import { ReferenceVault } from "../components/ReferenceVault";
import { TaskRecord } from "../components/TaskRecord";
import { useProjects } from "../context/ProjectContext";
import { useTasks } from "../context/TasksContext";
import { useToast } from "../context/ToastContext";
import { paths } from "../routes";
import type { Project } from "../types";
import { NotFoundPage } from "./NotFoundPage";

const TABS = ["Overview", "Tasks", "Design Documents", "Assets", "Reference Vault", "Builds & Tests", "Activity"] as const;
type ProjectTab = (typeof TABS)[number];

function ProjectWorkspace({ project }: { project: Project }) {
  const navigate = useNavigate();
  const notify = useToast();
  const { tasks = [], toggleTask, openTaskForm } = useTasks();
  const [tab, setTab] = useState<ProjectTab>("Overview");

  const features: { title: string; detail: string; tab: ProjectTab }[] = [
    { title: "Development tasks", detail: `${tasks.length} tracked demo tasks`, tab: "Tasks" },
    { title: "Design documents", detail: "Game design and technical docs", tab: "Design Documents" },
    { title: "Assets", detail: "Linked project resources", tab: "Assets" },
    { title: "Reference Vault", detail: "AI-discovered and user-saved references", tab: "Reference Vault" },
    { title: "Builds & tests", detail: "Engine verification history", tab: "Builds & Tests" },
  ];

  const renderTab = () => {
    switch (tab) {
      case "Overview":
        return (
          <>
            <p className="project-description">
              {project.description} This project has its own dedicated context, documents, assets, references and development history.
            </p>
            <div className="project-feature-grid">
              {features.map((f) => (
                <button type="button" key={f.title} onClick={() => setTab(f.tab)}>
                  <BookOpen size={20} aria-hidden="true" />
                  <b>{f.title}</b>
                  <small>{f.detail}</small>
                </button>
              ))}
            </div>
          </>
        );
      case "Tasks":
        return tasks.map((t) => <TaskRecord key={t.id} task={t} onToggle={toggleTask} />);
      case "Reference Vault":
        return <ReferenceVault projectSlug={project.slug} />;
      default:
        return (
          <EmptyState icon={Database} title={`${tab} workspace prepared`}>
            Project-specific {tab.toLowerCase()} and records will be connected to the backend.
          </EmptyState>
        );
    }
  };

  return (
    <div className="workspace-page">
      <div
        className="project-hero"
        style={{ backgroundImage: `linear-gradient(90deg,rgba(4,12,22,.97),rgba(4,12,22,.72),rgba(4,12,22,.25)),url(${project.image})` }}
      >
        <button type="button" className="back-link" onClick={() => navigate(paths.home)}><ArrowLeft size={14} aria-hidden="true" /> Dashboard</button>
        <span className="demo-chip">PROJECT WORKSPACE · DEMO</span>
        <h1>{project.name}</h1>
        <p>{project.type} · {project.engine} project</p>
        <div className="project-hero-bottom">
          <div>
            <small>Development progress</small>
            <b>{project.progress}%</b>
            <div className="progress-line"><span style={{ width: `${project.progress}%` }} /></div>
          </div>
          <button type="button" className="primary-btn" onClick={() => notify("Engine connection will be handled by the Unity bridge phase.")}>
            <Monitor size={15} aria-hidden="true" /> Connect engine
          </button>
        </div>
      </div>

      <div className="workspace-tabs" role="group" aria-label={`${project.name} sections`}>
        {TABS.map((t) => (
          <button type="button" aria-pressed={tab === t} className={tab === t ? "active-tab" : ""} key={t} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div className="workspace-stats">
        <div><small>Project status</small><b>{project.status}</b></div>
        <div><small>Engine</small><b>{project.engine}</b></div>
        <div><small>Open tasks</small><b>{tasks.filter((t) => !t.done).length}</b></div>
        <div><small>Project context</small><b className="green-text">Isolated demo context</b></div>
      </div>

      <div className="workspace-content-grid">
        <section className="panel workspace-main" aria-label={tab}>
          <div className="panel-title">
            <h2>{tab}</h2>
            {tab === "Tasks" && <button type="button" onClick={openTaskForm}><Plus size={14} aria-hidden="true" /> Add task</button>}
          </div>
          {renderTab()}
        </section>
        <aside className="panel workspace-side">
          <div className="panel-title"><h2>Project controls</h2></div>
          <button type="button" className="quick-action" onClick={() => notify("Project scan requires the Unity bridge.")}><Search size={15} aria-hidden="true" /> Inspect project</button>
          <button type="button" className="quick-action" onClick={() => notify("Build and test execution requires the Unity bridge.")}><Play size={15} aria-hidden="true" /> Run tests</button>
          <button type="button" className="quick-action" onClick={() => notify("Project backup will be connected to Git integration.")}><GitBranch size={15} aria-hidden="true" /> Version control</button>
          <div className="side-divider" />
          <div className="panel-title"><h2>Connection</h2></div>
          <div className="status-line"><span>Unity editor</span><b className="muted-text">Not connected</b></div>
          <div className="status-line"><span>Project memory</span><b className="green-text">Demo context</b></div>
        </aside>
      </div>
    </div>
  );
}

/** `/projects/:projectSlug` — a project's workspace. Opening it also makes it the current project. */
export function ProjectWorkspacePage() {
  const { projectSlug = "" } = useParams();
  const { projects, selectProject } = useProjects();
  const project = projects?.find((p) => p.slug === projectSlug);

  useEffect(() => {
    if (project) selectProject(project.slug);
  }, [project, selectProject]);

  if (!projects) return <div className="resource-state" role="status">Loading project…</div>;
  if (!project) return <NotFoundPage />;
  return <ProjectWorkspace key={project.slug} project={project} />;
}
