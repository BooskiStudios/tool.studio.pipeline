import { useState, type FormEvent } from "react";
import { Archive, Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { isApiError } from "../../api/client";
import * as core from "../../api/core";
import {
  useMemberNames, useProjectIndex, useTask, useTaskComments, useTaskHistory, useTaskList, useWorkspaceMutation,
} from "../../api/hooks";
import type { Comment, Task, TaskInput } from "../../api/types";
import { useMe } from "../../auth/AuthProvider";
import { useTasks } from "../../context/TasksContext";
import { useToast } from "../../context/ToastContext";
import { formatDate, formatDateTime, PRIORITY, TASK_STATUS, timeAgo } from "../../lib/format";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { ActivityList } from "../ActivityList";
import { Modal } from "../Modal";
import { ConflictNotice, FormError, LoadMore, QueryView } from "../ui";
import { draftFrom, inputFrom, TaskFields, type TaskDraft } from "./TaskFields";
import { TaskRecord } from "./TaskRecord";
import { useTaskLabels, useToggleTask } from "./useTaskHelpers";

type Section = "Details" | "Subtasks" | "Comments" | "History";
const SECTIONS: Section[] = ["Details", "Subtasks", "Comments", "History"];

function TaskEditor({ task, onDone }: { task: Task; onDone: () => void }) {
  const { slug } = useWorkspace();
  const queryClient = useQueryClient();
  const notify = useToast();
  const [draft, setDraft] = useState<TaskDraft>(() => draftFrom(task));
  const update = useWorkspaceMutation((ws, body: TaskInput) => core.tasks.update(ws, task.id, body));
  const conflict = isApiError(update.error, "conflict");

  const save = (event: FormEvent) => {
    event.preventDefault();
    // Send only what changed (a task's project can't be changed after creation).
    const before = inputFrom(draftFrom(task));
    const after = inputFrom(draft);
    const changes = Object.fromEntries(
      (Object.keys(after) as (keyof TaskInput)[])
        .filter((key) => key !== "project_id" && after[key] !== before[key])
        .map((key) => [key, after[key]]),
    ) as TaskInput;
    if (Object.keys(changes).length === 0) {
      onDone();
      return;
    }
    if (changes.title === "") return;
    update.mutate(
      { ...changes, version: task.version },
      {
        onSuccess: () => {
          notify("Task saved.");
          onDone();
        },
      },
    );
  };

  const reload = async () => {
    await queryClient.invalidateQueries({ queryKey: ["ws", slug] });
    update.reset();
    onDone();
  };

  return (
    <form onSubmit={save} noValidate>
      <TaskFields draft={draft} onChange={setDraft} projectLocked />
      {conflict ? <ConflictNotice onRefresh={() => void reload()} /> : <FormError error={update.error} />}
      <div className="modal-actions">
        <button type="button" className="secondary-btn" onClick={onDone}>Cancel</button>
        <button type="submit" className="primary-btn" disabled={update.isPending || conflict}>
          {update.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

function TaskSummary({ task }: { task: Task }) {
  const labels = useTaskLabels()(task);
  const nameOf = useMemberNames();
  return (
    <>
      <dl className="detail-grid">
        <dt>Status</dt><dd><span className={`status-tag status-${task.status}`}>{TASK_STATUS[task.status]}</span></dd>
        <dt>Priority</dt><dd><em className={`severity ${task.priority}`}>{PRIORITY[task.priority]}</em></dd>
        <dt>Project</dt><dd>{labels.projectName ?? "Studio-wide"}</dd>
        <dt>Department</dt><dd>{labels.departmentName ?? "—"}</dd>
        <dt>Assignee</dt><dd>{labels.assigneeName ?? "Unassigned"}</dd>
        <dt>Start</dt><dd>{formatDate(task.start_date)}</dd>
        <dt>Due</dt><dd>{formatDate(task.due_date)}</dd>
        <dt>Created</dt><dd>{formatDateTime(task.created_at)} by {nameOf(task.created_by_user_id) ?? "a former member"}</dd>
        {task.completed_at && <><dt>Completed</dt><dd>{formatDateTime(task.completed_at)}</dd></>}
      </dl>
      {task.description ? <p className="detail-text">{task.description}</p> : <p className="muted-text">No description.</p>}
    </>
  );
}

function Subtasks({ task, onOpen }: { task: Task; onOpen: (task: Task) => void }) {
  const { openTaskForm } = useTasks();
  const subtasks = useTaskList({ parent: task.id, sort: "position" });
  const labels = useTaskLabels();
  const { toggle, pendingId } = useToggleTask();
  const projects = useProjectIndex();
  const project = task.project_id ? projects.get(task.project_id) : undefined;
  const { can } = useWorkspace();
  const canCreate = project ? project.capabilities.includes("tasks.create") : can("tasks.create");
  return (
    <>
      <QueryView query={subtasks} label="subtasks">
        {() =>
          subtasks.items.length === 0 ? (
            <p className="muted-text">No subtasks.</p>
          ) : (
            <>
              {subtasks.items.map((t) => (
                <TaskRecord key={t.id} task={t} context={labels(t)} onToggle={toggle} onOpen={onOpen} busy={pendingId === t.id} />
              ))}
              <LoadMore {...subtasks} />
            </>
          )
        }
      </QueryView>
      {canCreate && (
        <button
          type="button"
          className="inline-add"
          onClick={() => openTaskForm({ parent_task_id: task.id, project_id: task.project_id, department_id: task.department_id })}
        >
          <Plus size={14} aria-hidden="true" /> Add subtask
        </button>
      )}
    </>
  );
}

function CommentRow({ comment }: { comment: Comment }) {
  const me = useMe();
  const nameOf = useMemberNames();
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(comment.body);
  const edit = useWorkspaceMutation((ws, text: string) => core.tasks.editComment(ws, comment.id, text));
  const remove = useWorkspaceMutation((ws, _: void) => core.tasks.deleteComment(ws, comment.id));
  const mine = comment.author_user_id === me.user.id;

  if (comment.deleted) {
    return <div className="comment-row deleted"><small>Comment deleted · {timeAgo(comment.created_at)}</small></div>;
  }
  return (
    <div className="comment-row">
      <div className="comment-head">
        <b>{nameOf(comment.author_user_id) ?? "Former member"}</b>
        <small>{timeAgo(comment.created_at)}{comment.edited_at ? " · edited" : ""}</small>
        {mine && !editing && (
          <span className="comment-actions">
            <button type="button" onClick={() => setEditing(true)} aria-label="Edit comment"><Pencil size={12} aria-hidden="true" /></button>
            <button type="button" onClick={() => remove.mutate()} aria-label="Delete comment" disabled={remove.isPending}>
              <Trash2 size={12} aria-hidden="true" />
            </button>
          </span>
        )}
      </div>
      {editing ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) edit.mutate(body.trim(), { onSuccess: () => setEditing(false) });
          }}
        >
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={2} aria-label="Edit comment" />
          <FormError error={edit.error} />
          <div className="modal-actions">
            <button type="button" className="secondary-btn" onClick={() => { setEditing(false); setBody(comment.body); }}>Cancel</button>
            <button type="submit" className="primary-btn" disabled={edit.isPending}>Save</button>
          </div>
        </form>
      ) : (
        <p>{comment.body}</p>
      )}
      <FormError error={remove.error} />
    </div>
  );
}

