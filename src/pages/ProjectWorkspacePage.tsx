import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";
import {
  Archive, ArrowLeft, BookOpen, Database, Flag, GitBranch, Lock, Monitor, Pencil, Play, Plus, RotateCcw, Search, Users,
} from "lucide-react";
import { isApiError } from "../api/client";
import * as core from "../api/core";
import {
  useActivity, useDepartments, useMilestones, useProject, useTaskList, useWorkspaceMutation, useWorkstreams,
} from "../api/hooks";
import type { Capability, Milestone, MilestoneStatus, Project } from "../api/types";
import { ActivityList } from "../components/ActivityList";
import { ApprovalList } from "../components/approvals/ApprovalList";
import { ApprovalDetailModal, ApprovalRequestModal } from "../components/approvals/ApprovalModals";
import { EmptyState } from "../components/common";
import { DecisionLogList } from "../components/DecisionLogList";
import { DocumentEditorModal } from "../components/knowledge/DocumentEditorModal";
import { DocumentList } from "../components/knowledge/DocumentList";
import { DocumentViewerModal } from "../components/knowledge/DocumentViewerModal";
import { Modal } from "../components/Modal";
import { ProjectAccessModal } from "../components/projects/ProjectAccessModal";
import { ProjectFormModal } from "../components/projects/ProjectFormModal";
import { ReferenceVault } from "../components/ReferenceVault";
import { TaskDetailModal } from "../components/tasks/TaskDetailModal";
import { TaskRecord } from "../components/tasks/TaskRecord";
import { useTaskLabels, useToggleTask } from "../components/tasks/useTaskHelpers";
import { ErrorState, Field, FormError, LoadingState, LoadMore, ProgressBar, QueryView, SourceChip } from "../components/ui";
import { useProjects } from "../context/ProjectContext";
import { useTasks } from "../context/TasksContext";
import { useToast } from "../context/ToastContext";
import { formatDate, MILESTONE_STATUS, PROJECT_STATUS, projectImage } from "../lib/format";
import { paths } from "../routes";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { NotFoundPage } from "./NotFoundPage";
import { useDocumentParam } from "./StudioKnowledgePage";

const TABS = [
  "Overview", "Tasks", "Milestones", "Documents", "Decisions", "Approvals", "Activity", "Assets", "Reference Vault", "Builds & Tests",
] as const;
type ProjectTab = (typeof TABS)[number];
const PLANNED: Partial<Record<ProjectTab, string>> = {
  Assets: "Project asset storage (images, audio, models) arrives with file storage in a later phase.",
  "Builds & Tests": "Build and test history arrives with the engine bridge in a later phase.",
};

function MilestoneForm({ project, milestone, onClose }: { project: Project; milestone?: Milestone; onClose: () => void }) {
  const [name, setName] = useState(milestone?.name ?? "");
  const [description, setDescription] = useState(milestone?.description ?? "");
  const [target, setTarget] = useState(milestone?.target_date ?? "");
  const [status, setStatus] = useState<MilestoneStatus>(milestone?.status ?? "planned");
  const save = useWorkspaceMutation((ws, _: void) => {
    const body = { name: name.trim(), description, target_date: target || null, status };
    return milestone
      ? core.milestones.update(ws, milestone.id, { ...body, version: milestone.version })
      : core.projects.createMilestone(ws, project.slug, body);
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim()) save.mutate(undefined, { onSuccess: onClose });
  };
  return (
    <Modal eyebrow={project.name.toUpperCase()} title={milestone ? "Edit milestone" : "New milestone"} onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <Field label="Name">{(props) => <input {...props} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} data-autofocus />}</Field>
        <Field label="Description">{(props) => <textarea {...props} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
        <Field label="Target date">{(props) => <input {...props} type="date" value={target} onChange={(e) => setTarget(e.target.value)} />}</Field>
        <Field label="Status">
          {(props) => (
            <select {...props} value={status} onChange={(e) => setStatus(e.target.value as MilestoneStatus)}>
              {(Object.keys(MILESTONE_STATUS) as MilestoneStatus[]).map((s) => <option key={s} value={s}>{MILESTONE_STATUS[s]}</option>)}
            </select>
          )}
        </Field>
        <FormError error={isApiError(save.error, "conflict") ? "Someone else changed this milestone. Close and reopen it to see the latest version." : save.error} />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={save.isPending || !name.trim()}>{save.isPending ? "Saving…" : "Save milestone"}</button>
        </div>
      </form>
    </Modal>
  );
}

