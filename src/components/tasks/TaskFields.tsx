import { useDepartments, useMembers, useMilestones, useProjectList, useWorkstreams } from "../../api/hooks";
import type { TaskInput, TaskPriority, TaskStatus } from "../../api/types";
import { useMe } from "../../auth/AuthProvider";
import { PRIORITY, TASK_STATUS } from "../../lib/format";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { Field } from "../ui";

export interface TaskDraft {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  project_id: string;
  department_id: string;
  workstream_id: string;
  milestone_id: string;
  assignee_user_id: string;
  start_date: string;
  due_date: string;
}

export function draftFrom(input: TaskInput): TaskDraft {
  return {
    title: input.title ?? "",
    description: input.description ?? "",
    status: input.status ?? "todo",
    priority: input.priority ?? "medium",
    project_id: input.project_id ?? "",
    department_id: input.department_id ?? "",
    workstream_id: input.workstream_id ?? "",
    milestone_id: input.milestone_id ?? "",
    assignee_user_id: input.assignee_user_id ?? "",
    start_date: input.start_date ?? "",
    due_date: input.due_date ?? "",
  };
}

/** Form values → API body; empty selections become `null` (no project, unassigned, no date…). */
export function inputFrom(draft: TaskDraft): TaskInput {
  const orNull = (value: string) => value || null;
  return {
    title: draft.title.trim(),
    description: draft.description,
    status: draft.status,
    priority: draft.priority,
    project_id: orNull(draft.project_id),
    department_id: orNull(draft.department_id),
    workstream_id: orNull(draft.workstream_id),
    milestone_id: orNull(draft.milestone_id),
    assignee_user_id: orNull(draft.assignee_user_id),
    start_date: orNull(draft.start_date),
    due_date: orNull(draft.due_date),
  };
}

/**
 * The shared task fields. Only projects where you may create tasks are offered; people who may only
 * edit their own work (collaborators) can only assign tasks to themselves. Booski Core re-checks all of it.
 */
export function TaskFields({ draft, onChange, projectLocked = false, titleError }: {
  draft: TaskDraft;
  onChange: (next: TaskDraft) => void;
  projectLocked?: boolean;
  titleError?: string | null;
}) {
  const me = useMe();
  const { can } = useWorkspace();
  const projects = useProjectList();
  const departments = useDepartments();
  const members = useMembers();
  const projectSlug = projects.data?.find((p) => p.id === draft.project_id)?.slug;
  const workstreams = useWorkstreams(projectSlug);
  const milestones = useMilestones(projectSlug);
  const set = <K extends keyof TaskDraft>(key: K, value: TaskDraft[K]) => onChange({ ...draft, [key]: value });

  const writableProjects = (projects.data ?? []).filter((p) => p.capabilities.includes("tasks.create") || p.id === draft.project_id);
  const assignAnyone = can("tasks.edit_any");
  const people = (members.data ?? []).filter((m) => assignAnyone || m.user_id === me.user.id || m.user_id === draft.assignee_user_id);

  return (
    <div className="form-grid">
      <Field label="Title" error={titleError} className="span-2">
        {(props) => <input {...props} value={draft.title} onChange={(e) => set("title", e.target.value)} maxLength={200} data-autofocus />}
      </Field>
      <Field label="Description" className="span-2">
        {(props) => <textarea {...props} rows={3} value={draft.description} onChange={(e) => set("description", e.target.value)} />}
      </Field>
      <Field label="Project">
        {(props) => (
          <select
            {...props}
            value={draft.project_id}
            disabled={projectLocked}
            onChange={(e) => onChange({ ...draft, project_id: e.target.value, workstream_id: "", milestone_id: "" })}
          >
            <option value="">No project (studio-wide)</option>
            {writableProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
      </Field>
      <Field label="Department">
        {(props) => (
          <select {...props} value={draft.department_id} onChange={(e) => set("department_id", e.target.value)}>
            <option value="">No department</option>
            {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        )}
      </Field>
      {draft.project_id && (
        <>
          <Field label="Workstream">
            {(props) => (
              <select {...props} value={draft.workstream_id} onChange={(e) => set("workstream_id", e.target.value)}>
                <option value="">None</option>
                {(workstreams.data ?? []).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Milestone">
            {(props) => (
              <select {...props} value={draft.milestone_id} onChange={(e) => set("milestone_id", e.target.value)}>
                <option value="">None</option>
                {(milestones.data ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            )}
          </Field>
        </>
      )}
      <Field label="Assignee">
        {(props) => (
          <select {...props} value={draft.assignee_user_id} onChange={(e) => set("assignee_user_id", e.target.value)}>
            <option value="">Unassigned</option>
            {people.map((m) => (
              <option key={m.user_id} value={m.user_id}>{m.user_id === me.user.id ? `${m.display_name} (you)` : m.display_name}</option>
            ))}
          </select>
        )}
      </Field>
      <Field label="Priority">
        {(props) => (
          <select {...props} value={draft.priority} onChange={(e) => set("priority", e.target.value as TaskPriority)}>
            {(Object.keys(PRIORITY) as TaskPriority[]).map((p) => <option key={p} value={p}>{PRIORITY[p]}</option>)}
          </select>
        )}
      </Field>
      <Field label="Status">
        {(props) => (
          <select {...props} value={draft.status} onChange={(e) => set("status", e.target.value as TaskStatus)}>
            {(Object.keys(TASK_STATUS) as TaskStatus[]).map((s) => <option key={s} value={s}>{TASK_STATUS[s]}</option>)}
          </select>
        )}
      </Field>
      <Field label="Start date">
        {(props) => <input {...props} type="date" value={draft.start_date} onChange={(e) => set("start_date", e.target.value)} />}
      </Field>
      <Field label="Due date">
        {(props) => <input {...props} type="date" value={draft.due_date} onChange={(e) => set("due_date", e.target.value)} />}
      </Field>
    </div>
  );
}
