import type { Department, DepartmentSlug, DepartmentWorkspace, QueueItem, WorkItem } from "../types";

/** DEMO DATA — the five studio departments. */
export const demoDepartments: Department[] = [
  { slug: "concept-lab", name: "Concept Lab", desc: "Explore ideas, research markets and design game concepts.", icon: "lightbulb", color: "pink", image: "https://images.unsplash.com/photo-1500534623283-312aade485b7?w=900&q=85", metric: "12 concepts explored" },
  { slug: "game-development", name: "Game Development", desc: "Build, test and iterate in Unity with AI assistance.", icon: "gamepad", color: "blue", image: "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=900&q=85", metric: "3 active projects" },
  { slug: "asset-production", name: "Asset Production", desc: "Generate and manage 2D/3D assets, audio and VFX.", icon: "image", color: "green", image: "https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&q=85", metric: "84 assets in library" },
  { slug: "marketing-studio", name: "Marketing Studio", desc: "Create devlogs, trailers and social content.", icon: "megaphone", color: "orange", image: "https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?w=900&q=85", metric: "24 content pieces" },
  { slug: "post-launch-intelligence", name: "Post-Launch Intelligence", desc: "Turn player feedback into actionable updates and insights.", icon: "message", color: "purple", image: "https://images.unsplash.com/photo-1519608487953-e999c86e7455?w=900&q=85", metric: "37 unique issues" },
];

type WorkspaceDetail = Omit<DepartmentWorkspace, "department">;

const workItems = (prefix: string, items: Omit<WorkItem, "id">[]): WorkItem[] =>
  items.map((item, i) => ({ ...item, id: `${prefix}-item-${i + 1}` }));
const queueItems = (prefix: string, items: Omit<QueueItem, "id">[]): QueueItem[] =>
  items.map((item, i) => ({ ...item, id: `${prefix}-queue-${i + 1}` }));

/** DEMO DATA — per-department workspace content (tabs, sample work, queued work). */
export const demoDepartmentWorkspaces: Record<DepartmentSlug, WorkspaceDetail> = {
  "concept-lab": {
    tabs: ["Concepts", "Research Briefs", "Evaluations", "Ideation", "Decision Log"],
    actions: ["Start a new concept", "Create research brief"],
    items: workItems("concept", [
      { title: "Mournforge", detail: "Dark fantasy world between human and monster realities", status: "Concept in progress", icon: "lightbulb" },
      { title: "Shattered Veil", detail: "Supernatural horror FPS concept and world direction", status: "Design exploration", icon: "flask" },
      { title: "Market opportunity scan", detail: "Research adjacent indie horror and action games", status: "Ready to review", icon: "search" },
    ]),
    queue: queueItems("concept", [
      { title: "Compare three horror market segments", detail: "Research brief · Due for review", priority: "High", owner: "Research Agent" },
      { title: "Score Mournforge concept scope", detail: "Feasibility assessment", priority: "Medium", owner: "Concept Agent" },
    ]),
    tabDescriptions: {
      Evaluations: "Concept scorecards, feasibility reviews and decision records.",
    },
  },
  "game-development": {
    tabs: ["Active Projects", "Work Queue", "Builds & Tests", "Technical Docs", "Decision Log"],
    actions: ["New development task", "Inspect project"],
    items: workItems("dev", [
      { title: "FPS Controller Package", detail: "Core movement and game-feel pass; integration architecture next", status: "In development", icon: "gamepad" },
      { title: "Project Horizon", detail: "Prototype gameplay systems and environment blockout", status: "Prototype", icon: "folder" },
      { title: "Dead Frequency", detail: "Project setup and horror gameplay foundations", status: "Pre-production", icon: "code" },
    ]),
    queue: queueItems("dev", [
      { title: "Review FPS controller movement architecture", detail: "Integration task · Awaiting developer review", priority: "High", owner: "Unity Agent" },
      { title: "Run controller regression test plan", detail: "Test suite · Ready to execute", priority: "Medium", owner: "QA Agent" },
      { title: "Document camera tuning parameters", detail: "Documentation task", priority: "Low", owner: "Documentation Agent" },
    ]),
    tabDescriptions: {
      "Builds & Tests": "Build history, test runs, compilation results and verification evidence.",
      "Technical Docs": "Architecture notes, API references, technical decisions and implementation docs.",
    },
  },
  "asset-production": {
    tabs: ["Asset Library", "Production Queue", "Reviews", "Pipelines", "Decision Log"],
    actions: ["Create asset brief", "Import assets"],
    items: workItems("asset", [
      { title: "Environment asset collection", detail: "Low-poly coastal environment references and props", status: "Reference collection", icon: "box" },
      { title: "Audio library", detail: "Ambience, effects and UI audio resources", status: "In library", icon: "audio" },
      { title: "Visual style guide", detail: "Reusable art direction and material standards", status: "Needs review", icon: "palette" },
    ]),
    queue: queueItems("asset", [
      { title: "Prepare coastal prop asset batch", detail: "Asset brief · Awaiting approval", priority: "High", owner: "Asset Agent" },
      { title: "Validate texture import settings", detail: "Technical validation", priority: "Medium", owner: "Pipeline Agent" },
    ]),
    tabDescriptions: {
      Reviews: "Assets awaiting technical, visual or creative review.",
      Pipelines: "Reusable generation, processing and import pipelines.",
    },
  },
  "marketing-studio": {
    tabs: ["Content Pipeline", "Campaigns", "Media Library", "Performance", "Decision Log"],
    actions: ["Create content brief", "Plan campaign"],
    items: workItems("marketing", [
      { title: "Monthly development update", detail: "Notes, screenshots and progress highlights", status: "Draft", icon: "file-text" },
      { title: "Gameplay feature showcase", detail: "Short-form video template and shot list", status: "Planned", icon: "clapperboard" },
      { title: "Studio social calendar", detail: "Upcoming posts and release moments", status: "Planning", icon: "calendar" },
    ]),
    queue: queueItems("marketing", [
      { title: "Assemble weekly development update", detail: "Video production · Waiting for footage selection", priority: "High", owner: "Content Agent" },
      { title: "Draft gameplay showcase captions", detail: "Social content task", priority: "Medium", owner: "Copy Agent" },
    ]),
    tabDescriptions: {
      "Media Library": "Approved footage, scripts, thumbnails, audio and rendered exports.",
    },
  },
  "post-launch-intelligence": {
    tabs: ["Feedback Inbox", "Issue Clusters", "Prioritised Backlog", "Reports", "Decision Log"],
    actions: ["Review feedback", "Generate insight report"],
    items: workItems("feedback", [
      { title: "Audio positioning bug", detail: "18 reports · Bug · High priority", status: "Candidate issue", icon: "bug" },
      { title: "Sprint stamina tuning", detail: "14 reports · Balance · Medium priority", status: "Needs review", icon: "gauge" },
      { title: "Environmental storytelling", detail: "11 reports · Feature request", status: "Emerging theme", icon: "star" },
    ]),
    queue: queueItems("feedback", [
      { title: "Review audio-positioning issue cluster", detail: "18 related reports · Evidence review", priority: "High", owner: "Feedback Agent" },
      { title: "Prepare sprint stamina balance report", detail: "14 related reports · Analysis", priority: "Medium", owner: "Analysis Agent" },
    ]),
    tabDescriptions: {
      "Prioritised Backlog": "Ranked issues with evidence, confidence, impact and estimated effort.",
    },
  },
};
