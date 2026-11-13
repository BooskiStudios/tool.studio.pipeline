/**
 * Shared domain types for the Booski Studios frontend.
 *
 * These describe the shape of records the UI consumes. They are deliberately
 * transport-agnostic: today they are filled from demo data in `src/data`, and
 * later they will be filled from Booski Core (FastAPI) responses.
 */

/** Identifier for an icon in the shared icon registry (see `components/Icon.tsx`). */
export type IconKey =
  | "lightbulb" | "gamepad" | "image" | "megaphone" | "message"
  | "flask" | "search" | "folder" | "code" | "box" | "audio" | "palette"
  | "file-text" | "clapperboard" | "calendar" | "bug" | "gauge" | "star"
  | "file-image" | "network" | "shield" | "bot" | "workflow";

/** Accent colour names used by existing CSS modifier classes (e.g. `.department-card.pink`). */
export type AccentColor = "pink" | "blue" | "green" | "orange" | "purple" | "cyan" | "red";

export type Priority = "High" | "Medium" | "Low";

// ---------------------------------------------------------------- Projects

export interface Project {
  /** URL-safe identifier, used in `/projects/:projectSlug`. */
  slug: string;
  name: string;
  type: string;
  status: string;
  color: AccentColor;
  image: string;
  progress: number;
  engine: string;
  description: string;
}

export interface ProjectReference {
  id: string;
  title: string;
  detail: string;
  source: "AI discovered" | "User saved";
}

// ---------------------------------------------------------------- Departments

export type DepartmentSlug =
  | "concept-lab"
  | "game-development"
  | "asset-production"
  | "marketing-studio"
  | "post-launch-intelligence";

export interface Department {
  slug: DepartmentSlug;
  name: string;
  desc: string;
  icon: IconKey;
  color: AccentColor;
  image: string;
  metric: string;
}

export interface WorkItem {
  id: string;
  title: string;
  detail: string;
  status: string;
  icon: IconKey;
}

export interface QueueItem {
  id: string;
  title: string;
  detail: string;
  priority: Priority;
  owner: string;
}

/** Everything a department workspace page needs, in one response. */
export interface DepartmentWorkspace {
  department: Department;
  /** Tab labels in display order. Tab 0 = items, tab 1 = queue; the last is always "Decision Log". */
  tabs: string[];
  /** Hero action labels; the first is the primary action. */
  actions: string[];
  items: WorkItem[];
  queue: QueueItem[];
  /** Placeholder descriptions for tabs that do not yet have real content, keyed by tab label. */
  tabDescriptions: Record<string, string>;
}

// ---------------------------------------------------------------- Tasks

export interface Task {
  id: string;
  title: string;
  department: string;
  priority: Priority;
  done: boolean;
}

// ---------------------------------------------------------------- Command Centre (Home)

export interface CommandMetric {
  id: string;
  label: string;
  value: string;
  note: string;
  icon: IconKey;
  tone: "cyan" | "pink" | "green" | "orange";
}

export interface WorkforceMember {
  name: string;
  status: string;
  icon: IconKey;
}

export interface AttentionItem {
  id: string;
  agent: string;
  title: string;
  department: string;
}

export interface Milestone {
  id: string;
  label: string;
  progress: string;
}

export interface InsightStat {
  label: string;
  value: string;
  change: string;
}

export interface ActivityItem {
  id: string;
  icon: IconKey;
  title: string;
  time: string;
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

export interface CommandCentreData {
  metrics: CommandMetric[];
  workforce: WorkforceMember[];
  attention: AttentionItem[];
  milestones: Milestone[];
  insights: InsightStat[];
  productivityChange: string;
  activity: ActivityItem[];
  feedbackStats: FeedbackStat[];
  feedbackIssues: FeedbackIssue[];
  latestAssets: AssetPreview[];
  focus: { title: string; department: string; label: string };
}

// ---------------------------------------------------------------- Knowledge

export interface ResearchDoc {
  id: string;
  title: string;
  detail: string;
  format: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  detail: string;
  scope: string;
}

// ---------------------------------------------------------------- Agents & operations

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

// ---------------------------------------------------------------- Governance

export interface Decision {
  id: string;
  date: string;
  decision: string;
  department: string;
  agent: string;
  type: string;
  reason: string;
}

export interface Approval {
  id: string;
  agent: string;
  title: string;
  department: string;
  kind: string;
}

export interface Integration {
  id: string;
  name: string;
  category: string;
  status: "Not connected" | "Planned" | "Connected";
}

export interface AuditEvent {
  id: string;
  agent: string;
  action: string;
  department: string;
  time: string;
}
