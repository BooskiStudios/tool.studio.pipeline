import { Link } from "react-router";
import { Clock3 } from "lucide-react";
import { useMemberNames, useProjectIndex } from "../api/hooks";
import type { ActivityEvent } from "../api/types";
import { formatDateTime, timeAgo } from "../lib/format";
import { paths, recordLinks } from "../routes";
import { EmptyState } from "./common";

const ENTITY_LABELS: Record<string, string> = {
  task: "Task",
  project: "Project",
  milestone: "Milestone",
  workstream: "Workstream",
  document: "Document",
  decision: "Decision",
  approval: "Approval",
  department: "Department",
  invitation: "Invitation",
  membership: "Membership",
  workspace: "Workspace",
};

export function entityLabel(type: string): string {
  return ENTITY_LABELS[type] ?? type.charAt(0).toUpperCase() + type.slice(1);
}

/** Where an event's record can be opened, if it's something with a page. */
function entityLink(event: ActivityEvent, projectSlug: string | undefined): string | null {
  if (!event.entity_id) return null;
  switch (event.entity_type) {
    case "task":
      return recordLinks.task(event.entity_id);
    case "document":
      return recordLinks.document(event.entity_id);
    case "decision":
      return recordLinks.decision(event.entity_id);
    case "approval":
      return recordLinks.approval(event.entity_id);
    case "project":
    case "milestone":
    case "workstream":
      return projectSlug ? paths.project(projectSlug) : null;
    default:
      return null;
  }
}

/** A list of activity events: who did what, when, with a link to the record where there is one. */
export function ActivityList({ events, emptyText = "Nothing has happened here yet." }: { events: ActivityEvent[]; emptyText?: string }) {
  const nameOf = useMemberNames();
  const projects = useProjectIndex();
  if (events.length === 0) return <EmptyState icon={Clock3} title="No activity">{emptyText}</EmptyState>;
  return (
    <div className="audit-list-rows">
      {events.map((event) => {
        const actor = event.actor_type === "system" ? "Booski Core" : nameOf(event.actor_user_id) ?? "Former member";
        // Projects you can't see are never named (their events don't reach you anyway).
        const project = event.project_id ? projects.get(event.project_id) : undefined;
        const link = entityLink(event, project?.slug);
        return (
          <div className="audit-row" key={event.id} data-testid="activity-row">
            <span className="audit-mark"><Clock3 size={16} aria-hidden="true" /></span>
            <div>
              {link ? <Link to={link} className="audit-link"><b>{event.summary}</b></Link> : <b>{event.summary}</b>}
              <small>
                {actor} · {entityLabel(event.entity_type)}
                {project ? ` · ${project.name}` : ""}
              </small>
            </div>
            <time dateTime={event.created_at} title={formatDateTime(event.created_at)}>{timeAgo(event.created_at)}</time>
          </div>
        );
      })}
    </div>
  );
}
