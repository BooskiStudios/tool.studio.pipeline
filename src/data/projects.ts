import type { Project, ProjectReference, Task } from "../types";

/** DEMO DATA — illustrative projects. Not persisted anywhere. */
export const demoProjects: Project[] = [
  {
    slug: "project-horizon",
    name: "Project Horizon",
    type: "Open World Survival",
    status: "Prototype",
    color: "cyan",
    image: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=700&q=85",
    progress: 43,
    engine: "Unity",
    description: "Open world survival adventure set in a post-collapse coastal region.",
  },
  {
    slug: "dead-frequency",
    name: "Dead Frequency",
    type: "Psychological Horror",
    status: "Pre-production",
    color: "red",
    image: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=700&q=85",
    progress: 18,
    engine: "Unity",
    description: "A psychological horror experience built around sound, isolation and unreliable perception.",
  },
  {
    slug: "neon-drift",
    name: "Neon Drift",
    type: "Racing Prototype",
    status: "Prototype",
    color: "purple",
    image: "https://images.unsplash.com/photo-1519608487953-e999c86e7455?w=700&q=85",
    progress: 27,
    engine: "Unity",
    description: "A high-speed arcade racing prototype with expressive handling and neon environments.",
  },
];

/** DEMO DATA — Reference Vault entries. Currently shared by every project. */
export const demoProjectReferences: ProjectReference[] = [
  { id: "ref-visual", title: "Visual direction", detail: "Low-poly abandoned research facility environment", source: "AI discovered" },
  { id: "ref-gameplay", title: "Gameplay inspiration", detail: "First-person exploration and interaction reference", source: "User saved" },
  { id: "ref-lighting", title: "Lighting reference", detail: "Atmospheric corridor lighting and fog", source: "AI discovered" },
];

/** DEMO DATA — the starting task list for a browser session. */
export const demoTasks: Task[] = [
  { id: "task-1", title: "Review controller movement architecture", department: "Game Development", priority: "High", done: false },
  { id: "task-2", title: "Test sprint stamina tuning", department: "Game Development", priority: "Medium", done: false },
  { id: "task-3", title: "Document camera polish settings", department: "Game Development", priority: "Low", done: true },
  { id: "task-4", title: "Prepare environment asset references", department: "Asset Production", priority: "Medium", done: true },
];
