import { CheckCircle2, Circle } from "lucide-react";
import type { Task } from "../types";

/** One row in a full task list (Task Centre, Project Workspace → Tasks). */
export function TaskRecord({ task, onToggle }: { task: Task; onToggle: (id: string) => void }) {
  return (
    <div className="task-record">
      <button
        type="button"
        className="task-toggle"
        onClick={() => onToggle(task.id)}
        aria-pressed={task.done}
        aria-label={`Mark “${task.title}” as ${task.done ? "not done" : "done"}`}
      >
        {task.done ? <CheckCircle2 className="task-done" size={18} aria-hidden="true" /> : <Circle className="task-open" size={18} aria-hidden="true" />}
      </button>
      <span>
        <b className={task.done ? "done" : ""}>{task.title}</b>
        <small>{task.department}</small>
      </span>
      <em className={`severity ${task.priority.toLowerCase()}`}>{task.priority}</em>
    </div>
  );
}
