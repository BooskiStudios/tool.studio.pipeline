import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowUpRight, Bot, ChevronRight, Layers, ListTodo, Plus, SearchX, Settings } from "lucide-react";
import { useDepartments, useTaskList } from "../api/hooks";
import type { Department } from "../api/types";
import { ApprovalList } from "../components/approvals/ApprovalList";
import { ApprovalDetailModal } from "../components/approvals/ApprovalModals";
import { EmptyState, matchesQuery, SearchField } from "../components/common";
import { DecisionLogList } from "../components/DecisionLogList";
import { Icon } from "../components/Icon";
import { DocumentEditorModal, type DocumentDefaults } from "../components/knowledge/DocumentEditorModal";
import { DocumentList } from "../components/knowledge/DocumentList";
import { DocumentViewerModal } from "../components/knowledge/DocumentViewerModal";
import { TaskDetailModal } from "../components/tasks/TaskDetailModal";
import { TaskRecord } from "../components/tasks/TaskRecord";
import { useTaskLabels, useToggleTask } from "../components/tasks/useTaskHelpers";
import { ErrorState, LoadingState, LoadMore, QueryView, SourceChip } from "../components/ui";
import { departmentPresentation, type ActionSpec, type TabSpec } from "../config/departments";
import { useProjects } from "../context/ProjectContext";
import { useTasks } from "../context/TasksContext";
import { useToast } from "../context/ToastContext";
import { PROJECT_STATUS, projectImage } from "../lib/format";
import { paths } from "../routes";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { NotFoundPage } from "./NotFoundPage";
import { useDocumentParam } from "./StudioKnowledgePage";

const OPEN = ["backlog", "todo", "in_progress", "in_review", "blocked"];

