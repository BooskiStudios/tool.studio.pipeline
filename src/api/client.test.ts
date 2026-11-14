import { describe, expect, it, vi } from "vitest";
import { mockApi, reply } from "../test/api";
import { ApiError, apiRequest, buildUrl, errorMessage, onUnauthorized, readCsrfCookie, setCsrfToken } from "./client";

describe("buildUrl", () => {
  it("prefixes the API base, repeats list values and drops empty ones", () => {
    expect(buildUrl("/w/booski/tasks", { status: ["todo", "done"], q: "", project: undefined, limit: 50, archived: false })).toBe(
      "/api/v1/w/booski/tasks?status=todo&status=done&limit=50&archived=false",
    );
  });
});

describe("apiRequest", () => {
  it("sends cookies same-origin and no CSRF header on reads", async () => {
    const { calls } = mockApi({ "GET /w/booski/projects": { items: [], next_cursor: null } });
    setCsrfToken("token-from-sign-in");
    await apiRequest("/w/booski/projects");
    expect(calls[0].credentials).toBe("same-origin");
    expect(calls[0].headers.get("X-CSRF-Token")).toBeNull();
  });

  it("adds the CSRF token to every state-changing request", async () => {
    const { calls } = mockApi({ "POST /w/booski/tasks": reply(201, { id: "t1" }), "PATCH /w/booski/tasks/t1": {}, "DELETE /w/booski/comments/c1": reply(204) });
    setCsrfToken("token-from-sign-in");
    await apiRequest("/w/booski/tasks", { method: "POST", body: { title: "x" } });
    await apiRequest("/w/booski/tasks/t1", { method: "PATCH", body: {} });
    await apiRequest("/w/booski/comments/c1", { method: "DELETE" });
    expect(calls.map((c) => c.headers.get("X-CSRF-Token"))).toEqual(["token-from-sign-in", "token-from-sign-in", "token-from-sign-in"]);
    expect(calls[0].headers.get("Content-Type")).toBe("application/json");
    expect(calls[0].body).toEqual({ title: "x" });
  });

  it("prefers the CSRF cookie, which survives a page reload", async () => {
    const { calls } = mockApi({ "POST /auth/logout": reply(204) });
    document.cookie = "__Host-booski_csrf=from-cookie; path=/; secure; samesite=lax";
    await apiRequest("/auth/logout", { method: "POST" });
    expect(calls[0].headers.get("X-CSRF-Token")).toBe("from-cookie");
  });

  it("returns undefined for 204 responses", async () => {
    mockApi({ "DELETE /w/booski/comments/c1": reply(204) });
    await expect(apiRequest("/w/booski/comments/c1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it.each([
    [403, { detail: "Only owners can do that." }, "forbidden", "Only owners can do that."],
    [404, {}, "not_found", "This item doesn't exist, or you no longer have access to it."],
    [409, { detail: "This task was changed by someone else.", current_version: 7 }, "conflict", "This task was changed by someone else."],
    [422, { detail: "The request is invalid.", errors: [{ loc: ["body", "due_date"], msg: "Input should be a valid date" }] }, "validation", "Due date: Input should be a valid date"],
    [429, { detail: "Too many sign-in attempts." }, "rate_limited", "Too many sign-in attempts."],
    [500, { request_id: "abc123" }, "server", "Something went wrong in Booski Core. Please try again. If it keeps happening, quote reference abc123."],
  ] as const)("turns %i into a %s error with a readable message", async (status, body, kind, message) => {
    mockApi({ "GET /thing": reply(status, body) });
    const error = await apiRequest("/thing").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).kind).toBe(kind);
    expect((error as ApiError).message).toBe(message);
    if (status === 409) expect((error as ApiError).currentVersion).toBe(7);
  });

  it("never shows server internals for unexpected failures", async () => {
    mockApi({ "GET /thing": reply(500, { detail: "psycopg.OperationalError at line 12" }) });
    const error = await apiRequest("/thing").catch((e: unknown) => e);
    expect(errorMessage(error)).not.toContain("psycopg");
  });

  it("reports an unreachable server as a network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = await apiRequest("/thing").catch((e: unknown) => e);
    expect((error as ApiError).kind).toBe("network");
  });

  it("lets a deliberate cancellation pass through untouched", async () => {
    mockApi({ "GET /thing": {} });
    const controller = new AbortController();
    controller.abort();
    await expect(apiRequest("/thing", { signal: controller.signal })).rejects.toMatchObject({ name: "AbortError" });
  });

  it("announces an ended session, except where 401 is expected", async () => {
    mockApi({ "GET /thing": reply(401, { detail: "Sign in to continue." }), "GET /auth/me": reply(401) });
    const listener = vi.fn();
    onUnauthorized(listener);
    await apiRequest("/auth/me", { expectUnauthenticated: true }).catch(() => undefined);
    expect(listener).not.toHaveBeenCalled();
    await apiRequest("/thing").catch(() => undefined);
    expect(listener).toHaveBeenCalledOnce();
    onUnauthorized(null);
  });
});

describe("readCsrfCookie", () => {
  it("finds the CSRF cookie among others", () => {
    expect(readCsrfCookie("a=1; __Host-booski_csrf=abc%3D; b=2")).toBe("abc=");
    expect(readCsrfCookie("a=1")).toBeNull();
  });
});
