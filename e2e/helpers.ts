import { expect, type APIResponse, type BrowserContext, type Page } from "@playwright/test";

export const PASSWORD = "e2e-password-not-secret"; // matches e2e/server.py; throwaway database only
export const WORKSPACE = "booski-e2e";
export const API = "/api/v1";

export async function signIn(page: Page, email: string, password = PASSWORD): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Studio Command Centre" })).toBeVisible();
}

/** The CSRF token the browser holds for this context's session (for direct API calls in tests). */
export async function csrf(context: BrowserContext): Promise<string> {
  const cookie = (await context.cookies()).find((c) => c.name === "__Host-booski_csrf");
  return cookie?.value ?? "";
}

/** A state-changing API call made exactly as the app makes it: session cookie plus CSRF header. */
export async function apiWrite(page: Page, method: "POST" | "PATCH" | "DELETE", path: string, data?: unknown): Promise<APIResponse> {
  return page.request.fetch(`${API}${path}`, {
    method,
    data,
    headers: { "X-CSRF-Token": await csrf(page.context()), "Content-Type": "application/json" },
  });
}

export async function openTaskCentre(page: Page): Promise<void> {
  await page.getByRole("navigation", { name: "Primary" }).waitFor();
  await page.goto("/tasks");
  await expect(page.getByRole("heading", { name: "Task Centre" })).toBeVisible();
}
