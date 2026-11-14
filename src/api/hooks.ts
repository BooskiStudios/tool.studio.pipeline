/**
 * Shared data access for pages: cached, de-duplicated and refreshed in the background (TanStack Query).
 *
 * Every key starts with `["ws", <workspace slug>]`, so one workspace's data can never be served for
 * another, and switching workspace drops it all. Mutations refresh the active workspace's data, so
 * every screen showing a record (task lists, project progress, activity…) stays consistent.
 */

import {
  keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient, type InfiniteData, type QueryKey,
} from "@tanstack/react-query";
import { useMemo } from "react";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import type { QueryValue } from "./client";
import * as core from "./core";
import type { Page, Project, Task, TaskInput } from "./types";

type Filters = Record<string, QueryValue>;
const PAGE_SIZE = 50;

export function useWorkspaceKey(): (...parts: unknown[]) => QueryKey {
  const { slug } = useWorkspace();
  return (...parts: unknown[]) => ["ws", slug, ...parts];
}

/** Paginated list with "load more". `items` is every loaded page, flattened. */
function useCursorList<T>(key: QueryKey, load: (query: Filters, signal: AbortSignal) => Promise<Page<T>>, filters: Filters, enabled = true) {
  const query = useInfiniteQuery({
    queryKey: [...key, filters],
    queryFn: ({ pageParam, signal }) => load({ ...filters, limit: filters.limit ?? PAGE_SIZE, cursor: pageParam }, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    placeholderData: keepPreviousData,
    enabled,
  });
  const items = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);
  return { ...query, items };
}

async function allPages<T>(load: (cursor: string | undefined) => Promise<Page<T>>, maxPages = 20): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | undefined;
  for (let i = 0; i < maxPages; i++) {
    const page = await load(cursor);
    items.push(...page.items);
    if (!page.next_cursor) break;
    cursor = page.next_cursor;
  }
  return items;
}

// ---------------------------------------------------------------- workspace

export function useMembers() {
  const { slug } = useWorkspace();
  return useQuery({ queryKey: ["ws", slug, "members"], queryFn: ({ signal }) => core.workspaces.members(slug, signal) });
}

/** user id → display name, for showing people on records. Unknown ids (former members) map to undefined. */
export function useMemberNames(): (userId: string | null | undefined) => string | undefined {
  const members = useMembers();
  return useMemo(() => {
    const names = new Map((members.data ?? []).map((m) => [m.user_id, m.display_name]));
    return (userId) => (userId ? names.get(userId) : undefined);
  }, [members.data]);
}

export function useInvitations(enabled: boolean) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "invitations"],
    queryFn: ({ signal }) => core.workspaces.invitations(slug, signal),
    enabled,
  });
}

export function useDepartments() {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "departments"],
    queryFn: ({ signal }) => core.departments.list(slug, signal),
    staleTime: 5 * 60_000,
  });
}

// ---------------------------------------------------------------- projects

/** Every project you can see (active, or archived with `archived: true`). Restricted projects you aren't on never arrive. */
export function useProjectList(archived = false) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "projects", { archived }],
    queryFn: ({ signal }) =>
      allPages((cursor) => core.projects.list(slug, { archived, sort: "name", limit: 200, cursor }, signal)),
  });
}

export function useProject(projectSlug: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "project", projectSlug],
    queryFn: ({ signal }) => core.projects.get(slug, projectSlug ?? "", signal),
    enabled: Boolean(projectSlug),
  });
}

/** id → project, for labelling records. Projects you can't see are simply absent. */
export function useProjectIndex(): Map<string, Project> {
  const projects = useProjectList();
  return useMemo(() => new Map((projects.data ?? []).map((p) => [p.id, p])), [projects.data]);
}

export function useMilestones(projectSlug: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "milestones", projectSlug],
    queryFn: ({ signal }) => core.projects.milestones(slug, projectSlug ?? "", signal),
    enabled: Boolean(projectSlug),
  });
}

export function useWorkstreams(projectSlug: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "workstreams", projectSlug],
    queryFn: ({ signal }) => core.projects.workstreams(slug, projectSlug ?? "", signal),
    enabled: Boolean(projectSlug),
  });
}

export function useProjectMembers(projectSlug: string | undefined, enabled = true) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "project-members", projectSlug],
    queryFn: ({ signal }) => core.projects.members(slug, projectSlug ?? "", signal),
    enabled: Boolean(projectSlug) && enabled,
  });
}