function Comments({ task }: { task: Task }) {
  const comments = useTaskComments(task.id);
  const projects = useProjectIndex();
  const { can } = useWorkspace();
  const project = task.project_id ? projects.get(task.project_id) : undefined;
  const canComment = project ? project.capabilities.includes("comments.write") : can("comments.write");
  const [body, setBody] = useState("");
  const add = useWorkspaceMutation((ws, text: string) => core.tasks.addComment(ws, task.id, text));
  return (
    <>
      <QueryView query={comments} label="comments">
        {() => (
          <>
            {comments.items.length === 0 && <p className="muted-text">No comments yet.</p>}
            {comments.items.map((c) => <CommentRow key={c.id} comment={c} />)}
            <LoadMore {...comments} />
          </>
        )}
      </QueryView>
      {canComment && (
        <form
          className="comment-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) add.mutate(body.trim(), { onSuccess: () => setBody("") });
          }}
        >
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={2} placeholder="Add a comment…" aria-label="New comment" />
          <FormError error={add.error} />
          <div className="modal-actions">
            <button type="submit" className="primary-btn" disabled={add.isPending || !body.trim()}>Comment</button>
          </div>
        </form>
      )}
    </>
  );
}

function History({ task }: { task: Task }) {
  const history = useTaskHistory(task.id);
  return (
    <QueryView query={history} label="history">
      {() => (
        <>
          <ActivityList events={history.items} emptyText="No changes recorded yet." />
          <LoadMore {...history} />
        </>
      )}
    </QueryView>
  );
}

