import { Route, Routes } from "react-router";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./components/layout/AppShell";
import { ProjectProvider } from "./context/ProjectContext";
import { TasksProvider } from "./context/TasksContext";
import { ToastProvider } from "./context/ToastContext";
import { AcceptInvitationPage } from "./pages/AcceptInvitationPage";
import { ActivityAuditPage } from "./pages/ActivityAuditPage";
import { AgentManagementPage } from "./pages/AgentManagementPage";
import { ApprovalsCentrePage } from "./pages/ApprovalsCentrePage";
import { CostUsagePage } from "./pages/CostUsagePage";
import { DecisionLogPage } from "./pages/DecisionLogPage";
import { DepartmentPage } from "./pages/DepartmentPage";
import { GameLibraryPage } from "./pages/GameLibraryPage";
import { HomePage } from "./pages/HomePage";
import { IntegrationsHubPage } from "./pages/IntegrationsHubPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProjectWorkspacePage } from "./pages/ProjectWorkspacePage";
import { ResearchPage } from "./pages/ResearchPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StudioKnowledgePage } from "./pages/StudioKnowledgePage";
import { StudioOperationsPage } from "./pages/StudioOperationsPage";
import { TaskCentrePage } from "./pages/TaskCentrePage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { paths } from "./routes";
import { WorkspaceProvider } from "./workspace/WorkspaceProvider";

/** The signed-in studio: everything here is scoped to the active workspace. */
function Studio() {
  return (
    <RequireAuth>
      <WorkspaceProvider>
        <ProjectProvider>
          <TasksProvider>
            <AppShell />
          </TasksProvider>
        </ProjectProvider>
      </WorkspaceProvider>
    </RequireAuth>
  );
}

/** App-wide providers and the route table. See `routes.ts` for URL builders. */
export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path={paths.login} element={<LoginPage />} />
        <Route path={paths.join} element={<AcceptInvitationPage />} />
        <Route element={<Studio />}>
          <Route index element={<HomePage />} />
          <Route path="departments/:departmentSlug" element={<DepartmentPage />} />
          <Route path="projects/:projectSlug" element={<ProjectWorkspacePage />} />
          <Route path={paths.operations} element={<StudioOperationsPage />} />
          <Route path={paths.tasks} element={<TaskCentrePage />} />
          <Route path={paths.library} element={<GameLibraryPage />} />
          <Route path={paths.research} element={<ResearchPage />} />
          <Route path={paths.templates} element={<TemplatesPage />} />
          <Route path={paths.agents} element={<AgentManagementPage />} />
          <Route path={paths.costUsage} element={<CostUsagePage />} />
          <Route path={paths.decisions} element={<DecisionLogPage />} />
          <Route path={paths.approvals} element={<ApprovalsCentrePage />} />
          <Route path={paths.integrations} element={<IntegrationsHubPage />} />
          <Route path={paths.knowledge} element={<StudioKnowledgePage />} />
          <Route path={paths.activity} element={<ActivityAuditPage />} />
          <Route path={paths.settings} element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}
