import type { CommandCentreData } from "../types";

/** DEMO DATA — everything shown on the Studio Command Centre (Home). */
export const demoCommandCentre: CommandCentreData = {
  metrics: [
    { id: "projects", label: "Active projects", value: "3", note: "Across 2 development stages", icon: "folder", tone: "cyan" },
    { id: "agents", label: "Registered agents", value: "6", note: "Illustrative workforce", icon: "bot", tone: "pink" },
    { id: "tasks", label: "Tasks in progress", value: "5", note: "Sample workflow activity", icon: "workflow", tone: "green" },
    { id: "approvals", label: "Awaiting approval", value: "3", note: "Demo approval requests", icon: "shield", tone: "orange" },
  ],
  workforce: [
    { name: "Orchestrator", status: "Coordinating", icon: "network" },
    { name: "Research Agent", status: "Working", icon: "search" },
    { name: "Unity Agent", status: "Working", icon: "code" },
    { name: "Asset Agent", status: "Available", icon: "box" },
    { name: "Marketing Agent", status: "Available", icon: "megaphone" },
    { name: "Quality Agent", status: "Reviewing", icon: "shield" },
  ],
  attention: [
    { id: "att-1", agent: "Unity Agent", title: "Review controller architecture changes", department: "Game Development" },
    { id: "att-2", agent: "Marketing Agent", title: "Approve gameplay showcase script", department: "Marketing Studio" },
    { id: "att-3", agent: "Asset Agent", title: "Approve environment asset direction", department: "Asset Production" },
  ],
  milestones: [
    { id: "ms-1", label: "Core movement & interaction systems", progress: "3/5" },
    { id: "ms-2", label: "Initial environment prototype", progress: "Completed" },
    { id: "ms-3", label: "Asset style guide", progress: "2/4" },
    { id: "ms-4", label: "Market analysis", progress: "Completed" },
  ],
  insights: [
    { label: "Ideas Explored", value: "12", change: "+33%" },
    { label: "Assets Generated", value: "84", change: "+120%" },
    { label: "Hours Saved", value: "38", change: "+45%" },
    { label: "Content Created", value: "24", change: "+80%" },
  ],
  productivityChange: "+120%",
  activity: [
    { id: "act-1", icon: "file-image", title: "Generated forest environment assets", time: "10 min ago" },
    { id: "act-2", icon: "code", title: "Updated player controller system", time: "1 hour ago" },
    { id: "act-3", icon: "clapperboard", title: "Created social media storyboard", time: "2 hours ago" },
    { id: "act-4", icon: "search", title: "Researched competitor analysis", time: "3 hours ago" },
  ],
  feedbackStats: [
    { label: "Total Feedback", value: "248", tone: "pink" },
    { label: "Unique Issues", value: "37", tone: "blue" },
    { label: "Need Review", value: "8", tone: "orange" },
    { label: "Positive Mentions", value: "12", tone: "green" },
  ],
  feedbackIssues: [
    { id: "fb-1", title: "Audio positioning bug", severity: "High", reports: 18 },
    { id: "fb-2", title: "Sprint stamina tuning", severity: "Medium", reports: 14 },
  ],
  latestAssets: [
    { id: "asset-rock", name: "Rock_Cliff_01", image: "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=300&q=80" },
    { id: "asset-cabin", name: "Cabin_Wall_01", image: "https://images.unsplash.com/photo-1518005020951-eccb494ad742?w=300&q=80" },
    { id: "asset-forest", name: "Ambient_Forest", image: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&q=80" },
  ],
  focus: { title: "FPS Controller Package", department: "Game Development", label: "Next up" },
};
