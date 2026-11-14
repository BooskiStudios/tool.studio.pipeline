import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { TaskInput } from "../api/types";

interface TasksContextValue {
  isTaskFormOpen: boolean;
  /** Pre-filled values for the "Create a task" dialog (e.g. the project or department you're in). */
  taskFormDefaults: TaskInput;
  openTaskForm: (defaults?: TaskInput) => void;
  closeTaskForm: () => void;
}

const TasksContext = createContext<TasksContextValue | null>(null);

/**
 * Opens the shared "Create a task" dialog from anywhere (Command Centre, Task Centre, project and
 * department workspaces). Tasks themselves are stored in Booski Core; see `api/hooks.ts`.
 */
export function TasksProvider({ children }: { children: ReactNode }) {
  const [isTaskFormOpen, setTaskFormOpen] = useState(false);
  const [taskFormDefaults, setDefaults] = useState<TaskInput>({});

  const openTaskForm = useCallback((defaults: TaskInput = {}) => {
    setDefaults(defaults);
    setTaskFormOpen(true);
  }, []);
  const closeTaskForm = useCallback(() => setTaskFormOpen(false), []);

  const value = useMemo<TasksContextValue>(
    () => ({ isTaskFormOpen, taskFormDefaults, openTaskForm, closeTaskForm }),
    [isTaskFormOpen, taskFormDefaults, openTaskForm, closeTaskForm],
  );
  return <TasksContext.Provider value={value}>{children}</TasksContext.Provider>;
}

export function useTasks(): TasksContextValue {
  const value = useContext(TasksContext);
  if (!value) throw new Error("useTasks must be used inside <TasksProvider>");
  return value;
}
