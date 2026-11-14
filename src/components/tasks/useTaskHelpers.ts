import { useCallback, useMemo } from "react";
import { errorMessage, isApiError } from "../../api/client";
import { useDepartments, useMemberNames, useProjectIndex, useUpdateTask } from "../../api/hooks";
import type { Task } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import type { TaskContext } from "./TaskRecord";

/** Labels for a task's project, department and assignee. */
export function useTaskLabels(): (task: Task) => TaskContext {
  const projects = useProjectIndex();
  const departments = useDepartments();
  const nameOf = useMemberNames();
  const departmentNames = useMemo(() => new Map((departments.data ?? []).map((d) => [d.id, d.name])), [departments.data]);
  return useCallback(
    (task: Task) => ({
      projectName: task.project_id ? projects.get(task.project_id)?.name : undefined,
      departmentName: task.department_id ? departmentNames.get(task.department_id) : undefined,
      assigneeName: nameOf(task.assignee_user_id),
    }),
    [projects, departmentNames, nameOf],
  );
}

/**
 * Tick a task done (or reopen it) with an optimistic update. If Booski Core refuses — for example
 * because someone else edited the task first — the list snaps back and the reason is shown.
 */
export function useToggleTask(): { toggle: (task: Task) => void; pendingId: string | undefined } {
  const update = useUpdateTask();
  const notify = useToast();
  const toggle = useCallback(
    (task: Task) => {
      const status = task.status === "done" ? "todo" : "done";
      update.mutate(
        { task, changes: { status } },
        {
          onError: (error) =>
            notify(
              isApiError(error, "conflict")
                ? `“${task.title}” was changed by someone else, so nothing was saved. The latest version is now shown.`
                : errorMessage(error),
            ),
        },
      );
    },
    [notify, update],
  );
  return { toggle, pendingId: update.isPending ? update.variables?.task.id : undefined };
}
