import { ArrowUpRight, Settings } from "lucide-react";
import { useToast } from "../context/ToastContext";

const SECTIONS = [
  { title: "AI providers", detail: "Choose and configure model providers" },
  { title: "Integrations", detail: "Unity, GitHub, MCP servers and external APIs" },
  { title: "Permissions", detail: "Approval rules and action boundaries" },
  { title: "Appearance", detail: "Branding, theme and interface preferences" },
];

/** `/settings` — studio settings (not yet functional). */
export function SettingsPage() {
  const notify = useToast();
  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">BOOSKI STUDIOS</span>
        <h1>Settings</h1>
        <p>Configure AI providers, integrations, permissions, notifications and studio preferences.</p>
      </div>
      <div className="utility-grid">
        {SECTIONS.map((s) => (
          <button type="button" className="panel utility-card" key={s.title} onClick={() => notify(`${s.title} will be configured when the backend is connected.`)}>
            <span className="work-icon"><Settings size={19} aria-hidden="true" /></span>
            <b>{s.title}</b>
            <small>{s.detail}</small>
            <ArrowUpRight size={16} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
