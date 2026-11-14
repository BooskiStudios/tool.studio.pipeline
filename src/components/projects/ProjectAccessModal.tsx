import { useState } from "react";
import { Trash2, UserPlus } from "lucide-react";
import * as core from "../../api/core";
import { useMembers, useProjectMembers, useWorkspaceMutation } from "../../api/hooks";
import type { Project, ProjectAccess } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { ROLE_LABELS } from "../../workspace/roles";
import { Modal } from "../Modal";
import { FormError, QueryView } from "../ui";

/**
 * Who can see a restricted project (owners and admins always can). "Viewer" access is read-only;
 * "contributor" access lets people work in the project up to what their workspace role allows. Project
 * access can only narrow a role, never widen it.
 */
export function ProjectAccessModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const notify = useToast();
  const access = useProjectMembers(project.slug);
  const members = useMembers();
  const [userId, setUserId] = useState("");
  const [level, setLevel] = useState<ProjectAccess>("contributor");
  const setMember = useWorkspaceMutation((ws, vars: { userId: string; access: ProjectAccess }) =>
    core.projects.setMember(ws, project.slug, vars.userId, vars.access),
  );
  const remove = useWorkspaceMutation((ws, memberId: string) => core.projects.removeMember(ws, project.slug, memberId));
  const listed = new Set((access.data ?? []).map((m) => m.user_id));
  const candidates = (members.data ?? []).filter((m) => !listed.has(m.user_id) && m.role !== "owner" && m.role !== "admin");

  return (
    <Modal
      eyebrow="PROJECT ACCESS"
      title={`Who can see ${project.name}`}
      description={
        project.visibility === "restricted"
          ? "This project is restricted: besides owners and admins, only the people listed here can see it."
          : "This project is visible to the whole workspace. Viewer access below still makes it read-only for that person."
      }
      onClose={onClose}
      size="wide"
    >
      <QueryView query={access} label="project access">
        {(rows) => (
          <div className="member-table">
            {rows.length === 0 && <p className="muted-text">Nobody is on the access list yet.</p>}
            {rows.map((m) => (
              <div className="member-row" key={m.user_id}>
                <span>
                  <b>{m.display_name}</b>
                  <small>{m.email}</small>
                </span>
                <select
                  value={m.access}
                  aria-label={`Access for ${m.display_name}`}
                  onChange={(e) => setMember.mutate({ userId: m.user_id, access: e.target.value as ProjectAccess })}
                >
                  <option value="viewer">Viewer (read-only)</option>
                  <option value="contributor">Contributor</option>
                </select>
                <button
                  type="button"
                  className="icon-only"
                  aria-label={`Remove ${m.display_name}`}
                  onClick={() => remove.mutate(m.user_id, { onSuccess: () => notify(`${m.display_name} removed from ${project.name}.`) })}
                >
                  <Trash2 size={13} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        )}
      </QueryView>
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (userId) setMember.mutate({ userId, access: level }, { onSuccess: () => setUserId("") });
        }}
      >
        <select value={userId} onChange={(e) => setUserId(e.target.value)} aria-label="Person to add">
          <option value="">Add a workspace member…</option>
          {candidates.map((m) => <option key={m.user_id} value={m.user_id}>{m.display_name} · {ROLE_LABELS[m.role]}</option>)}
        </select>
        <select value={level} onChange={(e) => setLevel(e.target.value as ProjectAccess)} aria-label="Access level">
          <option value="contributor">Contributor</option>
          <option value="viewer">Viewer (read-only)</option>
        </select>
        <button type="submit" className="primary-btn" disabled={!userId || setMember.isPending}>
          <UserPlus size={13} aria-hidden="true" /> Add
        </button>
      </form>
      <FormError error={setMember.error ?? remove.error} />
    </Modal>
  );
}
