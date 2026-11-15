import type { Capability, Role } from "../api/types";

/**
 * What each workspace role may do. Mirrors `backend/src/booski_core/access/roles.py` and is used only
 * to decide which buttons to show: Booski Core enforces every rule itself, so a stale copy here could
 * hide or show a button but never grant access.
 */
const EVERYONE: Capability[] = ["workspace.read", "members.read", "activity.read"];
const COLLABORATE: Capability[] = ["tasks.create", "comments.write"];
const DEVELOP: Capability[] = [
  "tasks.edit_any", "milestones.write", "documents.write", "decisions.write", "memory.write", "approvals.request",
  "approvals.review_assigned", "ai.use",
];
const ADMINISTER: Capability[] = [
  "workspace.update", "members.manage", "invitations.manage", "departments.manage", "projects.manage", "approvals.decide",
  "audit.read", "ai.manage", "ai.usage.read", "agents.manage",
];

export const ROLE_CAPABILITIES: Record<Role, ReadonlySet<Capability>> = {
  owner: new Set([...EVERYONE, ...COLLABORATE, ...DEVELOP, ...ADMINISTER, "ownership.transfer"]),
  admin: new Set([...EVERYONE, ...COLLABORATE, ...DEVELOP, ...ADMINISTER]),
  developer: new Set([...EVERYONE, ...COLLABORATE, ...DEVELOP]),
  collaborator: new Set([...EVERYONE, ...COLLABORATE]),
  viewer: new Set(EVERYONE),
};

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  developer: "Developer",
  collaborator: "Collaborator",
  viewer: "Viewer",
};

/** Roles an owner or admin may give to someone else. */
export const MANAGEABLE_ROLES: Record<Role, Role[]> = {
  owner: ["admin", "developer", "collaborator", "viewer"],
  admin: ["developer", "collaborator", "viewer"],
  developer: [],
  collaborator: [],
  viewer: [],
};
