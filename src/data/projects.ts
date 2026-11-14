import type { ProjectReference } from "../types";

/**
 * PREVIEW DATA — example Reference Vault entries. Collecting references (images, links, AI-discovered
 * material) needs file storage and AI research, which arrive in later phases. Shown with a preview label.
 */
export const previewProjectReferences: ProjectReference[] = [
  { id: "ref-visual", title: "Visual direction", detail: "Low-poly abandoned research facility environment", source: "AI discovered" },
  { id: "ref-gameplay", title: "Gameplay inspiration", detail: "First-person exploration and interaction reference", source: "User saved" },
  { id: "ref-lighting", title: "Lighting reference", detail: "Atmospheric corridor lighting and fog", source: "AI discovered" },
];
