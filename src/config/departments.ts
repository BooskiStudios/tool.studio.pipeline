import type { DocumentKind } from "../api/types";
import type { IconKey } from "../types";

/**
 * How each department's workspace is presented (decision D14: tabs, actions and artwork are frontend
 * configuration). The departments themselves — names, descriptions, colours, which exist — come from
 * Booski Core and can be renamed or added per workspace; a department without an entry here gets the
 * generic layout.
 *
 * Tab kinds:
 * - `tasks`, `documents`, `decisions`, `approvals`, `projects`: live records from Booski Core, filtered
 *   to this department where the record has a department.
 * - `sample`: illustrative content for a capability that arrives in a later phase (clearly labelled).
 * - `planned`: an empty placeholder describing what will appear.
 */
export type TabSpec =
  | { label: string; kind: "tasks" | "decisions" | "projects" }
  | { label: string; kind: "documents"; documentKind?: DocumentKind }
  | { label: string; kind: "approvals"; approvalKind?: "asset" | "publishing" | "code_change" }
  | { label: string; kind: "sample" }
  | { label: string; kind: "planned"; description: string };

export type ActionSpec =
  | { label: string; kind: "task" }
  | { label: string; kind: "document"; documentKind: DocumentKind }
  | { label: string; kind: "planned"; notice: string };

export interface SampleItem {
  id: string;
  title: string;
  detail: string;
  status: string;
  icon: IconKey;
}

export interface DepartmentPresentation {
  image: string;
  tabs: TabSpec[];
  actions: ActionSpec[];
  /** Illustrative items for the `sample` tab. Not stored anywhere. */
  sampleItems: SampleItem[];
}

const sample = (prefix: string, items: Omit<SampleItem, "id">[]): SampleItem[] =>
  items.map((item, i) => ({ ...item, id: `${prefix}-sample-${i + 1}` }));

const DECISIONS: TabSpec = { label: "Decision Log", kind: "decisions" };

