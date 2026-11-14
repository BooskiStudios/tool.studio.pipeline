/**
 * Booski Core API types. These mirror the backend's Pydantic schemas (see `/api/docs` while the API runs
 * in development). Dates are ISO-8601 strings; ids are UUID strings.
 */

export type Uuid = string;
export type IsoDateTime = string;
/** `YYYY-MM-DD` */
export type IsoDate = string;

export interface Page<T> {
  items: T[];
  /** Pass back as `cursor` to get the next page; `null` on the last page. */
  next_cursor: string | null;
}

// ---------------------------------------------------------------- identity & workspaces

export type Role = "owner" | "admin" | "developer" | "collaborator" | "viewer";
export type AssignableRole = Exclude<Role, "owner">;

export type Capability =
  | "workspace.read" | "workspace.update" | "members.read" | "members.manage" | "invitations.manage"
  | "ownership.transfer" | "departments.manage" | "projects.manage" | "tasks.create" | "tasks.edit_any"
  | "comments.write" | "milestones.write" | "documents.write" | "decisions.write" | "approvals.request"
  | "approvals.review_assigned" | "approvals.decide" | "activity.read" | "audit.read";

export interface User {
  id: Uuid;
  email: string;
  display_name: string;
}

export interface SessionInfo {
  id: Uuid;
  created_at: IsoDateTime;
  last_seen_at: IsoDateTime;
  idle_expires_at: IsoDateTime;
  absolute_expires_at: IsoDateTime;
  ip: string | null;
  user_agent: string | null;
  current?: boolean;
}

export interface MembershipSummary {
  workspace_id: Uuid;
  workspace_slug: string;
  workspace_name: string;
  role: Role;
}

export interface MeResponse {
  user: User;
  session: SessionInfo;
  workspaces: MembershipSummary[];
}

export interface LoginResponse {
  user: User;
  session: SessionInfo;
  csrf_token: string;
}

export interface Workspace {
  id: Uuid;
  slug: string;
  name: string;
  created_at: IsoDateTime;
  role: Role;
}

export interface Member {
  user_id: Uuid;
  email: string;
  display_name: string;
  role: Role;
  joined_at: IsoDateTime;
}

export interface Invitation {
  id: Uuid;
  email: string;
  role: Role;
  created_at: IsoDateTime;
  expires_at: IsoDateTime;
  invited_by_user_id: Uuid | null;
}

export interface InvitationCreated {
  invitation: Invitation;
  /** Shown once; not stored by the server. */
  token: string;
}

export interface InvitationPreview {
  workspace_slug: string;
  workspace_name: string;
  email: string;
  role: Role;
  expires_at: IsoDateTime;
  account_exists: boolean;
}

export interface InvitationAccepted {
  workspace: Workspace;
  user: User;
  signed_in: boolean;
  csrf_token?: string | null;
}

// ---------------------------------------------------------------- studio

export type AccentColor = "pink" | "blue" | "green" | "orange" | "purple" | "cyan" | "red";

export interface Progress {
  total: number;
  done: number;
  percent: number;
}

