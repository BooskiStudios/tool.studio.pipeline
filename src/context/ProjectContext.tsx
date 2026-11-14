import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { studioApi } from "../services";
import type { Project } from "../types";

interface ProjectContextValue {
  /** `undefined` while loading. */
  projects: Project[] | undefined;
  /** The project the studio is currently focused on (shown in Project Overview and department context). */
  currentProject: Project | undefined;
  selectProject: (slug: string) => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

/**
 * Holds the project list and the "current project" selection.
 *
 * The current project defaults to the first project. It changes when you pick a
 * project in the Command Centre's Project Overview, or open a project workspace.
 */
export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[] | undefined>(undefined);
  const [selectedSlug, setSelectedSlug] = useState<string | undefined>(undefined);

  useEffect(() => {
    let current = true;
    studioApi.listProjects().then((list) => current && setProjects(list));
    return () => {
      current = false;
    };
  }, []);

  const value = useMemo<ProjectContextValue>(() => {
    const currentProject = projects?.find((p) => p.slug === selectedSlug) ?? projects?.[0];
    return { projects, currentProject, selectProject: setSelectedSlug };
  }, [projects, selectedSlug]);

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjects(): ProjectContextValue {
  const value = useContext(ProjectContext);
  if (!value) throw new Error("useProjects must be used inside <ProjectProvider>");
  return value;
}