const PRESENTATIONS: Record<string, DepartmentPresentation> = {
  "concept-lab": {
    image: "https://images.unsplash.com/photo-1500534623283-312aade485b7?w=900&q=85",
    tabs: [
      { label: "Concepts", kind: "sample" },
      { label: "Research Briefs", kind: "documents", documentKind: "research" },
      { label: "Work Queue", kind: "tasks" },
      { label: "Evaluations", kind: "planned", description: "Concept scorecards, feasibility reviews and decision records." },
      DECISIONS,
    ],
    actions: [
      { label: "Start a new concept", kind: "planned", notice: "AI-assisted concept development arrives with Booski AI Core in Phase 3." },
      { label: "Create research brief", kind: "document", documentKind: "research" },
    ],
    sampleItems: sample("concept", [
      { title: "Mournforge", detail: "Dark fantasy world between human and monster realities", status: "Concept in progress", icon: "lightbulb" },
      { title: "Shattered Veil", detail: "Supernatural horror FPS concept and world direction", status: "Design exploration", icon: "flask" },
      { title: "Market opportunity scan", detail: "Research adjacent indie horror and action games", status: "Ready to review", icon: "search" },
    ]),
  },
  "game-development": {
    image: "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=900&q=85",
    tabs: [
      { label: "Active Projects", kind: "projects" },
      { label: "Work Queue", kind: "tasks" },
      { label: "Builds & Tests", kind: "planned", description: "Build history, test runs, compilation results and verification evidence (engine bridge, later phase)." },
      { label: "Technical Docs", kind: "documents" },
      DECISIONS,
    ],
    actions: [
      { label: "New development task", kind: "task" },
      { label: "Inspect project", kind: "planned", notice: "Project inspection needs the Unity bridge, planned for a later phase." },
    ],
    sampleItems: [],
  },
  "asset-production": {
    image: "https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&q=85",
    tabs: [
      { label: "Asset Library", kind: "sample" },
      { label: "Production Queue", kind: "tasks" },
      { label: "Reviews", kind: "approvals", approvalKind: "asset" },
      { label: "Pipelines", kind: "planned", description: "Reusable generation, processing and import pipelines." },
      DECISIONS,
    ],
    actions: [
      { label: "Create asset brief", kind: "document", documentKind: "design_doc" },
      { label: "Import assets", kind: "planned", notice: "File storage for assets arrives in a later phase; nothing is uploaded yet." },
    ],
    sampleItems: sample("asset", [
      { title: "Environment asset collection", detail: "Low-poly coastal environment references and props", status: "Reference collection", icon: "box" },
      { title: "Audio library", detail: "Ambience, effects and UI audio resources", status: "In library", icon: "audio" },
      { title: "Visual style guide", detail: "Reusable art direction and material standards", status: "Needs review", icon: "palette" },
    ]),
  },
  "marketing-studio": {
    image: "https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?w=900&q=85",
    tabs: [
      { label: "Content Pipeline", kind: "tasks" },
      { label: "Campaigns", kind: "sample" },
      { label: "Media Library", kind: "planned", description: "Approved footage, scripts, thumbnails, audio and rendered exports." },
      { label: "Publishing Approvals", kind: "approvals", approvalKind: "publishing" },
      DECISIONS,
    ],
    actions: [
      { label: "Create content brief", kind: "document", documentKind: "note" },
      { label: "Plan campaign", kind: "planned", notice: "Campaign planning and marketing automation are planned for a later phase." },
    ],
    sampleItems: sample("marketing", [
      { title: "Monthly development update", detail: "Notes, screenshots and progress highlights", status: "Draft", icon: "file-text" },
      { title: "Gameplay feature showcase", detail: "Short-form video template and shot list", status: "Planned", icon: "clapperboard" },
      { title: "Studio social calendar", detail: "Upcoming posts and release moments", status: "Planning", icon: "calendar" },
    ]),
  },
  "post-launch-intelligence": {
    image: "https://images.unsplash.com/photo-1519608487953-e999c86e7455?w=900&q=85",
    tabs: [
      { label: "Feedback Inbox", kind: "sample" },
      { label: "Prioritised Backlog", kind: "tasks" },
      { label: "Reports", kind: "documents", documentKind: "report" },
      { label: "Issue Clusters", kind: "planned", description: "Grouped player reports with evidence, confidence and impact (feedback ingestion, later phase)." },
      DECISIONS,
    ],
    actions: [
      { label: "Review feedback", kind: "planned", notice: "Player feedback ingestion arrives in a later phase." },
      { label: "Generate insight report", kind: "document", documentKind: "report" },
    ],
    sampleItems: sample("feedback", [
      { title: "Audio positioning bug", detail: "18 reports · Bug · High priority", status: "Candidate issue", icon: "bug" },
      { title: "Sprint stamina tuning", detail: "14 reports · Balance · Medium priority", status: "Needs review", icon: "gauge" },
      { title: "Environmental storytelling", detail: "11 reports · Feature request", status: "Emerging theme", icon: "star" },
    ]),
  },
};

const GENERIC: DepartmentPresentation = {
  image: "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=900&q=85",
  tabs: [
    { label: "Work Queue", kind: "tasks" },
    { label: "Documents", kind: "documents" },
    { label: "Approvals", kind: "approvals" },
    DECISIONS,
  ],
  actions: [
    { label: "New task", kind: "task" },
    { label: "New document", kind: "document", documentKind: "note" },
  ],
  sampleItems: [],
};

export function departmentPresentation(slug: string): DepartmentPresentation {
  return PRESENTATIONS[slug] ?? GENERIC;
}

/** The "Studio Operations" department is reached through the Studio Operations page, not a department link. */
export const NAV_HIDDEN_DEPARTMENTS = new Set(["studio-operations"]);
