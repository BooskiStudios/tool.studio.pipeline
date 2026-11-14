import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { useProjectList } from "../api/hooks";
import type { Project } from "../api/types";

interface ProjectContextValue {
  /** `undefined` while loading. Only projects you can see: restricted projects you aren't on never arrive. */
  projects: Project[] | undefined;
  /** Set when the project list failed to load. */
  error: unknown;
  /** The project the studio is focused on (Command Centre's Project Overview, department context). */
  currentProject: Project | undefined;
  selectProject: (slug: string) => void;
  refetch: () => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

/**
 * The workspace's projects (from Booski Core) and the "current project" selection. The selection
 * defaults to the first project and follows the project workspace you open.
 */
export function ProjectProvider({ children }: { children: ReactNode }) {
  const query = useProjectList();
  const [selectedSlug, setSelectedSlug] = useState<string | undefined>(undefined);
  const { data, error, refetch } = query;

  const value = useMemo<ProjectContextValue>(() => {
    const currentProject = data?.find((p) => p.slug === selectedSlug) ?? data?.[0];
    return {
      projects: data,
      error: query.isError ? error : null,
      currentProject,
      selectProject: setSelectedSlug,
      refetch: () => void refetch(),
    };
  }, [data, error, query.isError, refetch, selectedSlug]);

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjects(): ProjectContextValue {
  const value = useContext(ProjectContext);
  if (!value) throw new Error("useProjects must be used inside <ProjectProvider>");
  return value;
}
