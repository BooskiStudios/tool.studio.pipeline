import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { AuthProvider } from "../auth/AuthProvider";
import { RequireAuth } from "../auth/RequireAuth";
import { ProjectProvider } from "../context/ProjectContext";
import { TasksProvider } from "../context/TasksContext";
import { ToastProvider } from "../context/ToastContext";
import { WorkspaceProvider } from "../workspace/WorkspaceProvider";

export function testQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } } });
}

/**
 * Renders `ui` at `route` inside the same providers the app uses for signed-in pages, with a fresh
 * cache. `path` is the route pattern (e.g. "/projects/:projectSlug").
 */
export function renderSignedIn(ui: ReactElement, { route = "/", path = "*", queryClient = testQueryClient() } = {}) {
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <ToastProvider>
            <Routes>
              <Route path="/login" element={<p>Sign-in page</p>} />
              <Route
                path={path}
                element={
                  <RequireAuth>
                    <WorkspaceProvider>
                      <ProjectProvider>
                        <TasksProvider>{ui}</TasksProvider>
                      </ProjectProvider>
                    </WorkspaceProvider>
                  </RequireAuth>
                }
              />
            </Routes>
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, queryClient };
}