function Milestones({ project, can }: { project: Project; can: (c: Capability) => boolean }) {
  const milestones = useMilestones(project.slug);
  const [editing, setEditing] = useState<Milestone | "new" | null>(null);
  return (
    <>
      <QueryView query={milestones} label="milestones">
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState icon={Flag} title="No milestones yet">Milestones track progress from the tasks linked to them.</EmptyState>
          ) : (
            rows.map((m) => (
              <div className="milestone-row" key={m.id} data-testid="milestone-row">
                <span>
                  <b>{m.name}</b>
                  <small>{MILESTONE_STATUS[m.status]} · target {formatDate(m.target_date)} · {m.progress.done}/{m.progress.total} tasks done</small>
                </span>
                <span className="milestone-progress">
                  <ProgressBar percent={m.progress.percent} label={`${m.name} progress`} />
                  <b>{m.progress.percent}%</b>
                </span>
                {can("milestones.write") && (
                  <button type="button" className="icon-only" onClick={() => setEditing(m)} aria-label={`Edit ${m.name}`}>
                    <Pencil size={13} aria-hidden="true" />
                  </button>
                )}
              </div>
            ))
          )
        }
      </QueryView>
      {can("milestones.write") && (
        <button type="button" className="inline-add" onClick={() => setEditing("new")}><Plus size={14} aria-hidden="true" /> Add milestone</button>
      )}
      {editing && <MilestoneForm project={project} milestone={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function Workstreams({ project, canManage }: { project: Project; canManage: boolean }) {
  const workstreams = useWorkstreams(project.slug);
  const departments = useDepartments();
  const [name, setName] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const create = useWorkspaceMutation((ws, _: void) =>
    core.projects.createWorkstream(ws, project.slug, { department_id: departmentId, name: name.trim() }),
  );
  return (
    <div className="workstreams">
      <h3 className="section-title">Departments & workstreams</h3>
      <QueryView query={workstreams} label="workstreams">
        {(rows) =>
          rows.length === 0 ? (
            <p className="muted-text">No workstreams yet. Workstreams split a project's work by department.</p>
          ) : (
            <div className="tags">
              {rows.map((w) => (
                <span key={w.id}>{departments.data?.find((d) => d.id === w.department_id)?.name ?? "Department"} · {w.name}</span>
              ))}
            </div>
          )
        }
      </QueryView>
      {canManage && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim() && departmentId) create.mutate(undefined, { onSuccess: () => setName("") });
          }}
        >
          <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} aria-label="Workstream department">
            <option value="">Department…</option>
            {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Workstream name" aria-label="Workstream name" maxLength={80} />
          <button type="submit" className="secondary-btn" disabled={!name.trim() || !departmentId || create.isPending}>
            <Plus size={13} aria-hidden="true" /> Add
          </button>
        </form>
      )}
      <FormError error={create.error} />
    </div>
  );
}