function DepartmentWorkspaceView({ department }: { department: Department }) {
  const presentation = departmentPresentation(department.slug);
  const { tabs, actions, sampleItems } = presentation;
  const navigate = useNavigate();
  const notify = useToast();
  const { can } = useWorkspace();
  const { openTaskForm } = useTasks();
  const { projects, currentProject } = useProjects();
  const [tab, setTab] = useState<TabSpec>(tabs[0]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [openTask, setOpenTask] = useState<string | null>(null);
  const [openApproval, setOpenApproval] = useState<string | null>(null);
  const [openDocument, setOpenDocument] = useDocumentParam();
  const [newDocument, setNewDocument] = useState<DocumentDefaults | null>(null);
  const tasks = useTaskList({ department: department.slug, status: OPEN, parent: "none", sort: "priority" });
  const labels = useTaskLabels();
  const { toggle, pendingId } = useToggleTask();
  const name = department.name;
  const live = tab.kind !== "sample" && tab.kind !== "planned";

  const runAction = (action: ActionSpec) => {
    if (action.kind === "task") {
      if (can("tasks.create")) openTaskForm({ department_id: department.id });
      else notify("Your role can't create tasks in this workspace.");
    } else if (action.kind === "document") {
      if (can("documents.write")) setNewDocument({ kind: action.documentKind, department_id: department.id });
      else notify("Your role can't create documents in this workspace.");
    } else {
      notify(action.notice);
    }
  };

  const renderTab = () => {
    switch (tab.kind) {
      case "tasks":
        return (
          <QueryView query={tasks} label="tasks">
            {() =>
              tasks.items.length === 0 ? (
                <EmptyState icon={ListTodo} title="No open work">Open tasks for {name} will appear here.</EmptyState>
              ) : (
                <>
                  {tasks.items.map((t) => (
                    <TaskRecord key={t.id} task={t} context={labels(t)} onToggle={toggle} onOpen={(x) => setOpenTask(x.id)} busy={pendingId === t.id} />
                  ))}
                  <LoadMore {...tasks} />
                </>
              )
            }
          </QueryView>
        );
      case "documents":
        return (
          <DocumentList
            filters={{ department: department.slug, kind: tab.documentKind ? [tab.documentKind] : undefined, sort: "updated_at" }}
            onOpen={(d) => setOpenDocument(d.id)}
            emptyText={`${tab.label} for ${name} will appear here.`}
          />
        );
      case "decisions":
        return <DecisionLogList department={department.slug} embedded />;
      case "approvals":
        return (
          <ApprovalList
            filters={{ kind: tab.approvalKind ? [tab.approvalKind] : undefined }}
            onOpen={(a) => setOpenApproval(a.id)}
            emptyTitle="No requests"
            emptyText={`${tab.label} will appear here when someone requests a review.`}
          />
        );
      case "projects":
        return !projects ? (
          <LoadingState label="projects" />
        ) : projects.length === 0 ? (
          <EmptyState icon={Layers} title="No projects yet">Projects created in this workspace appear here.</EmptyState>
        ) : (
          projects.map((p) => (
            <button type="button" className="work-item" key={p.id} onClick={() => navigate(paths.project(p.slug))}>
              <span className="work-icon"><img src={projectImage(p)} alt="" className="work-thumb" /></span>
              <span className="work-copy">
                <b>{p.name}</b>
                <small>{[p.project_type, p.engine].filter(Boolean).join(" · ") || "Project"} · {p.progress.percent}% complete</small>
              </span>
              <span className="work-status">{PROJECT_STATUS[p.status]}</span>
              <ChevronRight size={17} aria-hidden="true" />
            </button>
          ))
        );
      case "sample": {
        const filtered = sampleItems.filter((x) => matchesQuery(query, x.title));
        return (
          <>
            <p className="small-note sample-note">Illustrative examples of what this area will hold. They are not stored records.</p>
            <SearchField value={query} onChange={setQuery} placeholder={`Search ${tab.label.toLowerCase()}...`} />
            {filtered.length === 0 && <EmptyState icon={SearchX} title="No matching examples">Nothing matches “{query}”.</EmptyState>}
            {filtered.map((w) => (
              <button
                type="button"
                className={`work-item ${selected === w.title ? "selected-work" : ""}`}
                key={w.id}
                onClick={() => setSelected(selected === w.title ? "" : w.title)}
                aria-pressed={selected === w.title}
              >
                <span className="work-icon"><Icon name={w.icon} size={19} /></span>
                <span className="work-copy">
                  <b>{w.title}</b>
                  <small>{w.detail}</small>
                </span>
                <span className="work-status">{w.status}</span>
                <ChevronRight size={17} aria-hidden="true" />
              </button>
            ))}
            {selected && (
              <div className="selected-detail">
                <b>{selected}</b>
                <p>Example item. Real {tab.label.toLowerCase()} with briefs, files, history and AI recommendations arrive in a later phase.</p>
              </div>
            )}
          </>
        );
      }
      default:
        return (
          <EmptyState icon={Layers} title={`${tab.label}: planned`}>
            {tab.description}
          </EmptyState>
        );
    }
  };

  return (
    <div className="workspace-page">
      <div
        className={`workspace-hero ${department.accent_color}`}
        style={{ backgroundImage: `linear-gradient(90deg,rgba(4,12,22,.96),rgba(4,12,22,.72),rgba(4,12,22,.28)),url(${presentation.image})` }}
      >
        <div className="workspace-hero-top">
          <span className="eyebrow">BOOSKI STUDIOS / DEPARTMENTS</span>
          <SourceChip source="live" />
        </div>
        <div className="workspace-heading">
          <div className="workspace-icon"><Icon name={department.icon_key} size={30} /></div>
          <div>
            <h1>{name}</h1>
            <p>{department.description}</p>
          </div>
        </div>
        <div className="workspace-actions">
          {actions.map((a, i) => (
            <button type="button" key={a.label} className={i === 0 ? "primary-btn" : "secondary-btn"} onClick={() => runAction(a)}>
              {i === 0 ? <Plus size={15} aria-hidden="true" /> : <ArrowUpRight size={15} aria-hidden="true" />} {a.label}
              {a.kind === "planned" ? " · planned" : ""}
            </button>
          ))}
        </div>
      </div>

      <div className="workspace-tabs" role="group" aria-label={`${name} sections`}>
        {tabs.map((t) => (
          <button
            type="button"
            aria-pressed={tab.label === t.label}
            className={tab.label === t.label ? "active-tab" : ""}
            key={t.label}
            onClick={() => {
              setTab(t);
              setSelected("");
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="workspace-stats">
        <div><small>Department</small><b>{name}</b></div>
        <div><small>Current project context</small><b>{currentProject?.name ?? "—"}</b></div>
        <div><small>Open tasks</small><b>{tasks.isPending ? "…" : `${tasks.items.length}${tasks.hasNextPage ? "+" : ""}`}</b></div>
        <div><small>Data source</small><b className="green-text">Booski Core</b></div>
      </div>

      <div className="workspace-content-grid">
        <section className="panel workspace-main" aria-label={tab.label}>
          <div className="panel-title">
            <h2>{tab.label}</h2>
            <span className="demo-label">{live ? "LIVE" : tab.kind === "sample" ? "SAMPLE CONTENT" : "PLANNED"}</span>
          </div>
          {renderTab()}
        </section>
        <aside className="panel workspace-side">
          <div className="panel-title"><h2>Department controls</h2></div>
          {can("tasks.create") && (
            <button type="button" className="quick-action" onClick={() => openTaskForm({ department_id: department.id })}>
              <Plus size={15} aria-hidden="true" /> Create new work
            </button>
          )}
          <button type="button" className="quick-action" onClick={() => notify("Assigning work to AI agents arrives with AI orchestration in Phase 3.")}>
            <Bot size={15} aria-hidden="true" /> Assign AI agent · planned
          </button>
          <div className="side-divider" />
          <div className="panel-title"><h2>Department status</h2></div>
          <div className="status-line"><span>Tasks, documents, decisions</span><b className="green-text">Live</b></div>
          <div className="status-line"><span>AI integration</span><b className="muted-text">Not connected</b></div>
          <div className="status-line"><span>Files and assets</span><b className="muted-text">Planned</b></div>
          <button type="button" className="outline-wide" onClick={() => navigate(paths.settings)}>
            <Settings size={14} aria-hidden="true" /> Settings
          </button>
        </aside>
      </div>
      {openTask && <TaskDetailModal taskId={openTask} onClose={() => setOpenTask(null)} />}
      {openApproval && <ApprovalDetailModal approvalId={openApproval} onClose={() => setOpenApproval(null)} />}
      {openDocument && <DocumentViewerModal documentId={openDocument} onClose={() => setOpenDocument(null)} />}
      {newDocument && <DocumentEditorModal defaults={newDocument} onClose={() => setNewDocument(null)} onSaved={(d) => setOpenDocument(d.id)} />}
    </div>
  );
}

/** `/departments/:departmentSlug` — a department workspace. */
export function DepartmentPage() {
  const { departmentSlug = "" } = useParams();
  const departments = useDepartments();
  if (departments.isPending) return <LoadingState label="this department" />;
  if (departments.isError) return <ErrorState error={departments.error} label="this department" onRetry={departments.refetch} />;
  const department = departments.data.find((d) => d.slug === departmentSlug && !d.archived_at);
  if (!department) return <NotFoundPage />;
  return <DepartmentWorkspaceView key={department.slug} department={department} />;
}
