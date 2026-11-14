import { demoCommandCentre } from "../data/commandCentre";
import { demoDepartments, demoDepartmentWorkspaces } from "../data/departments";
import { demoKnowledgeDocs, demoResearchDocs, demoTemplates } from "../data/knowledge";
import {
  demoAgentNodes, demoAgents, demoApprovals, demoAuditEvents, demoDecisions, demoIntegrations, demoUsage,
} from "../data/operations";
import { demoProjectReferences, demoProjects, demoTasks } from "../data/projects";
import type { DepartmentSlug } from "../types";
import type { StudioApi } from "./studioApi";

const resolve = <T,>(value: T): Promise<T> => Promise.resolve(value);

const isDepartmentSlug = (slug: string): slug is DepartmentSlug => slug in demoDepartmentWorkspaces;

/**
 * Demo implementation of `StudioApi`, backed by the static data in `src/data`.
 * Nothing here is fetched, saved or shared between browsers.
 */
export const demoStudioApi: StudioApi = {
  mode: "demo",

  getCommandCentre: () => resolve(demoCommandCentre),

  listProjects: () => resolve(demoProjects),
  // The demo Reference Vault is the same for every project.
  listProjectReferences: () => resolve(demoProjectReferences),

  listDepartments: () => resolve(demoDepartments),
  getDepartmentWorkspace: (slug) => {
    const department = demoDepartments.find((d) => d.slug === slug);
    if (!department || !isDepartmentSlug(slug)) return resolve(null);
    return resolve({ department, ...demoDepartmentWorkspaces[slug] });
  },

  listTasks: () => resolve(demoTasks.map((task) => ({ ...task }))),

  listResearchDocs: () => resolve(demoResearchDocs),
  listTemplates: () => resolve(demoTemplates),
  listKnowledgeDocs: () => resolve(demoKnowledgeDocs),

  listAgents: () => resolve(demoAgents),
  listAgentNodes: () => resolve(demoAgentNodes),
  getUsageReport: () => resolve(demoUsage),

  listDecisions: () => resolve(demoDecisions),
  listApprovals: () => resolve(demoApprovals),
  listIntegrations: () => resolve(demoIntegrations),
  listAuditEvents: () => resolve(demoAuditEvents),
};
