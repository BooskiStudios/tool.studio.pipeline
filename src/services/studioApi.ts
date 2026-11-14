import type {
  AgentNode, AgentRecord, CommandCentrePreview, Integration, ProjectReference, UsageReport,
} from "../types";

/**
 * Preview content for capabilities planned for later phases: the AI workforce, agent canvas, usage and
 * cost reporting, integrations, reference collection and the Command Centre's AI panels.
 *
 * Everything that Booski Core stores — projects, departments, tasks, milestones, documents, decisions,
 * approvals and activity — is NOT here: pages load it from the API through `src/api/hooks.ts`.
 * Pages that show preview content label it as such.
 */
export interface PreviewApi {
  getCommandCentrePreview(): Promise<CommandCentrePreview>;
  listProjectReferences(projectSlug: string): Promise<ProjectReference[]>;
  listAgents(): Promise<AgentRecord[]>;
  listAgentNodes(): Promise<AgentNode[]>;
  getUsageReport(): Promise<UsageReport>;
  listIntegrations(): Promise<Integration[]>;
}
