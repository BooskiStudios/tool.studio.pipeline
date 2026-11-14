import {
  BookOpen, Bot, Box, ClipboardList, Clock3, Compass, FileImage, Gamepad2, Gauge, Image, Lightbulb,
  Megaphone, MessageCircle, Network, Search, Settings, ShieldCheck, type LucideIcon,
} from "lucide-react";
import { paths } from "../../routes";
import type { DepartmentSlug } from "../../types";

export interface NavEntry {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Only highlight on an exact URL match (needed for "/"). */
  end?: boolean;
}

/** Department names by slug. Used for navigation and for labelling tasks created inside a department. */
export const departmentNames: Record<DepartmentSlug, string> = {
  "concept-lab": "Concept Lab",
  "game-development": "Game Development",
  "asset-production": "Asset Production",
  "marketing-studio": "Marketing Studio",
  "post-launch-intelligence": "Post-Launch Intelligence",
};

const departmentIcons: Record<DepartmentSlug, LucideIcon> = {
  "concept-lab": Lightbulb,
  "game-development": Gamepad2,
  "asset-production": Image,
  "marketing-studio": Megaphone,
  "post-launch-intelligence": MessageCircle,
};

export const primaryNav: NavEntry[] = [
  { label: "Home", to: paths.home, icon: Compass, end: true },
  ...(Object.keys(departmentNames) as DepartmentSlug[]).map((slug) => ({
    label: departmentNames[slug],
    to: paths.department(slug),
    icon: departmentIcons[slug],
  })),
  { label: "Studio Operations", to: paths.operations, icon: Settings },
];

export const knowledgeNav: NavEntry[] = [
  { label: "Game Library", to: paths.library, icon: Box },
  { label: "Research", to: paths.research, icon: Search },
  { label: "Templates", to: paths.templates, icon: FileImage },
];

export const studioSystemsNav: NavEntry[] = [
  { label: "Agent Management", to: paths.agents, icon: Bot },
  { label: "Cost & Usage", to: paths.costUsage, icon: Gauge },
  { label: "Decision Log", to: paths.decisions, icon: ClipboardList },
  { label: "Approvals Centre", to: paths.approvals, icon: ShieldCheck },
  { label: "Integrations Hub", to: paths.integrations, icon: Network },
  { label: "Studio Knowledge", to: paths.knowledge, icon: BookOpen },
  { label: "Activity & Audit", to: paths.activity, icon: Clock3 },
];
