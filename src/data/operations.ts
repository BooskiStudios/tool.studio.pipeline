import type { AgentNode, AgentRecord, Approval, AuditEvent, Decision, Integration, UsageReport } from "../types";

/** DEMO DATA — the specialist AI workforce shown in Agent Management. */
export const demoAgents: AgentRecord[] = [
  { name: "Orchestrator", role: "Task routing & coordination", department: "Studio-wide", status: "Coordinating", work: "Breaking requests into tasks and assigning specialist agents", model: "Claude", permissions: "Read · Create · Route", cost: "Shared" },
  { name: "Research Agent", role: "Market & reference research", department: "Concept Lab", status: "Working", work: "Preparing indie horror market landscape", model: "Claude", permissions: "Read · Create", cost: "Tracked per task" },
  { name: "Unity Agent", role: "Unity development specialist", department: "Game Development", status: "Working", work: "Reviewing FPS controller architecture", model: "Claude Code", permissions: "Read · Create · Modify · Execute (approval)", cost: "Tracked per task" },
  { name: "Asset Agent", role: "Asset creation & pipeline support", department: "Asset Production", status: "Available", work: "No active assignment", model: "Configurable", permissions: "Read · Create", cost: "Tracked per task" },
  { name: "Marketing Agent", role: "Marketing & content production", department: "Marketing Studio", status: "Available", work: "No active assignment", model: "Configurable", permissions: "Read · Create · Publish (approval)", cost: "Tracked per task" },
  { name: "Quality Agent", role: "Review, testing & verification", department: "Studio-wide", status: "Reviewing", work: "Checking acceptance criteria and evidence", model: "Configurable", permissions: "Read · Execute (approval)", cost: "Tracked per task" },
];

/** DEMO DATA — nodes on the Studio Operations workflow canvas (positions in % of canvas). */
export const demoAgentNodes: AgentNode[] = [
  { name: "Orchestrator", role: "Task routing & coordination", icon: "network", x: 50, y: 9, tasks: ["Breaking down incoming requests", "Assigning work to specialist agents"] },
  { name: "Research Agent", role: "Research & evidence gathering", icon: "search", x: 13, y: 43, tasks: ["Collecting competitor references", "Preparing market landscape report"] },
  { name: "Unity Agent", role: "Game development", icon: "code", x: 38, y: 43, tasks: ["Reviewing FPS controller architecture", "Preparing regression test plan"] },
  { name: "Asset Agent", role: "Asset production", icon: "box", x: 63, y: 43, tasks: ["Preparing environment asset brief", "Checking import requirements"] },
  { name: "Marketing Agent", role: "Content production", icon: "megaphone", x: 88, y: 43, tasks: ["Drafting development update outline"] },
  { name: "Quality Agent", role: "Review & verification", icon: "shield", x: 50, y: 78, tasks: ["Checking task acceptance criteria", "Reviewing evidence before completion"] },
];

/** DEMO DATA — illustrative usage figures. Not real provider charges. */
export const demoUsage: UsageReport = {
  summary: [
    { label: "Estimated monthly spend", value: "£22.50", note: "Illustrative sample only" },
    { label: "Model usage", value: "106k tokens", note: "Illustrative sample only" },
    { label: "API usage", value: "5 workflows", note: "Illustrative sample only" },
    { label: "Budget status", value: "Not configured", note: "Set limits before automation" },
  ],
  byDepartment: [
    { name: "Concept", tokens: 18, cost: 3.2 },
    { name: "Development", tokens: 42, cost: 8.4 },
    { name: "Assets", tokens: 25, cost: 5.1 },
    { name: "Marketing", tokens: 12, cost: 2.4 },
    { name: "Post-launch", tokens: 9, cost: 1.8 },
  ],
  weeklySpend: [
    { period: "W1", cost: 3.2 },
    { period: "W2", cost: 4.8 },
    { period: "W3", cost: 6.1 },
    { period: "W4", cost: 6.8 },
  ],
};

/** DEMO DATA — sample Decision Log entries. */
export const demoDecisions: Decision[] = [
  { id: "dec-1", date: "04 Nov 2026 · 14:32", decision: "Keep Booski Core model-provider agnostic", department: "Studio Operations", agent: "Architecture Agent", type: "Architecture", reason: "Avoid locking orchestration and future workflows to a single model provider." },
  { id: "dec-2", date: "04 Nov 2026 · 12:10", decision: "Use a single central Decision Log with contextual filters", department: "Studio Operations", agent: "Orchestrator", type: "Product", reason: "Maintain one source of truth while allowing department-level views." },
  { id: "dec-3", date: "03 Nov 2026 · 16:45", decision: "Unity is the first supported engine integration", department: "Game Development", agent: "Unity Agent", type: "Technical", reason: "Prioritise the existing Unity workflow before adding Unreal support." },
  { id: "dec-4", date: "02 Nov 2026 · 11:20", decision: "Separate project knowledge from studio-wide knowledge", department: "Concept Lab", agent: "Research Agent", type: "Knowledge", reason: "Prevent project-specific assumptions becoming universal studio rules." },
];

/** DEMO DATA — pending approvals. Nothing is actually approved or executed. */
export const demoApprovals: Approval[] = [
  { id: "apr-1", agent: "Unity Agent", title: "Review controller architecture changes", department: "Game Development", kind: "File modification" },
  { id: "apr-2", agent: "Marketing Agent", title: "Approve gameplay showcase script", department: "Marketing Studio", kind: "Content approval" },
  { id: "apr-3", agent: "Asset Agent", title: "Approve environment asset direction", department: "Asset Production", kind: "Creative approval" },
];

/** DEMO DATA — integration catalogue. No integration is connected. */
export const demoIntegrations: Integration[] = [
  { id: "unity", name: "Unity", category: "Game engine", status: "Not connected" },
  { id: "unreal", name: "Unreal Engine", category: "Game engine", status: "Planned" },
  { id: "github", name: "GitHub", category: "Version control", status: "Not connected" },
  { id: "blender", name: "Blender", category: "3D asset production", status: "Not connected" },
  { id: "steam", name: "Steam", category: "Player reviews", status: "Not connected" },
  { id: "discord", name: "Discord", category: "Community feedback", status: "Not connected" },
  { id: "youtube", name: "YouTube", category: "Video & comments", status: "Not connected" },
  { id: "claude-code", name: "Claude Code", category: "AI development tooling", status: "Not connected" },
];

/** DEMO DATA — illustrative audit trail. */
export const demoAuditEvents: AuditEvent[] = [
  { id: "aud-1", agent: "Unity Agent", action: "Reviewed FPS controller architecture", department: "Game Development", time: "Today · 14:32" },
  { id: "aud-2", agent: "Research Agent", action: "Prepared indie horror market scan", department: "Concept Lab", time: "Today · 12:10" },
  { id: "aud-3", agent: "Asset Agent", action: "Collected coastal environment references", department: "Asset Production", time: "Yesterday · 16:45" },
  { id: "aud-4", agent: "Marketing Agent", action: "Drafted gameplay showcase outline", department: "Marketing Studio", time: "Yesterday · 11:20" },
  { id: "aud-5", agent: "Orchestrator", action: "Routed new work to specialist agents", department: "Studio Operations", time: "02 Nov · 09:15" },
];
