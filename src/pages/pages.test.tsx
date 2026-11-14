/** Projects, documents, decisions, approvals and activity screens against a fake Booski Core. */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type { ActivityEvent, Approval, Decision, StudioDocument } from "../api/types";
import { meFixture, mockApi, projectFixture, reply, studioRoutes, USER_ID } from "../test/api";
import { renderSignedIn } from "../test/render";
import { ActivityAuditPage } from "./ActivityAuditPage";
import { ApprovalsCentrePage } from "./ApprovalsCentrePage";
import { DecisionLogPage } from "./DecisionLogPage";
import { ProjectWorkspacePage } from "./ProjectWorkspacePage";
import { StudioKnowledgePage } from "./StudioKnowledgePage";

const OTHER = "00000000-0000-7000-8000-000000000002";
const members = [
  { user_id: USER_ID, email: "olivia@booski.test", display_name: "Olivia Owner", role: "owner", joined_at: "2026-11-01T09:00:00Z" },
  { user_id: OTHER, email: "dana@booski.test", display_name: "Dana Developer", role: "developer", joined_at: "2026-11-01T09:00:00Z" },
];

function asRole(role: "owner" | "developer" | "viewer") {
  return meFixture({ workspaces: [{ workspace_id: "w1", workspace_slug: "booski", workspace_name: "Booski Studios", role }] });
}

const projectRoutes = (
  <Routes>
    <Route path="/projects/:projectSlug" element={<ProjectWorkspacePage />} />
  </Routes>
);

describe("Project workspace", () => {
  it("shows the project's live status and progress", async () => {
    mockApi(studioRoutes({ "GET /w/booski/projects/horizon": projectFixture(), "GET /w/booski/projects/horizon/workstreams": [] }));
    renderSignedIn(projectRoutes, { route: "/projects/horizon" });
    expect(await screen.findByRole("heading", { name: "Project Horizon" })).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("Prototype")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit project/ })).toBeInTheDocument(); // owner
  });

  it("treats a restricted project you aren't on exactly like a missing one", async () => {
    mockApi(studioRoutes({ "GET /w/booski/projects/secret": reply(404) }));
    renderSignedIn(projectRoutes, { route: "/projects/secret" });
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("shows read-only access and hides management for a project viewer", async () => {
    mockApi({
      ...studioRoutes({
        "GET /w/booski/projects/horizon": projectFixture({ capabilities: ["workspace.read", "members.read", "activity.read"] }),
        "GET /w/booski/projects/horizon/workstreams": [],
      }),
      "GET /auth/me": asRole("developer"),
    });
    renderSignedIn(projectRoutes, { route: "/projects/horizon" });
    expect(await screen.findByText("Read-only")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Edit project/ })).not.toBeInTheDocument();
  });
});

const doc: StudioDocument = {
  id: "d1", kind: "design_doc", title: "Movement design", summary: "", tags: ["movement"], project_id: "p1", department_id: null,
  current_revision: 2, created_by_user_id: USER_ID, updated_by_user_id: OTHER, archived_at: null,
  created_at: "2026-11-10T09:00:00Z", updated_at: "2026-11-12T09:00:00Z", version: 2, can_edit: true,
  body: "# Movement\n\nSprint is **7 m/s**.\n\n<script>alert(1)</script> [bad](javascript:alert(1))",
};

describe("Knowledge base", () => {
  it("lists documents, renders Markdown safely and shows the revision history", async () => {
    mockApi({
      ...studioRoutes({
        "GET /w/booski/documents": { items: [doc], next_cursor: null },
        "GET /w/booski/documents/d1": doc,
        "GET /w/booski/documents/d1/revisions": [
          { revision_no: 1, title: "Movement design", change_note: "", created_by_user_id: USER_ID, created_at: "2026-11-10T09:00:00Z" },
          { revision_no: 2, title: "Movement design", change_note: "Faster sprint", created_by_user_id: OTHER, created_at: "2026-11-12T09:00:00Z" },
        ],
        "GET /w/booski/documents/d1/revisions/1": { revision_no: 1, title: "Movement design", change_note: "", created_by_user_id: USER_ID, created_at: "2026-11-10T09:00:00Z", body: "Sprint is **6 m/s**." },
      }),
      "GET /w/booski/members": members,
    });
    renderSignedIn(<StudioKnowledgePage />, { route: "/knowledge" });
    const row = await screen.findByTestId("document-row");
    expect(row).toHaveTextContent("Design document · revision 2");
    await userEvent.click(within(row).getByRole("button", { name: "Open Movement design" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("7 m/s")).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Created by Olivia Owner · Last edited by Dana Developer");
    // No markup from the document runs or becomes a link.
    expect(dialog.querySelector("script")).toBeNull();
    expect(dialog).toHaveTextContent("<script>alert(1)</script>");
    expect(within(dialog).queryByRole("link", { name: "bad" })).not.toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "Revision history" }));
    expect(await within(dialog).findByText("Revision 2 (current)")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: /Revision 1/ }));
    expect(await within(dialog).findByText("6 m/s")).toBeInTheDocument();
  });

  it("only offers New document to roles that may write", async () => {
    mockApi({ ...studioRoutes({ "GET /w/booski/documents": { items: [], next_cursor: null } }), "GET /auth/me": asRole("viewer") });
    renderSignedIn(<StudioKnowledgePage />, { route: "/knowledge" });
    expect(await screen.findByText("No documents match")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New document" })).not.toBeInTheDocument();
  });
});

