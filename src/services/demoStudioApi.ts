import { commandCentrePreview } from "../data/commandCentre";
import { demoAgentNodes, demoAgents, demoIntegrations, demoUsage } from "../data/operations";
import { previewProjectReferences } from "../data/projects";
import type { PreviewApi } from "./studioApi";

const resolve = <T,>(value: T): Promise<T> => Promise.resolve(value);

/** Preview content bundled with the frontend. Nothing here is fetched, saved or shared. */
export const previewApi: PreviewApi = {
  getCommandCentrePreview: () => resolve(commandCentrePreview),
  // The example Reference Vault is the same for every project.
  listProjectReferences: () => resolve(previewProjectReferences),
  listAgents: () => resolve(demoAgents),
  listAgentNodes: () => resolve(demoAgentNodes),
  getUsageReport: () => resolve(demoUsage),
  listIntegrations: () => resolve(demoIntegrations),
};
