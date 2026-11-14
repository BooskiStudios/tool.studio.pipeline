import type { ReactNode } from "react";
import { Search, type LucideIcon } from "lucide-react";
import type { Resource } from "../hooks/useResource";
import { SourceChip } from "./ui";

/**
 * Standard heading for studio pages. `source` says where the page's data comes from: Booski Core
 * (`live`), or illustrative preview content for a capability planned for a later phase (`planned`).
 */
export function PageHeading({ eyebrow, title, description, source, actions }: {
  eyebrow: string;
  title: string;
  description: string;
  source: "live" | "planned";
  actions?: ReactNode;
}) {
  return (
    <div className="simple-page-heading page-heading-row">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
        <SourceChip source={source} />
      </div>
      {actions && <div className="page-heading-actions">{actions}</div>}
    </div>
  );
}

/** Centred placeholder used for empty lists and not-yet-built areas. */
export function EmptyState({ icon: IconComponent, title, children, action }: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-work">
      <IconComponent size={27} aria-hidden="true" />
      <b>{title}</b>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

/** Renders loading / error states for a `useResource` result, and `children(data)` once ready. */
export function ResourceView<T>({ resource, label, children }: {
  resource: Resource<T>;
  label: string;
  children: (data: T) => ReactNode;
}) {
  if (resource.status === "loading") {
    return <div className="resource-state" role="status">Loading {label}…</div>;
  }
  if (resource.status === "error") {
    return <div className="resource-state resource-error" role="alert">Couldn’t load {label}: {resource.error.message}</div>;
  }
  return <>{children(resource.data)}</>;
}

/** The search box styling shared by workspace, library and template pages. */
export function SearchField({ value, onChange, placeholder, label }: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  /** Accessible label; defaults to the placeholder. */
  label?: string;
}) {
  return (
    <div className="workspace-search">
      <Search size={16} aria-hidden="true" />
      <input
        role="searchbox"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={label ?? placeholder}
      />
    </div>
  );
}

/** Case-insensitive "contains" match across several fields. */
export function matchesQuery(query: string, ...fields: string[]): boolean {
  const q = query.trim().toLowerCase();
  return !q || fields.some((f) => f.toLowerCase().includes(q));
}
