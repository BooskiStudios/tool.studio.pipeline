import { useState } from "react";
import { useSearchParams } from "react-router";
import { ListTodo, Plus } from "lucide-react";
import { useDepartments, useProjectList, useTaskList } from "../api/hooks";
import type { TaskStatus } from "../api/types";
import { EmptyState, PageHeading, SearchField } from "../components/common";
import { TaskDetailModal } from "../components/tasks/TaskDetailModal";
import { TaskRecord } from "../components/tasks/TaskRecord";
import { useTaskLabels, useToggleTask } from "../components/tasks/useTaskHelpers";
import { LoadMore, QueryView, RefreshingHint } from "../components/ui";
import { useTasks } from "../context/TasksContext";
import { TASK_STATUS } from "../lib/format";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const OPEN_STATUSES: TaskStatus[] = ["backlog", "todo", "in_progress", "in_review", "blocked"];
type StatusFilter = "open" | "all" | TaskStatus;

/** `/tasks` — every task you can see across the studio (`?task=<id>` opens one). */
export function TaskCentrePage() {
  const { can } = useWorkspace();
  const { openTaskForm } = useTasks();
  const [params, setParams] = useSearchParams();
  const projects = useProjectList();
  const departments = useDepartments();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<StatusFilter>("open");
  const [project, setProject] = useState("");
  const [department, setDepartment] = useState("");
  const [assignee, setAssignee] = useState("");
  const [sort, setSort] = useState("position");
  const [archived, setArchived] = useState(false);

  const tasks = useTaskList({
    q: q.trim() || undefined,
    status: status === "open" ? OPEN_STATUSES : status === "all" ? undefined : [status],
    project: project || undefined,
    department: department || undefined,
    assignee: assignee || undefined,
    sort,
    archived,
    parent: "none",
  });
  const labels = useTaskLabels();
  const { toggle, pendingId } = useToggleTask();
  const openId = params.get("task");
  const setOpen = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set("task", id);
    else next.delete("task");
    setParams(next, { replace: !id });
  };

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="STUDIO OPERATIONS"
        title="Task Centre"
        description="One place to review and manage work across the studio."
        source="live"
        actions={
          can("tasks.create") && (
            <button type="button" className="primary-btn" onClick={() => openTaskForm()}>
              <Plus size={14} aria-hidden="true" /> New task
            </button>
          )
        }
      />
      <section className="panel task-centre">
        <div className="filter-bar" role="search" aria-label="Filter tasks">
          <SearchField value={q} onChange={setQ} placeholder="Search task titles…" />
          <select value={status} onChange={(e) => setStatus(e.target.value as StatusFilter)} aria-label="Status">
            <option value="open">Open tasks</option>
            <option value="all">All statuses</option>
            {(Object.keys(TASK_STATUS) as TaskStatus[]).map((s) => <option key={s} value={s}>{TASK_STATUS[s]}</option>)}
          </select>
          <select value={project} onChange={(e) => setProject(e.target.value)} aria-label="Project">
            <option value="">All projects</option>
            {(projects.data ?? []).map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
          <select value={department} onChange={(e) => setDepartment(e.target.value)} aria-label="Department">
            <option value="">All departments</option>
            {(departments.data ?? []).map((d) => <option key={d.id} value={d.slug}>{d.name}</option>)}
          </select>
          <select value={assignee} onChange={(e) => setAssignee(e.target.value)} aria-label="Assignee">
            <option value="">Anyone</option>
            <option value="me">Assigned to me</option>
            <option value="none">Unassigned</option>
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort by">
            <option value="position">Manual order</option>
            <option value="due_date">Due date</option>
            <option value="priority">Priority</option>
            <option value="updated_at">Recently updated</option>
            <option value="created_at">Newest</option>
          </select>
          <label className="check-label">
            <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Archived
          </label>
          <RefreshingHint active={tasks.isFetching && !tasks.isPending && !tasks.isFetchingNextPage} />
        </div>
        <QueryView query={tasks} label="tasks">
          {() =>
            tasks.items.length === 0 ? (
              <EmptyState icon={ListTodo} title="No tasks match">
                {archived ? "No archived tasks match these filters." : "Create a task, or change the filters to see more."}
              </EmptyState>
            ) : (
              <>
                {tasks.items.map((task) => (
                  <TaskRecord
                    key={task.id}
                    task={task}
                    context={labels(task)}
                    onToggle={toggle}
                    onOpen={(t) => setOpen(t.id)}
                    busy={pendingId === task.id}
                  />
                ))}
                <LoadMore {...tasks} />
              </>
            )
          }
        </QueryView>
      </section>
      <p className="small-note">Subtasks are listed inside their parent task. Changes are saved to Booski Core and shared with your workspace.</p>
      {openId && <TaskDetailModal key={openId} taskId={openId} onClose={() => setOpen(null)} />}
    </div>
  );
}
