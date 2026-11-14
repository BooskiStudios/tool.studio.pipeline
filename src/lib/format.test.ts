import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../components/MarkdownView";
import { isOverdue, projectImage, slugify, timeAgo } from "./format";
import { shouldRetry } from "../api/queryClient";
import { ApiError } from "../api/client";
import { returnPath } from "../pages/LoginPage";

describe("format helpers", () => {
  it("makes valid project addresses from names", () => {
    expect(slugify("Project Horizon")).toBe("project-horizon");
    expect(slugify("  Café — Déjà Vu!  ")).toBe("cafe-deja-vu");
    expect(slugify("a".repeat(80) + " b")).toHaveLength(60);
  });

  it("describes times relative to now", () => {
    const now = new Date("2026-11-14T12:00:00Z");
    expect(timeAgo("2026-11-14T11:59:30Z", now)).toBe("just now");
    expect(timeAgo("2026-11-14T11:30:00Z", now)).toBe("30 min ago");
    expect(timeAgo("2026-11-13T12:00:00Z", now)).toBe("1 day ago");
  });

  it("flags overdue open tasks only", () => {
    const today = new Date("2026-11-14T12:00:00Z");
    expect(isOverdue("2026-11-13", "todo", today)).toBe(true);
    expect(isOverdue("2026-11-13", "done", today)).toBe(false);
    expect(isOverdue("2026-11-15", "todo", today)).toBe(false);
  });

  it("uses a local gradient cover when a project has no image", () => {
    expect(projectImage({ cover_image_url: null, accent_color: "pink" })).toMatch(/^data:image\/svg\+xml,/);
    expect(projectImage({ cover_image_url: "https://example.com/a.png", accent_color: "pink" })).toBe("https://example.com/a.png");
  });
});

describe("markdown parsing", () => {
  it("recognises the supported blocks", () => {
    const blocks = parseMarkdown("# Title\n\nText\n\n- a\n- b\n\n1. one\n\n> quote\n\n```\ncode\n```\n\n---");
    expect(blocks.map((b) => b.type)).toEqual(["heading", "paragraph", "list", "list", "quote", "code", "rule"]);
  });
});

describe("retry policy", () => {
  it("retries only transient failures", () => {
    expect(shouldRetry(0, new ApiError(0))).toBe(true);
    expect(shouldRetry(0, new ApiError(503))).toBe(true);
    expect(shouldRetry(0, new ApiError(403))).toBe(false);
    expect(shouldRetry(0, new ApiError(409))).toBe(false);
    expect(shouldRetry(2, new ApiError(503))).toBe(false);
  });
});

describe("returning after sign-in", () => {
  it("only returns to pages inside the app", () => {
    expect(returnPath({ from: { pathname: "/tasks", search: "?task=1" } })).toBe("/tasks?task=1");
    expect(returnPath({ from: { pathname: "//evil.example" } })).toBe("/");
    expect(returnPath({ from: { pathname: "/login" } })).toBe("/");
    expect(returnPath(null)).toBe("/");
  });
});
