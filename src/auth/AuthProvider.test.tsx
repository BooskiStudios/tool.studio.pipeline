import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import { apiRequest } from "../api/client";
import { LoginPage } from "../pages/LoginPage";
import { meFixture, mockApi, reply } from "../test/api";
import { testQueryClient } from "../test/render";
import { AuthProvider, useAuth } from "./AuthProvider";
import { RequireAuth } from "./RequireAuth";

function Where() {
  const location = useLocation();
  return <p>at {location.pathname}</p>;
}

function SignOutButton() {
  const { logout } = useAuth();
  return <button type="button" onClick={() => void logout()}>Sign out</button>;
}

function renderApp(route: string) {
  return render(
    <QueryClientProvider client={testQueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<RequireAuth><Where /><SignOutButton /></RequireAuth>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("authentication", () => {
  it("restores an existing session from /auth/me on start-up", async () => {
    mockApi({ "GET /auth/me": meFixture() });
    renderApp("/tasks");
    expect(screen.getByText("Checking your session…")).toBeInTheDocument();
    expect(await screen.findByText("at /tasks")).toBeInTheDocument();
  });

  it("sends signed-out visitors to sign in, then back to where they were going", async () => {
    let signedIn = false;
    const { calls } = mockApi({
      "GET /auth/me": () => (signedIn ? { body: meFixture() } : reply(401)),
      "POST /auth/login": () => {
        signedIn = true;
        return { body: { ...meFixture(), csrf_token: "fresh-token" } };
      },
      "POST /auth/logout": reply(204),
    });
    renderApp("/tasks?view=mine");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Email"), "olivia@booski.test");
    await userEvent.type(screen.getByLabelText("Password"), "correct horse battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("at /tasks")).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/auth/login")?.body).toEqual({ email: "olivia@booski.test", password: "correct horse battery" });

    // The CSRF token from sign-in is used for the next state-changing request.
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(calls.find((c) => c.path === "/auth/logout")?.headers.get("X-CSRF-Token")).toBe("fresh-token");
    expect(await screen.findByText("You've signed out.")).toBeInTheDocument();
  });

  it("validates the form before calling the server, and explains a failed sign-in", async () => {
    const { calls } = mockApi({
      "GET /auth/me": reply(401),
      "POST /auth/login": reply(401, { detail: "Email or password is incorrect." }),
    });
    renderApp("/login");
    await screen.findByRole("heading", { name: "Sign in" });
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText("Enter the email address you were invited with.")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/auth/login")).toBe(false);

    await userEvent.type(screen.getByLabelText("Email"), "olivia@booski.test");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("returns to sign-in with an explanation when the session ends while the app is open", async () => {
    mockApi({ "GET /auth/me": meFixture(), "GET /w/booski/tasks": reply(401, { detail: "Sign in to continue." }) });
    renderApp("/tasks");
    await screen.findByText("at /tasks");
    await act(async () => {
      await apiRequest("/w/booski/tasks").catch(() => undefined);
    });
    expect(await screen.findByText("Your session has ended. Please sign in again to continue.")).toBeInTheDocument();
  });

  it("explains when Booski Core can't be reached", async () => {
    mockApi({ "GET /auth/me": reply(503, {}) });
    renderApp("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong in Booski Core");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("never stores session data in browser storage", async () => {
    mockApi({ "GET /auth/me": meFixture() });
    renderApp("/");
    await waitFor(() => expect(screen.getByText("at /")).toBeInTheDocument());
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toMatch(/session|csrf|token/i);
  });
});