/** A task's details, editing, subtasks, comments and history. */
export function TaskDetailModal({ taskId, onClose }: { taskId: string; onClose: () => void }) {
  const [currentId, setCurrentId] = useState(taskId);
  const task = useTask(currentId);
  const [section, setSection] = useState<Section>("Details");
  const [editing, setEditing] = useState(false);
  const open = (next: Task) => {
    setCurrentId(next.id);
    setSection("Details");
    setEditing(false);
  };
  const notify = useToast();
  const archive = useWorkspaceMutation((ws, vars: { task: Task; archived: boolean }) =>
    core.tasks.update(ws, vars.task.id, { archived: vars.archived, version: vars.task.version }),
  );

  return (
    <Modal eyebrow="TASK" title={task.data?.title ?? "Task"} onClose={onClose} size="wide">
      <QueryView query={task} label="this task">
        {(t) => (
          <>
            {t.archived_at && <div className="auth-notice">This task is archived.</div>}
            {t.parent_task_id && (
              <button type="button" className="inline-link" onClick={() => setCurrentId(t.parent_task_id ?? currentId)}>
                ← Back to parent task
              </button>
            )}
            <div className="workspace-tabs" role="group" aria-label="Task sections">
              {SECTIONS.map((s) => (
                <button type="button" key={s} aria-pressed={section === s} className={section === s ? "active-tab" : ""} onClick={() => setSection(s)}>
                  {s}
                </button>
              ))}
            </div>
            {section === "Details" &&
              (editing ? (
                <TaskEditor task={t} onDone={() => setEditing(false)} />
              ) : (
                <>
                  <TaskSummary task={t} />
                  <FormError error={archive.error} />
                  {t.can_edit && (
                    <div className="modal-actions">
                      <button
                        type="button"
                        className="secondary-btn"
                        disabled={archive.isPending}
                        onClick={() =>
                          archive.mutate(
                            { task: t, archived: !t.archived_at },
                            { onSuccess: () => notify(t.archived_at ? "Task restored." : "Task archived.") },
                          )
                        }
                      >
                        {t.archived_at ? <RotateCcw size={13} aria-hidden="true" /> : <Archive size={13} aria-hidden="true" />}
                        {t.archived_at ? "Restore" : "Archive"}
                      </button>
                      <button type="button" className="primary-btn" onClick={() => setEditing(true)}>
                        <Pencil size={13} aria-hidden="true" /> Edit task
                      </button>
                    </div>
                  )}
                  {!t.can_edit && <p className="small-note">You can view this task but not change it.</p>}
                </>
              ))}
            {section === "Subtasks" && <Subtasks task={t} onOpen={open} />}
            {section === "Comments" && <Comments task={t} />}
            {section === "History" && <History task={t} />}
          </>
        )}
      </QueryView>
    </Modal>
  );
}
