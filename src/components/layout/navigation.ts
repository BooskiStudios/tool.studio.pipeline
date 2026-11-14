import {
  BookOpen, Bot, Box, ClipboardList, Clock3, Compass, FileImage, Gauge, Network, Search, Settings, ShieldCheck, type LucideIcon,
} from "lucide-react";
import { paths } from "../../routes";

export interface NavEntry {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Only highlight on an exact URL match (needed for "/"). */
  end?: boolean;
  /** Shown as a preview of a later phase rather than live data. */
  planned?: boolean;
}

/** Departments are listed between these two entries, from Booski Core (see Sidebar). */
export const homeNav: NavEntry = { label: "Home", to: paths.home, icon: Compass, end: true };
export const operationsNav: NavEntry = { label: "Studio Operations", to: paths.operations, icon: Settings };

export const knowledgeNav: NavEntry[] = [
  { label: "Game Library", to: paths.library, icon: Box },
  { label: "Research", to: paths.research, icon: Search },
  { label: "Templates", to: paths.templates, icon: FileImage },
];

export const studioSystemsNav: NavEntry[] = [
  { label: "Agent Management", to: paths.agents, icon: Bot, planned: true },
  { label: "Cost & Usage", to: paths.costUsage, icon: Gauge, planned: true },
  { label: "Decision Log", to: paths.decisions, icon: ClipboardList },
  { label: "Approvals Centre", to: paths.approvals, icon: ShieldCheck },
  { label: "Integrations Hub", to: paths.integrations, icon: Network, planned: true },
  { label: "Studio Knowledge", to: paths.knowledge, icon: BookOpen },
  { label: "Activity & Audit", to: paths.activity, icon: Clock3 },
];
