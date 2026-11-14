import { CheckCircle2, ChevronRight, Circle } from "lucide-react";
import type { Task } from "../../api/types";
import { formatDate, isOverdue, PRIORITY, TASK_STATUS } from "../../lib/format";

export interface TaskContext {
  projectName?: string;
  departmentName?: string;
  assigneeName?: string;
}

/**
 * One row in a task list. The circle completes or reopens the task (only when you're allowed to edit
 * it); the title opens its details.
 */
export function TaskRecord({ task, context, onToggle, onOpen, busy = false }: {
  task: Task;
  context: TaskContext;
  onToggle: (task: Task) => void;
  onOpen: (task: Task) => void;
  busy?: boolean;
}) {
  const done = task.status === "done";
  const overdue = isOverdue(task.due_date, task.status);
  const assignee = !task.assignee_user_id ? "Unassigned" : context.assigneeName ? `@${context.assigneeName}` : "Assigned";
  const meta = [context.projectName, context.departmentName, assignee]
    .filter(Boolean)
    .join(" · ");
  return (
    <div className="task-record" data-testid="task-row">
      <button
        type="button"
        className="task-toggle"
        onClick={() => onToggle(task)}
        disabled={!task.can_edit || busy || task.status === "cancelled"}
        aria-pressed={done}
        aria-label={`Mark “${task.title}” as ${done ? "not done" : "done"}`}
        title={task.can_edit ? undefined : "You can't edit this task"}
      >
        {done ? <CheckCircle2 className="task-done" size={18} aria-hidden="true" /> : <Circle className="task-open" size={18} aria-hidden="true" />}
      </button>
      <button type="button" className="task-open-button" onClick={() => onOpen(task)}>
        <b className={done ? "done" : ""}>{task.title}</b>
        <small>{meta}</small>
      </button>
      <span className="task-meta">
        {task.due_date && (
          <small className={overdue ? "overdue-text" : undefined}>{overdue ? "Overdue · " : "Due "}{formatDate(task.due_date)}</small>
        )}
        <span className={`status-tag status-${task.status}`}>{TASK_STATUS[task.status]}</span>
      </span>
      <em className={`severity ${task.priority}`}>{PRIORITY[task.priority]}</em>
      <ChevronRight size={15} className="muted-text" aria-hidden="true" />
    </div>
  );
}
