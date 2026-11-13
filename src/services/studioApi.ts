import type {
  AgentNode, AgentRecord, Approval, AuditEvent, CommandCentreData, Decision, Department,
  DepartmentWorkspace, Integration, KnowledgeDoc, Project, ProjectReference, ResearchDoc,
  Task, Template, UsageReport,
} from "../types";

/**
 * Where the UI's data comes from.
 *
 * - `"demo"`: hardcoded illustrative data bundled with the frontend (current state).
 * - `"live"`: Booski Core (FastAPI). Not implemented yet.
 */
export type DataSourceMode = "demo" | "live";

/**
 * The contract between pages and their data source.
 *
 * Pages and components must read data through this interface (via `studioApi`
 * from `services/index.ts`), never by importing from `src/data` directly. When
 * Booski Core exists, add a `liveStudioApi` that implements this interface with
 * `fetch` calls and switch the export in `services/index.ts`; pages stay as they are.
 *
 * Every method is async so the swap to network calls does not change call sites.
 *
 * This interface is intentionally read-only. Actions that would create or change
 * records (approvals, uploads, new projects, agent configuration…) are not
 * implemented anywhere yet; the UI shows them as "future" notices instead. Demo
 * task edits are kept in browser memory only (see `context/TasksContext.tsx`).
 */
export interface StudioApi {
  readonly mode: DataSourceMode;

  getCommandCentre(): Promise<CommandCentreData>;

  listProjects(): Promise<Project[]>;
  listProjectReferences(projectSlug: string): Promise<ProjectReference[]>;

  listDepartments(): Promise<Department[]>;
  /** Resolves to `null` when no department has this slug. */
  getDepartmentWorkspace(departmentSlug: string): Promise<DepartmentWorkspace | null>;

  /** Initial task list. */
  listTasks(): Promise<Task[]>;

  listResearchDocs(): Promise<ResearchDoc[]>;
  listTemplates(): Promise<Template[]>;
  listKnowledgeDocs(): Promise<KnowledgeDoc[]>;

  listAgents(): Promise<AgentRecord[]>;
  listAgentNodes(): Promise<AgentNode[]>;
  getUsageReport(): Promise<UsageReport>;

  listDecisions(): Promise<Decision[]>;
  listApprovals(): Promise<Approval[]>;
  listIntegrations(): Promise<Integration[]>;
  listAuditEvents(): Promise<AuditEvent[]>;
}
