import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useMatch, useNavigate } from "react-router";
import { Check, ChevronRight, Lock, LogOut, Plus, Settings } from "lucide-react";
import logo from "../../assets/booski-logo.png";
import { useDepartments } from "../../api/hooks";
import { useAuth, useMe } from "../../auth/AuthProvider";
import { NAV_HIDDEN_DEPARTMENTS } from "../../config/departments";
import { useProjects } from "../../context/ProjectContext";
import { projectImage } from "../../lib/format";
import { paths } from "../../routes";
import { ROLE_LABELS } from "../../workspace/roles";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { Icon } from "../Icon";
import { homeNav, knowledgeNav, operationsNav, studioSystemsNav, type NavEntry } from "./navigation";

function SecondaryLinks({ title, entries, className }: { title: string; entries: NavEntry[]; className: string }) {
  return (
    <nav className={`side-section ${className}`} aria-label={title}>
      <div className="section-heading">{title.toUpperCase()}</div>
      {entries.map(({ label, to, icon: NavIcon, planned }) => (
        <NavLink key={to} to={to} className={({ isActive }) => `knowledge-link ${isActive ? "selected-knowledge" : ""}`}>
          <NavIcon size={16} aria-hidden="true" />
          {label}
          {planned && <span className="nav-planned" title="Preview of a later phase">preview</span>}
        </NavLink>
      ))}
    </nav>
  );
}

function PrimaryLink({ entry, iconNode }: { entry: NavEntry | { label: string; to: string; end?: boolean }; iconNode: ReactNode }) {
  return (
    <NavLink to={entry.to} end={entry.end} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
      {({ isActive }) => (
        <>
          {iconNode}
          <span>{entry.label}</span>
          {isActive && <ChevronRight size={15} className="nav-chevron" aria-hidden="true" />}
        </>
      )}
    </NavLink>
  );
}

/** The signed-in person, their role, the active workspace, switching workspace and signing out. */
function ProfileMenu() {
  const me = useMe();
  const { logout } = useAuth();
  const { name, role, slug, memberships, switchWorkspace } = useWorkspace();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const initials = me.user.display_name.split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div className="profile-wrap" ref={ref}>
      {open && (
        <div className="profile-menu" id={menuId} role="menu" aria-label="Account and workspace">
          <div className="profile-menu-head">
            <b>{me.user.display_name}</b>
            <small>{me.user.email}</small>
          </div>
          <div className="section-heading">WORKSPACES</div>
          {memberships.map((m) => (
            <button
              type="button"
              role="menuitemradio"
              aria-checked={m.workspace_slug === slug}
              key={m.workspace_id}
              onClick={() => {
                setOpen(false);
                switchWorkspace(m.workspace_slug);
              }}
            >
              <span>
                <b>{m.workspace_name}</b>
                <small>{ROLE_LABELS[m.role]}</small>
              </span>
              {m.workspace_slug === slug && <Check size={14} aria-hidden="true" />}
            </button>
          ))}
          <div className="side-divider" />
          <button type="button" role="menuitem" onClick={() => { setOpen(false); navigate(paths.settings); }}>
            <span><b>Settings</b></span>
            <Settings size={14} aria-hidden="true" />
          </button>
          <button type="button" role="menuitem" onClick={() => void logout()}>
            <span><b>Sign out</b></span>
            <LogOut size={14} aria-hidden="true" />
          </button>
        </div>
      )}
      <button
        type="button"
        className="profile"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={`${me.user.display_name}, ${ROLE_LABELS[role]} in ${name}. Open account menu`}
        onClick={() => setOpen((o) => !o)}
      >
        <div className="avatar" aria-hidden="true">{initials || "♛"}</div>
        <span>
          <b>{me.user.display_name}</b>
          <small>{ROLE_LABELS[role]} · {name}</small>
        </span>
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}

export function Sidebar({ onNewProject }: { onNewProject: () => void }) {
  const { projects, error } = useProjects();
  const { can } = useWorkspace();
  const departments = useDepartments();
  // A project is highlighted only while its own workspace is open.
  const openProjectSlug = useMatch("/projects/:projectSlug")?.params.projectSlug;
  const visibleDepartments = (departments.data ?? []).filter((d) => !d.archived_at && !NAV_HIDDEN_DEPARTMENTS.has(d.slug));
  const HomeIcon = homeNav.icon;
  const OpsIcon = operationsNav.icon;

  return (
    <aside className="sidebar">
      <div className="sidebar-scroll">
        <div className="brand">
          <img className="brand-logo" src={logo} alt="Booski Studios" />
        </div>

        <nav className="primary-nav" aria-label="Primary">
          <PrimaryLink entry={homeNav} iconNode={<HomeIcon size={18} aria-hidden="true" />} />
          {visibleDepartments.map((d) => (
            <PrimaryLink key={d.id} entry={{ label: d.name, to: paths.department(d.slug) }} iconNode={<Icon name={d.icon_key} size={18} />} />
          ))}
          <PrimaryLink entry={operationsNav} iconNode={<OpsIcon size={18} aria-hidden="true" />} />
        </nav>

        <nav className="side-section" aria-label="Projects">
          <div className="section-heading">
            PROJECTS
            {can("projects.manage") && (
              <button type="button" onClick={onNewProject} aria-label="New project">
                <Plus size={16} aria-hidden="true" />
              </button>
            )}
          </div>
          {error ? <small className="side-note">Couldn't load projects.</small> : null}
          {projects?.length === 0 && <small className="side-note">No projects yet.</small>}
          {projects?.map((p) => (
            <Link
              key={p.id}
              to={paths.project(p.slug)}
              className={`project-link ${openProjectSlug === p.slug ? "selected" : ""}`}
              aria-current={openProjectSlug === p.slug ? "page" : undefined}
            >
              <img src={projectImage(p)} alt="" />
              <span>
                <b>{p.name} {p.visibility === "restricted" && <Lock size={10} aria-label="Restricted" />}</b>
                <small>{p.project_type || "Project"}</small>
              </span>
            </Link>
          ))}
        </nav>

        <SecondaryLinks title="Knowledge" entries={knowledgeNav} className="knowledge" />
        <SecondaryLinks title="Studio Systems" entries={studioSystemsNav} className="studio-tools" />
      </div>

      <ProfileMenu />
    </aside>
  );
}
