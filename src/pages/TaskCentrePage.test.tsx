import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { meFixture, mockApi, reply, studioRoutes, taskFixture } from "../test/api";
import { renderSignedIn } from "../test/render";
import { TaskCentrePage } from "./TaskCentrePage";
import { TaskFormModal } from "../components/TaskFormModal";
import { useTasks } from "../context/TasksContext";

function WithTaskForm() {
  const { isTaskFormOpen } = useTasks();
  return (
    <>
      <TaskCentrePage />
      {isTaskFormOpen && <TaskFormModal />}
    </>
  );
}

const page = (items = [taskFixture()]) => ({ items, next_cursor: null });

describe("Task Centre", () => {
  it("shows loading, then real tasks with their project and assignee", async () => {
    mockApi(studioRoutes({ "GET /w/booski/tasks": page() }));
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    expect(screen.getByText("Checking your session…")).toBeInTheDocument();
    const row = await screen.findByTestId("task-row");
    expect(row).toHaveTextContent("Build FPS controller");
    expect(row).toHaveTextContent("Project Horizon");
    expect(row).toHaveTextContent("@Olivia Owner");
  });

  it("passes filters to Booski Core", async () => {
    const { calls } = mockApi(studioRoutes({ "GET /w/booski/tasks": page() }));
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    await screen.findByTestId("task-row");
    await userEvent.selectOptions(screen.getByLabelText("Assignee"), "me");
    await waitFor(() => expect(calls.at(-1)?.query.get("assignee")).toBe("me"));
    const last = calls.filter((c) => c.path === "/w/booski/tasks").at(-1)!;
    expect(last.query.getAll("status")).toEqual(["backlog", "todo", "in_progress", "in_review", "blocked"]);
    expect(last.query.get("parent")).toBe("none");
  });

  it("explains an empty result", async () => {
    mockApi(studioRoutes({ "GET /w/booski/tasks": page([]) }));
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    expect(await screen.findByText("No tasks match")).toBeInTheDocument();
  });

  it("explains a failed load and offers a retry", async () => {
    let fail = true;
    mockApi(studioRoutes({ "GET /w/booski/tasks": () => (fail ? reply(500, { request_id: "r1" }) : { body: page() }) }));
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    expect(await screen.findByText("Couldn't load tasks")).toBeInTheDocument();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByTestId("task-row")).toBeInTheDocument();
  });

  it("completes a task optimistically and keeps it when Booski Core agrees", async () => {
    const { calls } = mockApi(
      studioRoutes({
        "GET /w/booski/tasks": page(),
        "PATCH /w/booski/tasks/t1": (r) => ({ body: taskFixture({ ...(r.body as object), status: "done", version: 4 }) }),
      }),
    );
    document.cookie = "__Host-booski_csrf=session-csrf; path=/; secure";
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    await userEvent.click(await screen.findByRole("button", { name: /Mark “Build FPS controller” as done/ }));
    const patch = calls.find((c) => c.method === "PATCH")!;
    expect(patch.body).toEqual({ status: "done", version: 3 }); // sends the version it saw
    expect(patch.headers.get("X-CSRF-Token")).toBe("session-csrf");
    expect(await screen.findByText(/Done/)).toBeInTheDocument();
  });

  it("puts the task back and explains when someone else changed it first (409)", async () => {
    mockApi(
      studioRoutes({
        "GET /w/booski/tasks": page(),
        "PATCH /w/booski/tasks/t1": reply(409, { detail: "This task was changed by someone else.", current_version: 5 }),
      }),
    );
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    const toggle = await screen.findByRole("button", { name: /Mark “Build FPS controller” as done/ });
    await userEvent.click(toggle);
    expect(await screen.findByText(/was changed by someone else, so nothing was saved/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mark “Build FPS controller” as done/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("disables completing tasks you can't edit, and hides New task for viewers", async () => {
    mockApi({
      ...studioRoutes({ "GET /w/booski/tasks": page([taskFixture({ can_edit: false })]) }),
      "GET /auth/me": meFixture({ workspaces: [{ workspace_id: "w1", workspace_slug: "booski", workspace_name: "Booski Studios", role: "viewer" }] }),
    });
    renderSignedIn(<TaskCentrePage />, { route: "/tasks" });
    expect(await screen.findByRole("button", { name: /Mark “Build FPS controller” as done/ })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "New task" })).not.toBeInTheDocument();
  });

  it("creates a task through the form and shows validation from the server", async () => {
    const { calls } = mockApi(
      studioRoutes({
        "GET /w/booski/tasks": page([]),
        "POST /w/booski/tasks": reply(422, { detail: "The due date can't be before the start date." }),
      }),
    );
    renderSignedIn(<WithTaskForm />, { route: "/tasks" });
    await userEvent.click(await screen.findByRole("button", { name: "New task" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Create task" }));
    expect(within(dialog).getByText("Give the task a title.")).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText("Title"), "Tune sprint");
    await userEvent.click(within(dialog).getByRole("button", { name: "Create task" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("The due date can't be before the start date.");
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ title: "Tune sprint", priority: "medium", status: "todo", project_id: null });
  });
});
