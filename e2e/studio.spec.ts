/**
 * Real user journeys through the React app, against the real Booski Core API and PostgreSQL.
 * The journeys run in order and build on each other (one shared, disposable database).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { API, apiWrite, openTaskCentre, PASSWORD, signIn, WORKSPACE } from "./helpers";

test.describe.configure({ mode: "serial" });

const OWNER = "owner@e2e.test";
const RIVAL = "rival@e2e.test";
const DEVELOPER = "dev@e2e.test";
const VIEWER = "viewer@e2e.test";
const NEW_PASSWORD = "a-strong-e2e-password";

let owner: Page;
let developer: Page;
let viewer: Page;

const dialog = (page: Page) => page.getByRole("dialog");

async function newPage(browser: Browser): Promise<Page> {
  return (await browser.newContext()).newPage();
}

async function inviteAndJoin(browser: Browser, email: string, role: string, name: string): Promise<Page> {
  await owner.goto("/settings");
  await owner.getByLabel("Email to invite").fill(email);
  await owner.getByLabel("Role for the invitation").selectOption({ label: role });
  await owner.getByRole("button", { name: "Invite" }).click();
  const token = (await owner.getByTestId("invitation-token").textContent()) ?? "";
  expect(token.length).toBeGreaterThan(20);

  const page = await newPage(browser);
  await page.goto("/join");
  await page.getByLabel("Invitation code").fill(token);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText(`invited ${email}`)).toBeVisible();
  await page.getByLabel("Your name").fill(name);
  await page.getByLabel("Password", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Repeat password").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Join workspace" }).click();
  await expect(page.getByRole("heading", { name: "Studio Command Centre" })).toBeVisible();
  return page;
}

test("signed-out visitors are sent to sign in, and the API refuses them", async ({ page }) => {
  await page.goto("/tasks");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const response = await page.request.get(`${API}/w/${WORKSPACE}/projects`);
  expect(response.status()).toBe(401);
  // Deep links survive sign-in: back to /tasks afterwards.
  await page.getByLabel("Email").fill(OWNER);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
});

test("the owner signs in (a wrong password is explained) and sees live data", async ({ browser }) => {
  owner = await newPage(browser);
  await owner.goto("/login");
  await owner.getByLabel("Email").fill(OWNER);
  await owner.getByLabel("Password", { exact: true }).fill("not-the-password");
  await owner.getByRole("button", { name: "Sign in" }).click();
  await expect(owner.getByRole("alert")).toContainText(/email or password/i);
  await signIn(owner, OWNER);
  await expect(owner.getByText("LIVE · BOOSKI CORE").first()).toBeVisible();
  await expect(owner.locator("footer")).toContainText("BOOSKI E2E STUDIO");
  // Seeded departments come from the backend.
  await expect(owner.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Quality & Oversight" })).toBeVisible();
  // No sessions in browser storage.
  const stored = await owner.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }));
  expect(stored).not.toMatch(/booski_session|csrf/i);
});

test("the owner creates a project and a restricted project", async () => {
  await owner.getByRole("button", { name: "New project" }).click();
  await dialog(owner).getByLabel("Name", { exact: true }).fill("Project Horizon");
  await dialog(owner).getByLabel("Type", { exact: true }).fill("Open World Survival");
  await dialog(owner).getByLabel("Engine").fill("Unity");
  await dialog(owner).getByRole("button", { name: "Create project" }).click();
  await expect(owner).toHaveURL(/\/projects\/project-horizon$/);
  await expect(owner.getByRole("heading", { name: "Project Horizon" })).toBeVisible();

  await owner.getByRole("button", { name: "New project" }).click();
  await dialog(owner).getByLabel("Name", { exact: true }).fill("Secret Lab");
  await dialog(owner).getByLabel("Visibility").selectOption("restricted");
  await dialog(owner).getByRole("button", { name: "Create project" }).click();
  await expect(owner.getByRole("heading", { name: "Secret Lab" })).toBeVisible();
  await expect(owner.getByText("RESTRICTED", { exact: true })).toBeVisible();
});

test("the owner invites a developer and a viewer, who join with new accounts", async ({ browser }) => {
  developer = await inviteAndJoin(browser, DEVELOPER, "Developer", "Dana Developer");
  viewer = await inviteAndJoin(browser, VIEWER, "Viewer", "Vic Viewer");
  await owner.reload();
  await expect(owner.getByText("Dana Developer")).toBeVisible();
});

test("the owner creates a task and assigns it to the developer", async () => {
  await openTaskCentre(owner);
  await owner.getByRole("button", { name: "New task" }).click();
  await dialog(owner).getByLabel("Title").fill("Build FPS controller");
  await dialog(owner).getByLabel("Project").selectOption({ label: "Project Horizon" });
  await dialog(owner).getByLabel("Assignee").selectOption({ label: "Dana Developer" });
  await dialog(owner).getByLabel("Priority").selectOption("high");
  await dialog(owner).getByRole("button", { name: "Create task" }).click();
  await expect(owner.getByTestId("task-row").filter({ hasText: "Build FPS controller" })).toContainText("@Dana Developer");

  await owner.getByRole("button", { name: "New task" }).click();
  await dialog(owner).getByLabel("Title").fill("Prototype the secret mechanic");
  await dialog(owner).getByLabel("Project").selectOption({ label: "Secret Lab" });
  await dialog(owner).getByRole("button", { name: "Create task" }).click();
  await expect(owner.getByTestId("task-row").filter({ hasText: "secret mechanic" })).toBeVisible();
});

test("the developer updates their assigned task and the change persists", async () => {
  await openTaskCentre(developer);
  await developer.getByLabel("Assignee").selectOption("me");
  const row = developer.getByTestId("task-row").filter({ hasText: "Build FPS controller" });
  await row.getByRole("button", { name: /^Build FPS controller/ }).click();
  await dialog(developer).getByRole("button", { name: "Edit task" }).click();
  await dialog(developer).getByLabel("Status").selectOption("in_progress");
  await dialog(developer).getByLabel("Due date").fill("2026-12-01");
  await dialog(developer).getByRole("button", { name: "Save changes" }).click();
  await expect(developer.getByRole("dialog")).toContainText("In progress");
  await dialog(developer).getByRole("button", { name: "Comments" }).click();
  await dialog(developer).getByLabel("New comment").fill("Movement feels good now.");
  await dialog(developer).getByRole("button", { name: "Comment", exact: true }).click();
  await expect(developer.getByRole("dialog")).toContainText("Movement feels good now.");
  await dialog(developer).getByRole("button", { name: "History" }).click();
  await expect(developer.getByRole("dialog")).toContainText("Dana Developer");
  await developer.keyboard.press("Escape");

  await developer.getByLabel("Status").selectOption("all");
  await row.getByRole("button", { name: /Mark “Build FPS controller” as done/ }).click();
  await expect(row.getByText("Done", { exact: true })).toBeVisible();
  await developer.reload();
  await developer.getByLabel("Status").selectOption("all");
  await expect(developer.getByTestId("task-row").filter({ hasText: "Build FPS controller" }).getByText("Done", { exact: true })).toBeVisible();
});

test("the viewer can read but not change anything, and never sees the restricted project", async () => {
  await openTaskCentre(viewer);
  await expect(viewer.getByRole("button", { name: "New task" })).toHaveCount(0);
  const row = viewer.getByTestId("task-row").filter({ hasText: "Build FPS controller" });
  await viewer.getByLabel("Status").selectOption("all");
  await expect(row).toBeVisible();
  await expect(row.getByRole("button", { name: /Mark “Build FPS controller”/ })).toBeDisabled();
  await expect(viewer.getByText("secret mechanic")).toHaveCount(0);
  await expect(viewer.getByRole("navigation", { name: "Projects" })).not.toContainText("Secret Lab");

  await viewer.goto("/projects/secret-lab");
  await expect(viewer.getByRole("heading", { name: "Page not found" })).toBeVisible();

  // The server enforces it too, whatever the UI shows.
  const tasks = await viewer.request.get(`${API}/w/${WORKSPACE}/tasks?q=FPS`);
  const task = (await tasks.json()).items[0];
  const patch = await apiWrite(viewer, "PATCH", `/w/${WORKSPACE}/tasks/${task.id}`, { title: "Hijacked" });
  expect(patch.status()).toBe(403);
});

test("the developer writes a document, edits it, and its revision history stays intact", async () => {
  await developer.goto("/knowledge");
  await developer.getByRole("button", { name: "New document" }).click();
  await dialog(developer).getByLabel("Title").fill("Movement design");
  await dialog(developer).getByLabel("Type").selectOption("design_doc");
  await dialog(developer).getByLabel("Project").selectOption({ label: "Project Horizon" });
  await dialog(developer).getByLabel("Content (Markdown)").fill("# Movement\n\nSprint speed is **6 m/s**.");
  await developer.getByRole("button", { name: "Create document" }).click();
  const viewerDialog = dialog(developer);
  await expect(viewerDialog.getByRole("heading", { name: "Movement", exact: true })).toBeVisible();
  await expect(viewerDialog.locator("strong")).toHaveText("6 m/s");

  await viewerDialog.getByRole("button", { name: "Edit" }).click();
  await developer.getByLabel("Content (Markdown)").fill("# Movement\n\nSprint speed is **7 m/s** after playtesting.");
  await developer.getByLabel("What changed?").fill("Faster sprint");
  await developer.getByRole("button", { name: "Save new revision" }).click();
  await expect(developer.getByText("Saved revision 2")).toBeVisible();

  // Saving returns to the document, now showing the new text.
  await expect(viewerDialog.locator("strong")).toHaveText("7 m/s");
  await viewerDialog.getByRole("button", { name: "Revision history" }).click();
  await expect(developer.getByRole("dialog").getByText("Revision 2 (current)")).toBeVisible();
  await developer.getByRole("button", { name: /Revision 1/ }).click();
  await expect(developer.getByRole("dialog").locator(".revision-body strong")).toHaveText("6 m/s");
  await developer.keyboard.press("Escape");
});

test("decisions are recorded in the Decision Log", async () => {
  await developer.goto("/decisions");
  await developer.getByRole("button", { name: "Record decision" }).click();
  await dialog(developer).getByLabel("Decision", { exact: true }).fill("Use Unity for Horizon");
  await dialog(developer).getByLabel("Option 1", { exact: true }).fill("Unity");
  await dialog(developer).getByLabel("Option 2", { exact: true }).fill("Unreal");
  await dialog(developer).getByLabel("Outcome").fill("Unity");
  await dialog(developer).getByLabel("Status").selectOption("accepted");
  await dialog(developer).getByRole("button", { name: "Record decision" }).click();
  await expect(developer.getByTestId("decision-row").filter({ hasText: "Use Unity for Horizon" })).toContainText("Accepted");
  await expect(viewer.request.get(`${API}/w/${WORKSPACE}/decisions`).then((r) => r.json())).resolves.toMatchObject({
    items: [expect.objectContaining({ title: "Use Unity for Horizon" })],
  });
});

test("an approval request is resolved by an authorised reviewer, never by its requester", async () => {
  await developer.goto("/approvals");
  await developer.getByRole("button", { name: "Request approval" }).click();
  await dialog(developer).getByLabel("What needs approving?").fill("Merge the FPS controller");
  await dialog(developer).getByLabel("Type").selectOption("code_change");
  await dialog(developer).getByLabel("Reviewer").selectOption({ label: "Olivia Owner" });
  await dialog(developer).getByRole("button", { name: "Request approval" }).click();
  await developer.getByRole("button", { name: "Submitted by you" }).click();
  const mine = developer.getByTestId("approval-row").filter({ hasText: "Merge the FPS controller" });
  await expect(mine).toContainText("Waiting for review");
  await mine.getByRole("button", { name: "Open" }).click();
  await expect(developer.getByRole("button", { name: "Approve" })).toHaveCount(0);
  await expect(developer.getByText("You can't decide your own request")).toBeVisible();
  await developer.keyboard.press("Escape");

  await owner.goto("/approvals");
  const waiting = owner.getByTestId("approval-row").filter({ hasText: "Merge the FPS controller" });
  await waiting.getByRole("button", { name: "Review" }).click();
  await dialog(owner).getByRole("button", { name: "Reject" }).click();
  await expect(dialog(owner).getByRole("alert")).toContainText("Add a comment");
  await dialog(owner).getByLabel("Comment", { exact: true }).fill("Looks good, ship it.");
  await dialog(owner).getByRole("button", { name: "Approve" }).click();
  await expect(owner.getByRole("dialog")).toContainText("Approved");
  await expect(owner.getByRole("dialog")).toContainText("Looks good, ship it.");
  await expect(owner.getByRole("dialog")).toContainText("Nothing is executed or published automatically");
});

test("activity history reflects what happened, and restricted work stays private", async () => {
  await owner.goto("/activity");
  const feed = owner.getByTestId("activity-row");
  await expect(feed.filter({ hasText: "Build FPS controller" }).first()).toBeVisible();
  await expect(feed.filter({ hasText: "Movement design" }).first()).toBeVisible();
  await expect(feed.filter({ hasText: "Merge the FPS controller" }).first()).toBeVisible();
  await expect(owner.locator("main")).toContainText("Secret Lab");

  await developer.goto("/activity");
  await expect(developer.getByTestId("activity-row").first()).toBeVisible();
  await expect(developer.locator("main")).not.toContainText("Secret Lab");
  await expect(developer.locator("main")).not.toContainText("secret mechanic");
});

test("switching workspace never shows the previous workspace's data", async () => {
  const created = await apiWrite(owner, "POST", "/workspaces", { name: "Side Studio", slug: "side-studio" });
  expect(created.status()).toBe(201);
  await owner.goto("/tasks");
  await expect(owner.getByTestId("task-row").first()).toBeVisible();
  await owner.getByRole("button", { name: /Open account menu/ }).click();
  await owner.getByRole("menuitemradio", { name: /Side Studio/ }).click();
  await expect(owner.locator("footer")).toContainText("SIDE STUDIO");
  await expect(owner.getByRole("navigation", { name: "Projects" })).toContainText("No projects yet");
  await owner.goto("/tasks");
  await expect(owner.getByText("No tasks match")).toBeVisible();
  await expect(owner.getByText("Build FPS controller")).toHaveCount(0);

  await owner.getByRole("button", { name: /Open account menu/ }).click();
  await owner.getByRole("menuitemradio", { name: /Booski E2E Studio/ }).click();
  await expect(owner.getByRole("navigation", { name: "Projects" })).toContainText("Project Horizon");
});

test("another workspace's owner can't reach this workspace at all", async ({ browser }) => {
  const rival = await newPage(browser);
  await signIn(rival, RIVAL);
  await expect(rival.getByRole("navigation", { name: "Projects" })).not.toContainText("Project Horizon");
  for (const path of ["projects", "tasks", "documents", "activity"]) {
    expect((await rival.request.get(`${API}/w/${WORKSPACE}/${path}`)).status()).toBe(404);
  }
  await rival.context().close();
});

test("signing out ends the session on the server", async ({ browser }) => {
  const cookies = await owner.context().cookies();
  await owner.getByRole("button", { name: /Open account menu/ }).click();
  await owner.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(owner).toHaveURL(/\/login$/);
  await expect(owner.getByText("You've signed out.")).toBeVisible();
  expect((await owner.request.get(`${API}/auth/me`)).status()).toBe(401);
  await owner.goto("/tasks");
  await expect(owner).toHaveURL(/\/login$/);

  // Replaying the old session cookie in a fresh browser gets nowhere.
  const replay = await browser.newContext();
  await replay.addCookies(cookies);
  expect((await replay.request.get(`http://localhost:${process.env.BOOSKI_E2E_WEB_PORT ?? "5174"}${API}/auth/me`)).status()).toBe(401);
  await replay.close();
});
