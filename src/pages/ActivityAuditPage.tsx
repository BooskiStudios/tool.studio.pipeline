import { useState } from "react";
import { useActivity, useMembers, useProjectList } from "../api/hooks";
import { ActivityList, entityLabel } from "../components/ActivityList";
import { PageHeading } from "../components/common";
import { LoadMore, QueryView, RefreshingHint } from "../components/ui";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const ENTITY_TYPES = ["project", "task", "milestone", "workstream", "document", "decision", "approval", "department", "membership", "workspace"];

/** `/activity` — the workspace's permanent activity record, newest first. */
export function ActivityAuditPage() {
  const { can } = useWorkspace();
  const projects = useProjectList();
  const members = useMembers();
  const [project, setProject] = useState("");
  const [entityType, setEntityType] = useState("");
  const [actor, setActor] = useState("");
  const [since, setSince] = useState("");
  const activity = useActivity({
    project: project || undefined,
    entity_type: entityType || undefined,
    actor: actor || undefined,
    since: since ? new Date(`${since}T00:00:00`).toISOString() : undefined,
  });
  const types = can("audit.read") ? [...ENTITY_TYPES, "invitation"] : ENTITY_TYPES;

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI STUDIOS / TRACEABILITY"
        title="Activity & Audit"
        description="A permanent, append-only record of who changed what and when. Entries can't be edited or deleted."
        source="live"
      />
      <div className="panel audit-list">
        <div className="filter-bar" role="search" aria-label="Filter activity">
          <select value={project} onChange={(e) => setProject(e.target.value)} aria-label="Project">
            <option value="">All projects</option>
            {(projects.data ?? []).map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
          <select value={entityType} onChange={(e) => setEntityType(e.target.value)} aria-label="Record type">
            <option value="">All record types</option>
            {types.map((t) => <option key={t} value={t}>{entityLabel(t)}</option>)}
          </select>
          <select value={actor} onChange={(e) => setActor(e.target.value)} aria-label="Person">
            <option value="">Everyone</option>
            {(members.data ?? []).map((m) => <option key={m.user_id} value={m.user_id}>{m.display_name}</option>)}
          </select>
          <label className="check-label">
            Since <input type="date" value={since} onChange={(e) => setSince(e.target.value)} aria-label="Since date" />
          </label>
          <RefreshingHint active={activity.isFetching && !activity.isPending && !activity.isFetchingNextPage} />
        </div>
        <QueryView query={activity} label="activity">
          {() => (
            <>
              <ActivityList events={activity.items} emptyText="No activity matches these filters." />
              <LoadMore {...activity} />
            </>
          )}
        </QueryView>
      </div>
      <p className="small-note">
        You see activity for the projects you can access. Restricted projects' history is only shown to their members, owners and admins
        {can("audit.read") ? "" : "; invitation records are visible to owners and admins"}.
      </p>
    </div>
  );
}
