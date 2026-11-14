import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useProjectList } from "../api/hooks";
import { meFixture, mockApi, projectFixture } from "../test/api";
import { renderSignedIn } from "../test/render";
import { useWorkspace } from "./WorkspaceProvider";

const twoWorkspaces = meFixture({
  workspaces: [
    { workspace_id: "w1", workspace_slug: "booski", workspace_name: "Booski Studios", role: "owner" },
    { workspace_id: "w2", workspace_slug: "side", workspace_name: "Side Studio", role: "viewer" },
  ],
});

function Probe() {
  const { name, role, can, switchWorkspace } = useWorkspace();
  const projects = useProjectList();
  return (
    <div>
      <p>workspace: {name} ({role})</p>
      <p>can manage projects: {String(can("projects.manage"))}</p>
      <ul>{projects.data?.map((p) => <li key={p.id}>{p.name}</li>)}</ul>
      <button type="button" onClick={() => switchWorkspace("side")}>switch</button>
    </div>
  );
}

describe("workspaces", () => {
  it("scopes data to the active workspace and drops it on a switch", async () => {
    const { calls } = mockApi({
      "GET /auth/me": twoWorkspaces,
      "GET /w/booski/projects": { items: [projectFixture({ name: "Booski Secret Game" })], next_cursor: null },
      "GET /w/side/projects": { items: [], next_cursor: null },
    });
    const { queryClient } = renderSignedIn(<Probe />);
    expect(await screen.findByText("Booski Secret Game")).toBeInTheDocument();
    expect(screen.getByText("workspace: Booski Studios (owner)")).toBeInTheDocument();
    expect(screen.getByText("can manage projects: true")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "switch" }));
    expect(await screen.findByText("workspace: Side Studio (viewer)")).toBeInTheDocument();
    expect(screen.getByText("can manage projects: false")).toBeInTheDocument();
    expect(screen.queryByText("Booski Secret Game")).not.toBeInTheDocument();
    await waitFor(() => expect(calls.some((c) => c.path === "/w/side/projects")).toBe(true));
    // Nothing from the previous workspace remains cached.
    expect(queryClient.getQueryCache().findAll({ queryKey: ["ws", "booski"] })).toHaveLength(0);
    expect(window.localStorage.getItem("booski.activeWorkspace")).toBe("side");
  });

  it("remembers the chosen workspace, but ignores one you no longer belong to", async () => {
    window.localStorage.setItem("booski.activeWorkspace", "side");
    mockApi({ "GET /auth/me": twoWorkspaces, "GET /w/side/projects": { items: [], next_cursor: null } });
    renderSignedIn(<Probe />);
    expect(await screen.findByText("workspace: Side Studio (viewer)")).toBeInTheDocument();
  });

  it("falls back to the first workspace when the remembered one is gone", async () => {
    window.localStorage.setItem("booski.activeWorkspace", "removed-workspace");
    mockApi({ "GET /auth/me": twoWorkspaces, "GET /w/booski/projects": { items: [], next_cursor: null } });
    renderSignedIn(<Probe />);
    expect(await screen.findByText("workspace: Booski Studios (owner)")).toBeInTheDocument();
  });

  it("offers to create a workspace to someone who belongs to none", async () => {
    mockApi({ "GET /auth/me": meFixture({ workspaces: [] }) });
    renderSignedIn(<Probe />);
    expect(await screen.findByRole("heading", { name: "You're not in a workspace yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create workspace" })).toBeInTheDocument();
  });
});
