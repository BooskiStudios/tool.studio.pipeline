import { Link, NavLink, useMatch } from "react-router";
import { ChevronRight, Plus } from "lucide-react";
import logo from "../../assets/booski-logo.png";
import { useProjects } from "../../context/ProjectContext";
import { paths } from "../../routes";
import { knowledgeNav, primaryNav, studioSystemsNav, type NavEntry } from "./navigation";

function SecondaryLinks({ title, entries, className }: { title: string; entries: NavEntry[]; className: string }) {
  return (
    <nav className={`side-section ${className}`} aria-label={title}>
      <div className="section-heading">{title.toUpperCase()}</div>
      {entries.map(({ label, to, icon: NavIcon }) => (
        <NavLink key={to} to={to} className={({ isActive }) => `knowledge-link ${isActive ? "selected-knowledge" : ""}`}>
          <NavIcon size={16} aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function Sidebar({ onNewProject }: { onNewProject: () => void }) {
  const { projects } = useProjects();
  // A project is highlighted only while its own workspace is open.
  const openProjectSlug = useMatch("/projects/:projectSlug")?.params.projectSlug;

  return (
    <aside className="sidebar">
      <div className="sidebar-scroll">
        <div className="brand">
          <img className="brand-logo" src={logo} alt="Booski Studios" />
        </div>

        <nav className="primary-nav" aria-label="Primary">
          {primaryNav.map(({ label, to, icon: NavIcon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              {({ isActive }) => (
                <>
                  <NavIcon size={18} aria-hidden="true" />
                  <span>{label}</span>
                  {isActive && <ChevronRight size={15} className="nav-chevron" aria-hidden="true" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <nav className="side-section" aria-label="Projects">
          <div className="section-heading">
            PROJECTS
            <button type="button" onClick={onNewProject} aria-label="New project">
              <Plus size={16} aria-hidden="true" />
            </button>
          </div>
          {projects?.map((p) => (
            <Link
              key={p.slug}
              to={paths.project(p.slug)}
              className={`project-link ${openProjectSlug === p.slug ? "selected" : ""}`}
              aria-current={openProjectSlug === p.slug ? "page" : undefined}
            >
              <img src={p.image} alt="" />
              <span>
                <b>{p.name}</b>
                <small>{p.type}</small>
              </span>
            </Link>
          ))}
        </nav>

        <SecondaryLinks title="Knowledge" entries={knowledgeNav} className="knowledge" />
        <SecondaryLinks title="Studio Systems" entries={studioSystemsNav} className="studio-tools" />
      </div>

      <Link to={paths.settings} className="profile" aria-label="Booski, Solo Developer — open settings">
        <div className="avatar" aria-hidden="true">♛</div>
        <span>
          <b>Booski</b>
          <small>Solo Developer</small>
        </span>
        <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </aside>
  );
}
