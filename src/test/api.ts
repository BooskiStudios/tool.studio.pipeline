/**
 * A fake Booski Core for unit tests: routes like "GET /auth/me" map to a JSON body, a handler, or
 * `{ status, body }`. Unknown routes answer 404, so a test never silently talks to a real server.
 * (The end-to-end tests in e2e/ use the real API.)
 */
import { vi } from "vitest";
import type { MeResponse, Project, Task } from "../api/types";

export interface Recorded {
  method: string;
  path: string;
  query: URLSearchParams;
  headers: Headers;
  body: unknown;
  credentials: RequestCredentials | undefined;
}

export interface Reply {
  status?: number;
  body?: unknown;
}

type Handler = (request: Recorded) => Reply | Promise<Reply>;
/** A JSON body, a fixed reply, or a handler computing the reply from the request. */
type Route = Handler | Reply | object;

export function reply(status: number, body?: unknown): Reply {
  return { status, body };
}

const isReply = (value: unknown): value is Reply =>
  typeof value === "object" && value !== null && "status" in value && Object.keys(value).every((k) => k === "status" || k === "body");

export function mockApi(routes: Record<string, Route>) {
  const calls: Recorded[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = (init?.method ?? "GET").toUpperCase();
    const request: Recorded = {
      method,
      path,
      query: url.searchParams,
      headers: new Headers(init?.headers),
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
      credentials: init?.credentials,
    };
    calls.push(request);
    if (init?.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const route = routes[`${method} ${path}`];
    let result: Reply;
    if (route === undefined) result = reply(404, { title: "Not Found", status: 404 });
    else if (typeof route === "function") result = await (route as Handler)(request);
    else if (isReply(route)) result = route;
    else result = { status: 200, body: route };
    const status = result.status ?? 200;
    if (status === 204) return new Response(null, { status });
    const type = status >= 400 ? "application/problem+json" : "application/json";
    return new Response(JSON.stringify(result.body ?? {}), { status, headers: { "content-type": type } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

// ---------------------------------------------------------------- fixtures

export const USER_ID = "00000000-0000-7000-8000-000000000001";

export function meFixture(overrides: Partial<MeResponse> = {}): MeResponse {
  return {
    user: { id: USER_ID, email: "olivia@booski.test", display_name: "Olivia Owner" },
    session: {
      id: "s1",
      created_at: "2026-11-14T09:00:00Z",
      last_seen_at: "2026-11-14T09:00:00Z",
      idle_expires_at: "2026-11-14T21:00:00Z",
      absolute_expires_at: "2026-12-14T09:00:00Z",
      ip: "127.0.0.1",
      user_agent: "test",
      current: true,
    },
    workspaces: [
      { workspace_id: "w1", workspace_slug: "booski", workspace_name: "Booski Studios", role: "owner" },
    ],
    ...overrides,
  };
}

export function projectFixture(overrides: Partial<Project> = {}): Project {
  return {
    id: "p1",
    slug: "horizon",
    name: "Project Horizon",
    description: "Survival adventure",
    project_type: "Open World Survival",
    engine: "Unity",
    status: "prototype",
    visibility: "workspace",
    accent_color: "cyan",
    cover_image_url: null,
    properties: {},
    archived_at: null,
    created_at: "2026-11-01T09:00:00Z",
    updated_at: "2026-11-01T09:00:00Z",
    version: 1,
    progress: { total: 4, done: 1, percent: 25 },
    capabilities: ["workspace.read", "tasks.create", "tasks.edit_any", "comments.write", "documents.write"],
    ...overrides,
  };
}

export function taskFixture(overrides: Partial<Task> = {}): Task {
  return {
    id: "t1",
    title: "Build FPS controller",
    description: "",
    status: "todo",
    priority: "high",
    project_id: "p1",
    department_id: null,
    workstream_id: null,
    milestone_id: null,
    parent_task_id: null,
    assignee_user_id: USER_ID,
    created_by_user_id: USER_ID,
    start_date: null,
    due_date: null,
    completed_at: null,
    position: 1,
    archived_at: null,
    created_at: "2026-11-10T09:00:00Z",
    updated_at: "2026-11-10T09:00:00Z",
    version: 3,
    can_edit: true,
    ...overrides,
  };
}

/** The reference data every signed-in screen loads. */
export function studioRoutes(extra: Record<string, Route> = {}): Record<string, Route> {
  return {
    "GET /auth/me": meFixture(),
    "GET /w/booski/projects": { items: [projectFixture()], next_cursor: null },
    "GET /w/booski/departments": [],
    "GET /w/booski/members": [
      { user_id: USER_ID, email: "olivia@booski.test", display_name: "Olivia Owner", role: "owner", joined_at: "2026-11-01T09:00:00Z" },
    ],
    "GET /w/booski/approvals": { items: [], next_cursor: null },
    ...extra,
  };
}