// ---------------------------------------------------------------- tasks

export function useTaskList(filters: Filters, enabled = true) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "tasks"], (query, signal) => core.tasks.list(slug, query, signal), filters, enabled);
}

export function useTask(taskId: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "task", taskId],
    queryFn: ({ signal }) => core.tasks.get(slug, taskId ?? "", signal),
    enabled: Boolean(taskId),
  });
}

export function useTaskComments(taskId: string) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "comments", taskId], (q, signal) => core.tasks.comments(slug, taskId, q, signal), {});
}

export function useTaskHistory(taskId: string) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "task-history", taskId], (q, signal) => core.tasks.history(slug, taskId, q, signal), {});
}

/**
 * Edit a task with an optimistic update: lists show the change at once, and if Booski Core rejects it
 * (permission, validation, or someone else changed the task first) every list is put back exactly as
 * it was before the edit and the error is passed to the caller to explain.
 */
export function useUpdateTask() {
  const { slug } = useWorkspace();
  const queryClient = useQueryClient();
  const listKey = ["ws", slug, "tasks"];
  return useMutation({
    mutationFn: ({ task, changes }: { task: Task; changes: TaskInput }) =>
      core.tasks.update(slug, task.id, { ...changes, version: task.version }),
    onMutate: async ({ task, changes }) => {
      await queryClient.cancelQueries({ queryKey: listKey });
      const snapshots = queryClient.getQueriesData<InfiniteData<Page<Task>>>({ queryKey: listKey });
      const patch = { ...changes } as Partial<Task>;
      queryClient.setQueriesData<InfiniteData<Page<Task>>>({ queryKey: listKey }, (data) =>
        data && {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.map((item) => (item.id === task.id ? { ...item, ...patch } : item)),
          })),
        },
      );
      return { snapshots };
    },
    onError: (_error, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["ws", slug] }),
  });
}

// ---------------------------------------------------------------- knowledge, decisions, approvals, activity

export function useDocumentList(filters: Filters) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "documents"], (q, signal) => core.documents.list(slug, q, signal), filters);
}

export function useDocument(documentId: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "document", documentId],
    queryFn: ({ signal }) => core.documents.get(slug, documentId ?? "", signal),
    enabled: Boolean(documentId),
  });
}

export function useRevisions(documentId: string) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "revisions", documentId],
    queryFn: ({ signal }) => core.documents.revisions(slug, documentId, signal),
  });
}

export function useRevision(documentId: string, revisionNo: number | null) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "revision", documentId, revisionNo],
    queryFn: ({ signal }) => core.documents.revision(slug, documentId, revisionNo ?? 0, signal),
    enabled: revisionNo !== null,
    staleTime: Infinity, // revisions never change
  });
}

export function useDecisionList(filters: Filters) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "decisions"], (q, signal) => core.decisions.list(slug, q, signal), filters);
}

export function useDecisionHistory(decisionId: string) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "decision-history", decisionId],
    queryFn: ({ signal }) => core.decisions.history(slug, decisionId, signal),
  });
}

export function useApprovalList(filters: Filters, enabled = true) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "approvals"], (q, signal) => core.approvals.list(slug, q, signal), filters, enabled);
}

export function useApproval(approvalId: string | undefined) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "approval", approvalId],
    queryFn: ({ signal }) => core.approvals.get(slug, approvalId ?? "", signal),
    enabled: Boolean(approvalId),
  });
}

export function useReviews(approvalId: string) {
  const { slug } = useWorkspace();
  return useQuery({
    queryKey: ["ws", slug, "reviews", approvalId],
    queryFn: ({ signal }) => core.approvals.reviews(slug, approvalId, signal),
  });
}

export function useActivity(filters: Filters, enabled = true) {
  const { slug } = useWorkspace();
  return useCursorList(["ws", slug, "activity"], (q, signal) => core.activity.list(slug, q, signal), filters, enabled);
}

// ---------------------------------------------------------------- mutations

/**
 * Any change to workspace data. On success the whole workspace's cache is marked stale, so open
 * screens refetch and every view of the changed record agrees.
 */
export function useWorkspaceMutation<TVariables, TResult>(action: (workspaceSlug: string, variables: TVariables) => Promise<TResult>) {
  const { slug } = useWorkspace();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: TVariables) => action(slug, variables),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ws", slug] }),
  });
}
