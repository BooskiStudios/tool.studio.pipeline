import { createContext, Fragment, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { useMe } from "../auth/AuthProvider";
import type { Capability, MembershipSummary, Role } from "../api/types";
import { paths } from "../routes";
import { ROLE_CAPABILITIES } from "./roles";
import { NoWorkspacePage } from "./NoWorkspacePage";

const STORAGE_KEY = "booski.activeWorkspace";

export interface WorkspaceContextValue {
  /** The active workspace's slug; every studio request is scoped to it. */
  slug: string;
  name: string;
  role: Role;
  memberships: MembershipSummary[];
  /** Whether your workspace role allows this. Projects can narrow it further (see `project.capabilities`). */
  can: (capability: Capability) => boolean;
  switchWorkspace: (slug: string) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function rememberedSlug(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // storage blocked: fall back to the first workspace
  }
}

/** Make `slug` the active workspace next time the app loads (e.g. right after joining it). */
export function rememberWorkspace(slug: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, slug); // a preference, not a secret
  } catch {
    // ignore
  }
}

/**
 * The workspace everything is scoped to. People can belong to several; the choice is remembered per
 * browser. Switching drops every cached record and remounts the app under the new workspace, so nothing
 * from the previous workspace can appear in the next one.
 */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const me = useMe();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const memberships = me.workspaces;
  const [selected, setSelected] = useState<string | null>(rememberedSlug);
  const active = memberships.find((m) => m.workspace_slug === selected) ?? memberships[0];

  const switchWorkspace = useCallback(
    (slug: string) => {
      if (slug === active?.workspace_slug) return;
      queryClient.removeQueries({ queryKey: ["ws"] });
      rememberWorkspace(slug);
      setSelected(slug);
      navigate(paths.home);
    },
    [active, navigate, queryClient],
  );

  const value = useMemo<WorkspaceContextValue | null>(() => {
    if (!active) return null;
    const capabilities = ROLE_CAPABILITIES[active.role];
    return {
      slug: active.workspace_slug,
      name: active.workspace_name,
      role: active.role,
      memberships,
      can: (capability) => capabilities.has(capability),
      switchWorkspace,
    };
  }, [active, memberships, switchWorkspace]);

  if (!value) return <NoWorkspacePage />;
  return (
    <WorkspaceContext.Provider value={value}>
      {/* Remount everything on a switch so no component keeps state from the previous workspace. */}
      <Fragment key={value.slug}>{children}</Fragment>
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return value;
}