function ProjectWorkspace({ project }: { project: Project }) {
  const navigate = useNavigate();
  const notify = useToast();
  const { openTaskForm } = useTasks();
  const { can: canInWorkspace } = useWorkspace();
  const [tab, setTab] = useState<ProjectTab>("Overview");
  const [editing, setEditing] = useState(false);
  const [managingAccess, setManagingAccess] = useState(false);
  const [newDocument, setNewDocument] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [openTask, setOpenTask] = useState<string | null>(null);
  const [openApproval, setOpenApproval] = useState<string | null>(null);
  const [openDocument, setOpenDocument] = useDocumentParam();
  const can = (capability: Capability) => project.capabilities.includes(capability);
  const manage = canInWorkspace("projects.manage");
  const readOnly = !can("tasks.create") && !can("documents.write");
  const tasks = useTaskList({ project: project.slug, parent: "none", status: tab === "Tasks" ? undefined : ["backlog", "todo", "in_progress", "in_review", "blocked"] }, tab === "Tasks");
  const activity = useActivity({ project: project.slug }, tab === "Activity");
  const labels = useTaskLabels();
  const { toggle, pendingId } = useToggleTask();
  const archive = useWorkspaceMutation((ws, archived: boolean) => core.projects.update(ws, project.slug, { archived, version: project.version }));
  const openCount = project.progress.total - project.progress.done;

  const features: { title: string; detail: string; tab: ProjectTab }[] = [
    { title: "Tasks", detail: `${openCount} open of ${project.progress.total}`, tab: "Tasks" },
    { title: "Milestones", detail: "Progress computed from linked tasks", tab: "Milestones" },
    { title: "Documents", detail: "Design docs, notes and references", tab: "Documents" },
    { title: "Decisions", detail: "What was decided and why", tab: "Decisions" },
    { title: "Approvals", detail: "Requests waiting for review", tab: "Approvals" },
    { title: "Activity", detail: "Everything that changed in this project", tab: "Activity" },
  ];

  const renderTab = () => {
    if (PLANNED[tab]) {
      return <EmptyState icon={Database} title={`${tab}: planned`}>{PLANNED[tab]}</EmptyState>;
    }
    switch (tab) {
      case "Overview":
        return (
          <>
            <p className="project-description">{project.description || "No description yet."}</p>
            <div className="project-feature-grid">
              {features.map((f) => (
                <button type="button" key={f.title} onClick={() => setTab(f.tab)}>
                  <BookOpen size={20} aria-hidden="true" />
                  <b>{f.title}</b>
                  <small>{f.detail}</small>
                </button>
              ))}
            </div>
            <Workstreams project={project} canManage={manage} />
          </>
        );
      case "Tasks":
        return (
          <QueryView query={tasks} label="tasks">
            {() =>
              tasks.items.length === 0 ? (
                <EmptyState icon={Database} title="No tasks yet">Tasks you add to this project will appear here.</EmptyState>
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
      case "Milestones":
        return <Milestones project={project} can={can} />;
      case "Documents":
        return <DocumentList filters={{ project: project.slug, sort: "updated_at" }} onOpen={(d) => setOpenDocument(d.id)} emptyText="Design documents and notes for this project will appear here." />;
      case "Decisions":
        return <DecisionLogList project={project.slug} embedded defaults={{ project_id: project.id }} />;
      case "Approvals":
        return (
          <ApprovalList
            filters={{ project: project.slug }}
            onOpen={(a) => setOpenApproval(a.id)}
            emptyTitle="No approval requests"
            emptyText="Requests linked to this project will appear here."
          />
        );
      case "Activity":
        return (
          <QueryView query={activity} label="project activity">
            {() => (
              <>
                <ActivityList events={activity.items} />
                <LoadMore {...activity} />
              </>
            )}
          </QueryView>
        );
      case "Reference Vault":
        return <ReferenceVault projectSlug={project.slug} />;
      default:
        return null;
    }
  };

  const addButton =
    tab === "Tasks" && can("tasks.create") ? (
      <button type="button" onClick={() => openTaskForm({ project_id: project.id })}><Plus size={14} aria-hidden="true" /> Add task</button>
    ) : tab === "Documents" && can("documents.write") ? (
      <button type="button" onClick={() => setNewDocument(true)}><Plus size={14} aria-hidden="true" /> New document</button>
    ) : tab === "Approvals" && can("approvals.request") ? (
      <button type="button" onClick={() => setRequesting(true)}><Plus size={14} aria-hidden="true" /> Request approval</button>
    ) : null;

  return (
    <div className="workspace-page">
      <div
        className="project-hero"
        style={{ backgroundImage: `linear-gradient(90deg,rgba(4,12,22,.97),rgba(4,12,22,.72),rgba(4,12,22,.25)),url("${projectImage(project)}")` }}
      >
        <button type="button" className="back-link" onClick={() => navigate(paths.home)}><ArrowLeft size={14} aria-hidden="true" /> Dashboard</button>
        <SourceChip source="live" />
        {project.visibility === "restricted" && <span className="demo-chip restricted-chip"><Lock size={10} aria-hidden="true" /> RESTRICTED</span>}
        {project.archived_at && <span className="demo-chip">ARCHIVED</span>}
        <h1>{project.name}</h1>
        <p>{[project.project_type, project.engine && `${project.engine} project`].filter(Boolean).join(" · ") || "Project"}</p>
        <div className="project-hero-bottom">
          <div>
            <small>Development progress · {project.progress.done}/{project.progress.total} tasks done</small>
            <b>{project.progress.percent}%</b>
            <ProgressBar percent={project.progress.percent} label="Project progress" />
          </div>
          <button type="button" className="primary-btn" onClick={() => notify("Engine connection arrives with the Unity bridge in a later phase.")}>
            <Monitor size={15} aria-hidden="true" /> Connect engine
          </button>
        </div>
      </div>

      <div className="workspace-tabs" role="group" aria-label={`${project.name} sections`}>
        {TABS.map((t) => (
          <button type="button" aria-pressed={tab === t} className={tab === t ? "active-tab" : ""} key={t} onClick={() => setTab(t)}>
            {t}{PLANNED[t] || t === "Reference Vault" ? " ·" : ""}
          </button>
        ))}
      </div>

      <div className="workspace-stats">
        <div><small>Project status</small><b>{PROJECT_STATUS[project.status]}</b></div>
        <div><small>Engine</small><b>{project.engine || "—"}</b></div>
        <div><small>Open tasks</small><b>{openCount}</b></div>
        <div><small>Your access</small><b className={readOnly ? "muted-text" : "green-text"}>{readOnly ? "Read-only" : "Can contribute"}</b></div>
      </div>

      <div className="workspace-content-grid">
        <section className="panel workspace-main" aria-label={tab}>
          <div className="panel-title">
            <h2>{tab}</h2>
            {addButton}
          </div>
          {renderTab()}
        </section>
        <aside className="panel workspace-side">
          <div className="panel-title"><h2>Project controls</h2></div>
          {manage && (
            <>
              <button type="button" className="quick-action" onClick={() => setEditing(true)}><Pencil size={15} aria-hidden="true" /> Edit project</button>
              <button type="button" className="quick-action" onClick={() => setManagingAccess(true)}><Users size={15} aria-hidden="true" /> Project access</button>
              <button
                type="button"
                className="quick-action"
                disabled={archive.isPending}
                onClick={() => archive.mutate(!project.archived_at, { onSuccess: () => notify(project.archived_at ? "Project restored." : "Project archived.") })}
              >
                {project.archived_at ? <RotateCcw size={15} aria-hidden="true" /> : <Archive size={15} aria-hidden="true" />}
                {project.archived_at ? "Restore project" : "Archive project"}
              </button>
              <FormError error={archive.error} />
            </>
          )}
          <button type="button" className="quick-action" onClick={() => notify("Project scans need the Unity bridge (later phase).")}><Search size={15} aria-hidden="true" /> Inspect project · planned</button>
          <button type="button" className="quick-action" onClick={() => notify("Build and test runs need the Unity bridge (later phase).")}><Play size={15} aria-hidden="true" /> Run tests · planned</button>
          <button type="button" className="quick-action" onClick={() => notify("Version control integration is planned for a later phase.")}><GitBranch size={15} aria-hidden="true" /> Version control · planned</button>
          <div className="side-divider" />
          <div className="panel-title"><h2>Connection</h2></div>
          <div className="status-line"><span>Project records</span><b className="green-text">Booski Core</b></div>
          <div className="status-line"><span>Visibility</span><b>{project.visibility === "restricted" ? "Restricted" : "Whole workspace"}</b></div>
          <div className="status-line"><span>Unity editor</span><b className="muted-text">Not connected</b></div>
          <div className="status-line"><span>AI project memory</span><b className="muted-text">Planned</b></div>
        </aside>
      </div>
      {editing && <ProjectFormModal project={project} onClose={() => setEditing(false)} />}
      {managingAccess && <ProjectAccessModal project={project} onClose={() => setManagingAccess(false)} />}
      {newDocument && <DocumentEditorModal defaults={{ project_id: project.id, kind: "design_doc" }} onClose={() => setNewDocument(false)} />}
      {requesting && <ApprovalRequestModal defaults={{ project_id: project.id }} onClose={() => setRequesting(false)} />}
      {openTask && <TaskDetailModal taskId={openTask} onClose={() => setOpenTask(null)} />}
      {openApproval && <ApprovalDetailModal approvalId={openApproval} onClose={() => setOpenApproval(null)} />}
      {openDocument && <DocumentViewerModal documentId={openDocument} onClose={() => setOpenDocument(null)} />}
    </div>
  );
}

/** `/projects/:projectSlug` — a project's workspace. Opening it also makes it the current project. */
export function ProjectWorkspacePage() {
  const { projectSlug = "" } = useParams();
  const project = useProject(projectSlug);
  const { selectProject } = useProjects();

  useEffect(() => {
    if (project.data) selectProject(project.data.slug);
  }, [project.data, selectProject]);

  if (project.isPending) return <LoadingState label="project" />;
  // A restricted project you aren't on answers 404, exactly like one that doesn't exist.
  if (isApiError(project.error, "not_found")) return <NotFoundPage />;
  if (project.isError) return <ErrorState error={project.error} label="this project" onRetry={project.refetch} />;
  return <ProjectWorkspace key={project.data.slug} project={project.data} />;
}
