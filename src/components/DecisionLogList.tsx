import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { ChevronRight, ClipboardList, GitBranch, Pencil, Plus } from "lucide-react";
import * as core from "../api/core";
import {
  useDecisionHistory, useDecisionList, useDepartments, useMemberNames, useProjectIndex,
} from "../api/hooks";
import type { DecisionStatus } from "../api/types";
import { useQuery } from "@tanstack/react-query";
import { DECISION_STATUS, formatDate, formatDateTime } from "../lib/format";
import { recordLinks } from "../routes";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { ActivityList } from "./ActivityList";
import { EmptyState } from "./common";
import { DecisionFormModal, type DecisionDefaults } from "./decisions/DecisionFormModal";
import { Modal } from "./Modal";
import { LoadMore, QueryView, RefreshingHint } from "./ui";

function DecisionDetail({ decisionId, onClose, onOpen }: { decisionId: string; onClose: () => void; onOpen: (id: string) => void }) {
  const { slug, can } = useWorkspace();
  const decision = useQuery({
    queryKey: ["ws", slug, "decision", decisionId],
    queryFn: ({ signal }) => core.decisions.get(slug, decisionId, signal),
  });
  const history = useDecisionHistory(decisionId);
  const nameOf = useMemberNames();
  const projects = useProjectIndex();
  const departments = useDepartments();
  const [editing, setEditing] = useState(false);
  const [superseding, setSuperseding] = useState(false);

  if (decision.data && editing) return <DecisionFormModal decision={decision.data} onClose={() => setEditing(false)} />;
  if (decision.data && superseding) {
    return <DecisionFormModal defaults={{ supersedes: decision.data }} onClose={() => setSuperseding(false)} />;
  }

  return (
    <Modal eyebrow="DECISION LOG" title={decision.data?.title ?? "Decision"} onClose={onClose} size="wide">
      <QueryView query={decision} label="this decision">
        {(d) => {
          const project = d.project_id ? projects.get(d.project_id) : undefined;
          const canWrite = project ? project.capabilities.includes("decisions.write") : can("decisions.write");
          return (
            <>
              <div className="tags">
                <span>{DECISION_STATUS[d.status]}</span>
                <span>{project?.name ?? "Studio-wide"}</span>
                {d.department_id && <span>{departments.data?.find((x) => x.id === d.department_id)?.name}</span>}
              </div>
              <p className="document-meta">
                Recorded {formatDateTime(d.recorded_at)} by {nameOf(d.author_user_id) ?? "a former member"}
                {d.decided_at ? ` · decided ${formatDate(d.decided_at)}` : ""}
              </p>
              {d.superseded_by_decision_id && (
                <button type="button" className="inline-link" onClick={() => onOpen(d.superseded_by_decision_id ?? "")}>
                  Superseded by a later decision →
                </button>
              )}
              {d.supersedes_decision_id && (
                <button type="button" className="inline-link" onClick={() => onOpen(d.supersedes_decision_id ?? "")}>
                  ← Replaces an earlier decision
                </button>
              )}
              <dl className="decision-detail">
                <dt>Context</dt><dd>{d.context || "—"}</dd>
                <dt>Options considered</dt>
                <dd>
                  {d.options.length === 0 ? "—" : (
                    <ul>{d.options.map((o, i) => <li key={i}><b>{o.title}</b>{o.summary ? ` — ${o.summary}` : ""}</li>)}</ul>
                  )}
                </dd>
                <dt>Outcome</dt><dd>{d.outcome || "—"}</dd>
                <dt>Rationale</dt><dd>{d.rationale || "—"}</dd>
                <dt>Supporting documents</dt>
                <dd>
                  {d.document_ids.length === 0 ? "—" : (
                    <ul>{d.document_ids.map((id) => <li key={id}><Link to={recordLinks.document(id)}>Open document</Link></li>)}</ul>
                  )}
                </dd>
              </dl>
              <h3 className="section-title">History</h3>
              <QueryView query={history} label="decision history">
                {(page) => <ActivityList events={page.items} />}
              </QueryView>
              {canWrite && d.status !== "superseded" && (
                <div className="modal-actions">
                  <button type="button" className="secondary-btn" onClick={() => setSuperseding(true)}>
                    <GitBranch size={13} aria-hidden="true" /> Supersede
                  </button>
                  <button type="button" className="primary-btn" onClick={() => setEditing(true)}>
                    <Pencil size={13} aria-hidden="true" /> Edit
                  </button>
                </div>
              )}
            </>
          );
        }}
      </QueryView>
    </Modal>
  );
}

