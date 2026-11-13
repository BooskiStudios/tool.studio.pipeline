import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowUpRight, Bot, ChevronRight, Layers, Plus, SearchX, Settings } from "lucide-react";
import { DecisionLogList } from "../components/DecisionLogList";
import { EmptyState, matchesQuery, ResourceView, SearchField } from "../components/common";
import { Icon } from "../components/Icon";
import { useProjects } from "../context/ProjectContext";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { paths } from "../routes";
import { studioApi } from "../services";
import type { DepartmentWorkspace } from "../types";
import { NotFoundPage } from "./NotFoundPage";

const DECISION_LOG_TAB = "Decision Log";

function DepartmentWorkspaceView({ workspace }: { workspace: DepartmentWorkspace }) {
  const { department, tabs, actions, items, queue, tabDescriptions } = workspace;
  const navigate = useNavigate();
  const notify = useToast();
  const { currentProject } = useProjects();
  const [tab, setTab] = useState(tabs[0]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const name = department.name;
  const filtered = items.filter((x) => matchesQuery(query, x.title));

  const renderTab = () => {
    if (tab === tabs[1]) {
      return queue.map((q) => (
        <div className="queue-item" key={q.id}>
          <div className="queue-priority">
            <span className={`severity ${q.priority.toLowerCase()}`}>{q.priority}</span>
            <small>{q.owner}</small>
          </div>
          <div className="queue-copy">
            <b>{q.title}</b>
            <small>{q.detail}</small>
          </div>
          <button type="button" onClick={() => notify(`Queue item selected: ${q.title}`)} aria-label={`Select ${q.title}`}>
            <ChevronRight size={17} aria-hidden="true" />
          </button>
        </div>
      ));
    }
    if (tab === DECISION_LOG_TAB) return <DecisionLogList initialDepartment={name} embedded />;
    if (tab === tabs[0]) {
      return (
        <>
          <SearchField value={query} onChange={setQuery} placeholder={`Search ${name.toLowerCase()}...`} />
          {filtered.length === 0 && (
            <EmptyState icon={SearchX} title="No matching work">Nothing in {tab.toLowerCase()} matches “{query}”.</EmptyState>
          )}
          {filtered.map((w) => (
            <button
              type="button"
              className={`work-item ${selected === w.title ? "selected-work" : ""}`}
              key={w.id}
              onClick={() => setSelected(selected === w.title ? "" : w.title)}
              aria-pressed={selected === w.title}
            >
              <span className="work-icon"><Icon name={w.icon} size={19} /></span>
              <span className="work-copy">
                <b>{w.title}</b>
                <small>{w.detail}</small>
              </span>
              <span className="work-status">{w.status}</span>
              <ChevronRight size={17} aria-hidden="true" />
            </button>
          ))}
        </>
      );
    }
    return (
      <EmptyState
        icon={Layers}
        title={tab}
        action={<button type="button" className="secondary-btn" onClick={() => notify(`${tab} tools will be connected in a later phase.`)}>Explore {tab}</button>}
      >
        {tabDescriptions[tab] ?? "Department records and supporting information will appear here."}
      </EmptyState>
    );
  };

  return (
    <div className="workspace-page">
      <div
        className={`workspace-hero ${department.color}`}
        style={{ backgroundImage: `linear-gradient(90deg,rgba(4,12,22,.96),rgba(4,12,22,.72),rgba(4,12,22,.28)),url(${department.image})` }}
      >
        <div className="workspace-hero-top">
          <span className="eyebrow">BOOSKI STUDIOS / DEPARTMENTS</span>
          <span className="demo-chip">DEMO WORKSPACE</span>
        </div>
        <div className="workspace-heading">
          <div className="workspace-icon"><Icon name={department.icon} size={30} /></div>
          <div>
            <h1>{name}</h1>
            <p>{department.desc}</p>
          </div>
        </div>
        <div className="workspace-actions">
          {actions.map((a, i) => (
            <button type="button" key={a} className={i === 0 ? "primary-btn" : "secondary-btn"} onClick={() => notify(`${a} will be connected to Booski AI Core in a later phase.`)}>
              {i === 0 ? <Plus size={15} aria-hidden="true" /> : <ArrowUpRight size={15} aria-hidden="true" />} {a}
            </button>
          ))}
        </div>
      </div>

      <div className="workspace-tabs" role="group" aria-label={`${name} sections`}>
        {tabs.map((t) => (
          <button
            type="button"
            aria-pressed={tab === t}
            className={tab === t ? "active-tab" : ""}
            key={t}
            onClick={() => {
              setTab(t);
              setSelected("");
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="workspace-stats">
        <div><small>Department</small><b>{name}</b></div>
        <div><small>Current project context</small><b>{currentProject?.name ?? "—"}</b></div>
        <div><small>Workspace pulse</small><b className="green-text">Ready for setup</b></div>
        <div><small>Department overview</small><b>{department.metric}</b></div>
      </div>

      <div className="workspace-content-grid">
        <section className="panel workspace-main" aria-label={tab}>
          <div className="panel-title">
            <h2>{tab}</h2>
            <span className="demo-label">{tab === tabs[1] ? "QUEUED WORK" : "SAMPLE CONTENT"}</span>
          </div>
          {renderTab()}
          {selected && (
            <div className="selected-detail">
              <b>{selected}</b>
              <p>Demonstration item. Its full brief, linked files, history and AI recommendations will be available when connected to the backend.</p>
              <button type="button" onClick={() => notify(`Opened demo item: ${selected}`)}>Open details <ArrowUpRight size={14} aria-hidden="true" /></button>
            </div>
          )}
        </section>
        <aside className="panel workspace-side">
          <div className="panel-title"><h2>Department controls</h2></div>
          <button type="button" className="quick-action" onClick={() => notify("New work item will be created through Booski Core.")}>
            <Plus size={15} aria-hidden="true" /> Create new work
          </button>
          <button type="button" className="quick-action" onClick={() => notify("Agent assignment will be available after orchestration is connected.")}>
            <Bot size={15} aria-hidden="true" /> Assign AI agent
          </button>
          <div className="side-divider" />
          <div className="panel-title"><h2>Department status</h2></div>
          <div className="status-line"><span>Workspace</span><b className="green-text">Initialised</b></div>
          <div className="status-line"><span>AI integration</span><b className="muted-text">Not connected</b></div>
          <div className="status-line"><span>Data source</span><b className="muted-text">Demo content</b></div>
          <button type="button" className="outline-wide" onClick={() => navigate(paths.settings)}>
            <Settings size={14} aria-hidden="true" /> Configure integrations
          </button>
        </aside>
      </div>
    </div>
  );
}

/** `/departments/:departmentSlug` — a department workspace. */
export function DepartmentPage() {
  const { departmentSlug = "" } = useParams();
  const workspace = useResource(() => studioApi.getDepartmentWorkspace(departmentSlug), [departmentSlug]);
  return (
    <ResourceView resource={workspace} label="this department">
      {(data) => (data ? <DepartmentWorkspaceView workspace={data} /> : <NotFoundPage />)}
    </ResourceView>
  );
}
