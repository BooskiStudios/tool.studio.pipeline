import type {
  AccentColor, ApprovalKind, ApprovalStatus, DecisionStatus, DocumentKind, MilestoneStatus, Project, ProjectStatus,
  ReviewRecordAction, TaskPriority, TaskStatus,
} from "../api/types";

export const PROJECT_STATUS: Record<ProjectStatus, string> = {
  concept: "Concept",
  pre_production: "Pre-production",
  prototype: "Prototype",
  production: "Production",
  released: "Released",
  paused: "Paused",
  cancelled: "Cancelled",
};

export const TASK_STATUS: Record<TaskStatus, string> = {
  backlog: "Backlog",
  todo: "To do",
  in_progress: "In progress",
  in_review: "In review",
  blocked: "Blocked",
  done: "Done",
  cancelled: "Cancelled",
};

export const PRIORITY: Record<TaskPriority, string> = { high: "High", medium: "Medium", low: "Low" };

export const MILESTONE_STATUS: Record<MilestoneStatus, string> = {
  planned: "Planned",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const DOCUMENT_KIND: Record<DocumentKind, string> = {
  guide: "Guide",
  research: "Research",
  template: "Template",
  reference: "Reference",
  design_doc: "Design document",
  note: "Note",
  report: "Report",
};

export const DECISION_STATUS: Record<DecisionStatus, string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  rejected: "Rejected",
  superseded: "Superseded",
};

export const APPROVAL_KIND: Record<ApprovalKind, string> = {
  general: "General",
  ai_output: "AI output",
  code_change: "Code change",
  asset: "Asset",
  spending: "Spending",
  publishing: "Publishing",
  project_decision: "Project decision",
};

export const APPROVAL_STATUS: Record<ApprovalStatus, string> = {
  pending: "Waiting for review",
  changes_requested: "Changes requested",
  approved: "Approved",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export const REVIEW_ACTION: Record<ReviewRecordAction, string> = {
  approved: "Approved",
  rejected: "Rejected",
  changes_requested: "Requested changes",
  commented: "Commented",
  resubmitted: "Resubmitted",
  cancelled: "Cancelled",
};

export const ACCENT_COLORS: AccentColor[] = ["cyan", "pink", "blue", "green", "orange", "purple", "red"];

const ACCENT_HEX: Record<AccentColor, [string, string]> = {
  cyan: ["#0b4f63", "#35cce7"],
  pink: ["#5c0f3b", "#ec1681"],
  blue: ["#0d2f5c", "#3b82f6"],
  green: ["#163f22", "#7fd957"],
  orange: ["#5a3110", "#ff9b2f"],
  purple: ["#33185c", "#9f29db"],
  red: ["#5c1414", "#ff4d5e"],
};

/** A project's cover: its own HTTPS image, or a gradient in its accent colour (no external request). */
export function projectImage(project: Pick<Project, "cover_image_url" | "accent_color">): string {
  if (project.cover_image_url) return project.cover_image_url;
  const [dark, light] = ACCENT_HEX[project.accent_color] ?? ACCENT_HEX.cyan;
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">` +
    `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${dark}"/>` +
    `<stop offset="1" stop-color="${light}"/></linearGradient></defs><rect width="640" height="360" fill="url(#g)"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

const dateFormat = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/** "14 Nov 2026" for an ISO date or date-time. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateTimeFormat.format(date);
}

/** "just now", "5 min ago", "3 h ago", "2 days ago", then a date. */
export function timeAgo(value: string, now: Date = new Date()): string {
  const seconds = Math.round((now.getTime() - new Date(value).getTime()) / 1000);
  if (Number.isNaN(seconds)) return "—";
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 7 * 86_400) {
    const days = Math.floor(seconds / 86_400);
    return `${days} ${days === 1 ? "day" : "days"} ago`;
  }
  return formatDate(value);
}

export function isOverdue(dueDate: string | null, status: TaskStatus, today: Date = new Date()): boolean {
  if (!dueDate || status === "done" || status === "cancelled") return false;
  const todayIso = today.toISOString().slice(0, 10);
  return dueDate < todayIso;
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** Lowercase-hyphenated address from a name ("Project Horizon" → "project-horizon"). */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .slice(0, 60)
    .replace(/^-+|-+$/g, "");
}