/**
 * The live Decision Log. Used on the Decision Log page (in a panel), inside department workspaces
 * (`department`) and project workspaces (`project`). `?decision=<id>` opens one.
 */
export function DecisionLogList({ department, project, embedded = false, defaults }: {
  department?: string;
  project?: string;
  embedded?: boolean;
  defaults?: DecisionDefaults;
}) {
  const { can } = useWorkspace();
  const departments = useDepartments();
  const projects = useProjectIndex();
  const nameOf = useMemberNames();
  const [departmentFilter, setDepartmentFilter] = useState(department ?? "");
  const [status, setStatus] = useState<DecisionStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [params, setParams] = useSearchParams();
  const openId = params.get("decision");
  const setOpen = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set("decision", id);
    else next.delete("decision");
    setParams(next, { replace: !id });
  };
  const decisions = useDecisionList({
    department: departmentFilter || undefined,
    project,
    status: status ? [status] : undefined,
  });

  const content = (
    <QueryView query={decisions} label="decisions">
      {() => (
        <>
          <div className="decision-toolbar">
            <span>
              {decisions.items.length}
              {decisions.hasNextPage ? "+" : ""} recorded {decisions.items.length === 1 ? "decision" : "decisions"}
              <RefreshingHint active={decisions.isFetching && !decisions.isFetchingNextPage} />
            </span>
            <span className="toolbar-controls">
              {!department && (
                <select value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)} aria-label="Filter decisions by department">
                  <option value="">All departments</option>
                  {(departments.data ?? []).map((d) => <option key={d.id} value={d.slug}>{d.name}</option>)}
                </select>
              )}
              <select value={status} onChange={(e) => setStatus(e.target.value as DecisionStatus | "")} aria-label="Filter decisions by status">
                <option value="">Any status</option>
                {(Object.keys(DECISION_STATUS) as DecisionStatus[]).map((s) => <option key={s} value={s}>{DECISION_STATUS[s]}</option>)}
              </select>
              {can("decisions.write") && (
                <button type="button" className="primary-btn" onClick={() => setCreating(true)}>
                  <Plus size={13} aria-hidden="true" /> Record decision
                </button>
              )}
            </span>
          </div>
          {decisions.items.length === 0 ? (
            <EmptyState icon={ClipboardList} title="No decisions recorded yet">
              Decisions will appear here once they are recorded.
            </EmptyState>
          ) : (
            decisions.items.map((r) => {
              const dept = departments.data?.find((d) => d.id === r.department_id);
              const proj = r.project_id ? projects.get(r.project_id) : undefined;
              return (
                <button type="button" className="decision-row" key={r.id} onClick={() => setOpen(r.id)} data-testid="decision-row">
                  <div className="decision-date">{formatDate(r.recorded_at)}</div>
                  <div className="decision-main">
                    <b>{r.title}</b>
                    <p>{r.outcome || r.rationale || r.context || "No outcome recorded yet."}</p>
                    <div className="decision-tags">
                      <span>{DECISION_STATUS[r.status]}</span>
                      <span>{dept?.name ?? "Studio-wide"}</span>
                      {proj && <span>{proj.name}</span>}
                      <span>{nameOf(r.author_user_id) ?? "Former member"}</span>
                    </div>
                  </div>
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              );
            })
          )}
          <LoadMore {...decisions} />
        </>
      )}
    </QueryView>
  );

  const departmentId = departments.data?.find((d) => d.slug === department)?.id;
  return (
    <div className={embedded ? "decision-embedded" : "panel decision-panel"}>
      {content}
      {creating && <DecisionFormModal defaults={{ department_id: departmentId, ...defaults }} onClose={() => setCreating(false)} />}
      {openId && <DecisionDetail key={openId} decisionId={openId} onClose={() => setOpen(null)} onOpen={setOpen} />}
    </div>
  );
}

