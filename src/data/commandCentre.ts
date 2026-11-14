import type { CommandCentrePreview } from "../types";

/**
 * PREVIEW DATA — the Command Centre panels for capabilities that arrive in later phases (AI workforce,
 * productivity insights, player feedback, generated assets). They are shown with a "preview" label;
 * everything else on the Command Centre comes from Booski Core.
 */
export const commandCentrePreview: CommandCentrePreview = {
  workforce: [
    { name: "Orchestrator", status: "Coordinating", icon: "network" },
    { name: "Research Agent", status: "Working", icon: "search" },
    { name: "Unity Agent", status: "Working", icon: "code" },
    { name: "Asset Agent", status: "Available", icon: "box" },
    { name: "Marketing Agent", status: "Available", icon: "megaphone" },
    { name: "Quality Agent", status: "Reviewing", icon: "shield" },
  ],
  insights: [
    { label: "Ideas Explored", value: "12", change: "+33%" },
    { label: "Assets Generated", value: "84", change: "+120%" },
    { label: "Hours Saved", value: "38", change: "+45%" },
    { label: "Content Created", value: "24", change: "+80%" },
  ],
  productivityChange: "+120%",
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
};
