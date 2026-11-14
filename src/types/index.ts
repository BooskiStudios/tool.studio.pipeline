/**
 * Types for PREVIEW content: screens and panels for capabilities planned for later phases (AI agents,
 * usage reporting, integrations, reference collection, the Command Centre's AI panels).
 *
 * Records stored in Booski Core (projects, departments, tasks, documents, decisions, approvals,
 * activity) use the API types in `src/api/types.ts` instead.
 */

/** Identifier for an icon in the shared icon registry (see `components/Icon.tsx`). */
export type IconKey =
  | "lightbulb" | "gamepad" | "image" | "megaphone" | "message"
  | "flask" | "search" | "folder" | "code" | "box" | "audio" | "palette"
  | "file-text" | "clapperboard" | "calendar" | "bug" | "gauge" | "star"
  | "file-image" | "network" | "shield" | "bot" | "workflow";

export type Priority = "High" | "Medium" | "Low";

export interface ProjectReference {
  id: string;
  title: string;
  detail: string;
  source: "AI discovered" | "User saved";
}

// ---------------------------------------------------------------- Command Centre previews

export interface WorkforceMember {
  name: string;
  status: string;
  icon: IconKey;
}

export interface InsightStat {
  label: string;
  value: string;
  change: string;
}

export interface FeedbackStat {
  label: string;
  value: string;
  tone: "pink" | "blue" | "orange" | "green";
}

export interface FeedbackIssue {
  id: string;
  title: string;
  severity: Priority;
  reports: number;
}

export interface AssetPreview {
  id: string;
  name: string;
  image: string;
}

export interface CommandCentrePreview {
  workforce: WorkforceMember[];
  insights: InsightStat[];
  productivityChange: string;
  feedbackStats: FeedbackStat[];
  feedbackIssues: FeedbackIssue[];
  latestAssets: AssetPreview[];
}

// ---------------------------------------------------------------- Agents & operations (previews)

export type AgentStatus = "Coordinating" | "Working" | "Available" | "Reviewing";

export interface AgentRecord {
  name: string;
  role: string;
  department: string;
  status: AgentStatus;
  work: string;
  model: string;
  permissions: string;
  cost: string;
}

/** A node on the Studio Operations workflow canvas. Positions are percentages of the canvas. */
export interface AgentNode {
  name: string;
  role: string;
  icon: IconKey;
  x: number;
  y: number;
  tasks: string[];
}

export interface UsageSummary {
  label: string;
  value: string;
  note: string;
}

export interface DepartmentUsage {
  name: string;
  tokens: number;
  cost: number;
}

export interface SpendPoint {
  period: string;
  cost: number;
}

export interface UsageReport {
  summary: UsageSummary[];
  byDepartment: DepartmentUsage[];
  weeklySpend: SpendPoint[];
}

export interface Integration {
  id: string;
  name: string;
  category: string;
  status: "Not connected" | "Planned" | "Connected";
}