export interface Department {
  id: Uuid;
  slug: string;
  name: string;
  description: string;
  icon_key: string;
  accent_color: AccentColor;
  sort_order: number;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type ProjectStatus = "concept" | "pre_production" | "prototype" | "production" | "released" | "paused" | "cancelled";
export type ProjectVisibility = "workspace" | "restricted";
export type ProjectAccess = "viewer" | "contributor";
export type PropertyValue = string | number | boolean | null;

export interface Project {
  id: Uuid;
  slug: string;
  name: string;
  description: string;
  project_type: string;
  engine: string;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  accent_color: AccentColor;
  cover_image_url: string | null;
  properties: Record<string, PropertyValue>;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  version: number;
  progress: Progress;
  /** What the current user can do inside this project. */
  capabilities: Capability[];
}

export interface ProjectInput {
  slug?: string;
  name?: string;
  description?: string;
  project_type?: string;
  engine?: string;
  status?: ProjectStatus;
  visibility?: ProjectVisibility;
  accent_color?: AccentColor;
  cover_image_url?: string | null;
  archived?: boolean;
  version?: number;
}

export interface ProjectMember {
  user_id: Uuid;
  email: string;
  display_name: string;
  access: ProjectAccess;
  added_at: IsoDateTime;
}

export interface Workstream {
  id: Uuid;
  project_id: Uuid;
  department_id: Uuid;
  name: string;
  description: string;
  sort_order: number;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type MilestoneStatus = "planned" | "in_progress" | "completed" | "cancelled";

export interface Milestone {
  id: Uuid;
  project_id: Uuid;
  name: string;
  description: string;
  target_date: IsoDate | null;
  status: MilestoneStatus;
  completed_at: IsoDateTime | null;
  position: number;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  version: number;
  progress: Progress;
}

export interface MilestoneInput {
  name?: string;
  description?: string;
  target_date?: IsoDate | null;
  status?: MilestoneStatus;
  archived?: boolean;
  version?: number;
}

export type TaskStatus = "backlog" | "todo" | "in_progress" | "in_review" | "blocked" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high";

export interface Task {
  id: Uuid;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  project_id: Uuid | null;
  department_id: Uuid | null;
  workstream_id: Uuid | null;
  milestone_id: Uuid | null;
  parent_task_id: Uuid | null;
  assignee_user_id: Uuid | null;
  created_by_user_id: Uuid | null;
  start_date: IsoDate | null;
  due_date: IsoDate | null;
  completed_at: IsoDateTime | null;
  position: number;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  version: number;
  can_edit: boolean;
}

export interface TaskInput {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  project_id?: Uuid | null;
  department_id?: Uuid | null;
  workstream_id?: Uuid | null;
  milestone_id?: Uuid | null;
  parent_task_id?: Uuid | null;
  assignee_user_id?: Uuid | null;
  start_date?: IsoDate | null;
  due_date?: IsoDate | null;
  archived?: boolean;
  version?: number;
}

export interface Comment {
  id: Uuid;
  task_id: Uuid;
  author_user_id: Uuid | null;
  body: string;
  created_at: IsoDateTime;
  edited_at: IsoDateTime | null;
  deleted: boolean;
}

export type DocumentKind = "guide" | "research" | "template" | "reference" | "design_doc" | "note" | "report";

export interface DocumentSummary {
  id: Uuid;
  kind: DocumentKind;
  title: string;
  summary: string;
  tags: string[];
  project_id: Uuid | null;
  department_id: Uuid | null;
  current_revision: number;
  created_by_user_id: Uuid | null;
  updated_by_user_id: Uuid | null;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  version: number;
}

export interface StudioDocument extends DocumentSummary {
  body: string;
  can_edit: boolean;
}

export interface DocumentInput {
  kind?: DocumentKind;
  title?: string;
  summary?: string;
  body?: string;
  tags?: string[];
  project_id?: Uuid | null;
  department_id?: Uuid | null;
  change_note?: string;
  archived?: boolean;
  version?: number;
}

export interface RevisionSummary {
  revision_no: number;
  title: string;
  change_note: string;
  created_by_user_id: Uuid | null;
  created_at: IsoDateTime;
}

export interface Revision extends RevisionSummary {
  body: string;
}

export type DecisionStatus = "proposed" | "accepted" | "rejected" | "superseded";

export interface DecisionOption {
  title: string;
  summary?: string;
}

export interface Decision {
  id: Uuid;
  title: string;
  context: string;
  options: DecisionOption[];
  outcome: string;
  rationale: string;
  status: DecisionStatus;
  project_id: Uuid | null;
  department_id: Uuid | null;
  author_user_id: Uuid | null;
  recorded_at: IsoDateTime;
  decided_at: IsoDateTime | null;
  supersedes_decision_id: Uuid | null;
  superseded_by_decision_id: Uuid | null;
  document_ids: Uuid[];
  updated_at: IsoDateTime;
  version: number;
}

export interface DecisionInput {
  title?: string;
  context?: string;
  options?: DecisionOption[];
  outcome?: string;
  rationale?: string;
  status?: DecisionStatus;
  project_id?: Uuid | null;
  department_id?: Uuid | null;
  supersedes_decision_id?: Uuid | null;
  document_ids?: Uuid[];
  version?: number;
}

export type ApprovalKind = "general" | "ai_output" | "code_change" | "asset" | "spending" | "publishing" | "project_decision";
export type ApprovalStatus = "pending" | "changes_requested" | "approved" | "rejected" | "cancelled";
export type ApprovalSubjectType = "task" | "document" | "decision" | "milestone" | "project";
export type ReviewAction = "approve" | "reject" | "request_changes" | "comment";
export type ReviewRecordAction = "approved" | "rejected" | "changes_requested" | "commented" | "resubmitted" | "cancelled";

export interface Approval {
  id: Uuid;
  kind: ApprovalKind;
  title: string;
  description: string;
  payload: Record<string, unknown>;
  project_id: Uuid | null;
  subject_type: ApprovalSubjectType | null;
  subject_id: Uuid | null;
  status: ApprovalStatus;
  requested_by_user_id: Uuid | null;
  reviewer_user_id: Uuid | null;
  resolved_by_user_id: Uuid | null;
  resolution_comment: string;
  resolved_at: IsoDateTime | null;
  due_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  version: number;
  /** True when the current user may approve, reject or request changes now. */
  can_decide: boolean;
}

export interface ApprovalInput {
  kind?: ApprovalKind;
  title: string;
  description?: string;
  project_id?: Uuid | null;
  subject_type?: ApprovalSubjectType | null;
  subject_id?: Uuid | null;
  reviewer_user_id?: Uuid | null;
  due_at?: IsoDateTime | null;
}

export interface Review {
  id: Uuid;
  actor_user_id: Uuid | null;
  action: ReviewRecordAction;
  comment: string;
  created_at: IsoDateTime;
}

export interface ActivityEvent {
  id: Uuid;
  created_at: IsoDateTime;
  verb: string;
  entity_type: string;
  entity_id: Uuid | null;
  project_id: Uuid | null;
  actor_type: "user" | "system";
  actor_user_id: Uuid | null;
  summary: string;
  changes: Record<string, unknown>;
  request_id: string | null;
}

export interface Readiness {
  status: "ok" | "unavailable";
  database: "ok" | "unreachable";
  migrations: "head" | "behind" | "unknown";
}
