import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { studioApi } from "../services";
import type { Task } from "../types";

interface TasksContextValue {
  /** `undefined` while the initial list is loading. */
  tasks: Task[] | undefined;
  toggleTask: (id: string) => void;
  addTask: (title: string, department: string) => void;
  isTaskFormOpen: boolean;
  openTaskForm: () => void;
  closeTaskForm: () => void;
}

const TasksContext = createContext<TasksContextValue | null>(null);

/**
 * Session task list.
 *
 * DEMO BEHAVIOUR: the initial list comes from `studioApi.listTasks()`, but
 * adding and ticking off tasks only changes browser memory. Changes are lost on
 * refresh. When Booski Core exists, these mutations become API calls.
 */
export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<Task[] | undefined>(undefined);
  const [isTaskFormOpen, setTaskFormOpen] = useState(false);

  useEffect(() => {
    let current = true;
    studioApi.listTasks().then((initial) => current && setTasks(initial));
    return () => {
      current = false;
    };
  }, []);

  const toggleTask = useCallback((id: string) => {
    setTasks((list) => list?.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));
  }, []);

  const addTask = useCallback((title: string, department: string) => {
    const task: Task = { id: `session-${Date.now()}`, title, department, priority: "Medium", done: false };
    setTasks((list) => [...(list ?? []), task]);
  }, []);

  const openTaskForm = useCallback(() => setTaskFormOpen(true), []);
  const closeTaskForm = useCallback(() => setTaskFormOpen(false), []);

  const value = useMemo<TasksContextValue>(
    () => ({ tasks, toggleTask, addTask, isTaskFormOpen, openTaskForm, closeTaskForm }),
    [tasks, toggleTask, addTask, isTaskFormOpen, openTaskForm, closeTaskForm],
  );

  return <TasksContext.Provider value={value}>{children}</TasksContext.Provider>;
}

export function useTasks(): TasksContextValue {
  const value = useContext(TasksContext);
  if (!value) throw new Error("useTasks must be used inside <TasksProvider>");
  return value;
}