const decision: Decision = {
  id: "dec1", title: "Use Unity", context: "Engine choice", options: [{ title: "Unity" }, { title: "Unreal" }], outcome: "Unity",
  rationale: "Team knows it", status: "accepted", project_id: null, department_id: null, author_user_id: USER_ID,
  recorded_at: "2026-11-10T09:00:00Z", decided_at: "2026-11-10T09:00:00Z", supersedes_decision_id: null,
  superseded_by_decision_id: null, document_ids: [], updated_at: "2026-11-10T09:00:00Z", version: 1,
};

describe("Decision Log", () => {
  it("lists decisions and opens their details and history", async () => {
    mockApi({
      ...studioRoutes({
        "GET /w/booski/decisions": { items: [decision], next_cursor: null },
        "GET /w/booski/decisions/dec1": decision,
        "GET /w/booski/decisions/dec1/history": { items: [], next_cursor: null },
      }),
    });
    renderSignedIn(<DecisionLogPage />, { route: "/decisions" });
    const row = await screen.findByTestId("decision-row");
    expect(row).toHaveTextContent("Use Unity");
    expect(row).toHaveTextContent("Accepted");
    await userEvent.click(row);
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("Team knows it")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Supersede/ })).toBeInTheDocument();
  });
});

const approval = (overrides: Partial<Approval>): Approval => ({
  id: "a1", kind: "code_change", title: "Merge controller", description: "", payload: {}, project_id: null, subject_type: null,
  subject_id: null, status: "pending", requested_by_user_id: OTHER, reviewer_user_id: USER_ID, resolved_by_user_id: null,
  resolution_comment: "", resolved_at: null, due_at: null, created_at: "2026-11-12T09:00:00Z", updated_at: "2026-11-12T09:00:00Z",
  version: 1, can_decide: true, ...overrides,
});

describe("Approvals Centre", () => {
  it("requires a comment to reject, then records the decision", async () => {
    const { calls } = mockApi({
      ...studioRoutes({
        "GET /w/booski/approvals": { items: [approval({})], next_cursor: null },
        "GET /w/booski/approvals/a1": approval({}),
        "GET /w/booski/approvals/a1/reviews": [],
        "POST /w/booski/approvals/a1/reviews": approval({ status: "rejected", can_decide: false }),
      }),
      "GET /w/booski/members": members,
    });
    renderSignedIn(<ApprovalsCentrePage />, { route: "/approvals" });
    const row = await screen.findByTestId("approval-row");
    await userEvent.click(within(row).getByRole("button", { name: "Review" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(await within(dialog).findByRole("button", { name: "Reject" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Add a comment");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.type(within(dialog).getByLabelText("Comment"), "Needs tests");
    await userEvent.click(within(dialog).getByRole("button", { name: "Reject" }));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ action: "reject", comment: "Needs tests" });
    expect(dialog).toHaveTextContent("Nothing is executed or published automatically");
  });

  it("never offers to approve your own request", async () => {
    const mine = approval({ requested_by_user_id: USER_ID, reviewer_user_id: OTHER, can_decide: false });
    mockApi({
      ...studioRoutes({
        "GET /w/booski/approvals": { items: [mine], next_cursor: null },
        "GET /w/booski/approvals/a1": mine,
        "GET /w/booski/approvals/a1/reviews": [],
      }),
      "GET /w/booski/members": members,
    });
    renderSignedIn(<ApprovalsCentrePage />, { route: "/approvals?approval=a1" });
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/You can't decide your own request/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Cancel request/ })).toBeInTheDocument();
  });
});

const event = (overrides: Partial<ActivityEvent>): ActivityEvent => ({
  id: "e1", created_at: new Date().toISOString(), verb: "task.created", entity_type: "task", entity_id: "t1", project_id: "p1",
  actor_type: "user", actor_user_id: OTHER, summary: "Created task Build FPS controller", changes: {}, request_id: "r1", ...overrides,
});

describe("Activity & Audit", () => {
  it("shows who did what, links to the record, and paginates", async () => {
    const { calls } = mockApi({
      ...studioRoutes({
        "GET /w/booski/activity": (r) =>
          r.query.get("cursor")
            ? { body: { items: [event({ id: "e2", summary: "Older event", project_id: null })], next_cursor: null } }
            : { body: { items: [event({})], next_cursor: "page-2" } },
      }),
      "GET /w/booski/members": members,
    });
    renderSignedIn(<ActivityAuditPage />, { route: "/activity" });
    const row = await screen.findByTestId("activity-row");
    expect(row).toHaveTextContent("Dana Developer · Task · Project Horizon");
    expect(within(row).getByRole("link")).toHaveAttribute("href", "/tasks?task=t1");
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Older event")).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/w/booski/activity").at(-1)?.query.get("cursor")).toBe("page-2");
  });

  it("never names a project you can't see", async () => {
    mockApi({
      ...studioRoutes({ "GET /w/booski/activity": { items: [event({ project_id: "hidden-project" })], next_cursor: null } }),
      "GET /w/booski/members": members,
    });
    renderSignedIn(<ActivityAuditPage />, { route: "/activity" });
    const row = await screen.findByTestId("activity-row");
    expect(row).toHaveTextContent("Dana Developer · Task");
    expect(row).not.toHaveTextContent("hidden-project");
  });
});
