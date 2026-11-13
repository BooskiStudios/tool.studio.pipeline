import { useState } from "react";
import { useMatch } from "react-router";
import { useTasks } from "../context/TasksContext";
import { useToast } from "../context/ToastContext";
import type { DepartmentSlug } from "../types";
import { departmentNames } from "./layout/navigation";
import { Modal } from "./Modal";

/** "Create a task" dialog. Tasks are attributed to the department you are in, else Studio Operations. */
export function TaskFormModal() {
  const { addTask, closeTaskForm } = useTasks();
  const notify = useToast();
  const [title, setTitle] = useState("");
  const departmentSlug = useMatch("/departments/:departmentSlug")?.params.departmentSlug as DepartmentSlug | undefined;
  const department = (departmentSlug && departmentNames[departmentSlug]) || "Studio Operations";

  const submit = () => {
    if (!title.trim()) return;
    addTask(title.trim(), department);
    closeTaskForm();
    notify("Demo task added to this session.");
  };

  return (
    <Modal
      eyebrow="TASK CENTRE"
      title="Create a task"
      description="Add a task to your local demo workspace. It is kept in this browser tab only and is lost on refresh."
      onClose={closeTaskForm}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          data-autofocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs doing?"
          aria-label="Task title"
        />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={closeTaskForm}>Cancel</button>
          <button type="submit" className="primary-btn">Add task</button>
        </div>
      </form>
    </Modal>
  );
}
