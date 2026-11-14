import { useState, type FormEvent } from "react";
import { useWorkspaceMutation } from "../api/hooks";
import { tasks } from "../api/core";
import type { TaskInput } from "../api/types";
import { useTasks } from "../context/TasksContext";
import { useToast } from "../context/ToastContext";
import { Modal } from "./Modal";
import { draftFrom, inputFrom, TaskFields, type TaskDraft } from "./tasks/TaskFields";
import { FormError } from "./ui";

/** "Create a task" dialog. Pre-filled with the project, department or parent task you opened it from. */
export function TaskFormModal() {
  const { taskFormDefaults, closeTaskForm } = useTasks();
  const notify = useToast();
  const [draft, setDraft] = useState<TaskDraft>(() => draftFrom(taskFormDefaults));
  const [titleError, setTitleError] = useState<string | null>(null);
  const create = useWorkspaceMutation((ws, body: TaskInput) => tasks.create(ws, body));
  const parentId = taskFormDefaults.parent_task_id ?? null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft.title.trim()) {
      setTitleError("Give the task a title.");
      return;
    }
    setTitleError(null);
    create.mutate(
      { ...inputFrom(draft), parent_task_id: parentId },
      {
        onSuccess: (task) => {
          notify(`Task created: ${task.title}`);
          closeTaskForm();
        },
      },
    );
  };

  return (
    <Modal
      eyebrow="TASK CENTRE"
      title={parentId ? "Add a subtask" : "Create a task"}
      description="Saved to Booski Core and visible to everyone who can see its project."
      onClose={closeTaskForm}
      size="wide"
    >
      <form onSubmit={submit} noValidate>
        <TaskFields draft={draft} onChange={setDraft} projectLocked={Boolean(parentId)} titleError={titleError} />
        <FormError error={create.error} />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={closeTaskForm}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={create.isPending}>
            {create.isPending ? "Saving…" : parentId ? "Add subtask" : "Create task"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
