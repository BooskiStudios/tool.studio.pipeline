import {
  AudioLines, Bot, Box, Bug, CalendarDays, Clapperboard, Code2, FileImage, FileText, FlaskConical,
  FolderKanban, Gamepad2, Gauge, Image, Lightbulb, Megaphone, MessageCircle, Network, Palette, Search,
  ShieldCheck, Star, Workflow, type LucideIcon, type LucideProps,
} from "lucide-react";
import type { IconKey } from "../types";

/**
 * Maps data-friendly icon keys to Lucide components, so data records (and a
 * future API) can name an icon without importing React components.
 */
const icons: Record<IconKey, LucideIcon> = {
  lightbulb: Lightbulb,
  gamepad: Gamepad2,
  image: Image,
  megaphone: Megaphone,
  message: MessageCircle,
  flask: FlaskConical,
  search: Search,
  folder: FolderKanban,
  code: Code2,
  box: Box,
  audio: AudioLines,
  palette: Palette,
  "file-text": FileText,
  clapperboard: Clapperboard,
  calendar: CalendarDays,
  bug: Bug,
  gauge: Gauge,
  star: Star,
  "file-image": FileImage,
  network: Network,
  shield: ShieldCheck,
  bot: Bot,
  workflow: Workflow,
};

export function Icon({ name, ...props }: { name: IconKey } & LucideProps) {
  const Component = icons[name];
  return <Component aria-hidden="true" {...props} />;
}
