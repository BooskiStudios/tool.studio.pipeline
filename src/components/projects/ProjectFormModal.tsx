import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { isApiError } from "../../api/client";
import * as core from "../../api/core";
import { useWorkspaceMutation } from "../../api/hooks";
import type { AccentColor, Project, ProjectInput, ProjectStatus, ProjectVisibility } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { ACCENT_COLORS, PROJECT_STATUS, slugify } from "../../lib/format";
import { paths } from "../../routes";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { Modal } from "../Modal";
import { ConflictNotice, Field, FormError } from "../ui";

/** Create a project, or edit one (owners and admins). The address (slug) is permanent once created. */
export function ProjectFormModal({ project, onClose }: { project?: Project; onClose: () => void }) {
  const { slug: workspaceSlug } = useWorkspace();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const notify = useToast();
  const [name, setName] = useState(project?.name ?? "");
  const [slug, setSlug] = useState(project?.slug ?? "");
  const [slugTouched, setSlugTouched] = useState(Boolean(project));
  const [description, setDescription] = useState(project?.description ?? "");
  const [projectType, setProjectType] = useState(project?.project_type ?? "");
  const [engine, setEngine] = useState(project?.engine ?? "");
  const [status, setStatus] = useState<ProjectStatus>(project?.status ?? "concept");
  const [visibility, setVisibility] = useState<ProjectVisibility>(project?.visibility ?? "workspace");
  const [accent, setAccent] = useState<AccentColor>(project?.accent_color ?? "cyan");
  const [cover, setCover] = useState(project?.cover_image_url ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  const save = useWorkspaceMutation((ws, input: ProjectInput) =>
    project ? core.projects.update(ws, project.slug, input) : core.projects.create(ws, input),
  );
  const conflict = isApiError(save.error, "conflict") && Boolean(project);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return setLocalError("Give the project a name.");
    if (!project && !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(slug)) {
      return setLocalError("The address may only use lowercase letters, numbers and single hyphens.");
    }
    if (cover && !cover.startsWith("https://")) return setLocalError("The cover image must be an https:// address.");
    setLocalError(null);
    const input: ProjectInput = {
      name: name.trim(),
      description,
      project_type: projectType.trim(),
      engine: engine.trim(),
      status,
      visibility,
      accent_color: accent,
      cover_image_url: cover.trim() || null,
    };
    save.mutate(project ? { ...input, version: project.version } : { ...input, slug }, {
      onSuccess: (saved) => {
        notify(project ? "Project saved." : `Project created: ${saved.name}`);
        onClose();
        if (!project) navigate(paths.project(saved.slug));
      },
    });
  };

  return (
    <Modal
      eyebrow="PROJECTS"
      title={project ? `Edit ${project.name}` : "New project"}
      description={project ? undefined : "Projects group tasks, milestones, documents, decisions and approvals."}
      onClose={onClose}
      size="wide"
    >
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <Field label="Name">
            {(props) => (
              <input
                {...props}
                value={name}
                maxLength={120}
                data-autofocus
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slugTouched) setSlug(slugify(e.target.value));
                }}
              />
            )}
          </Field>
          <Field label="Address" hint={project ? "Permanent." : `/projects/${slug || "…"}`}>
            {(props) => (
              <input
                {...props}
                value={slug}
                disabled={Boolean(project)}
                onChange={(e) => {
                  setSlugTouched(true);
                  setSlug(e.target.value.toLowerCase());
                }}
              />
            )}
          </Field>
          <Field label="Description" className="span-2">
            {(props) => <textarea {...props} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />}
          </Field>
          <Field label="Type" hint="e.g. Open World Survival">
            {(props) => <input {...props} value={projectType} onChange={(e) => setProjectType(e.target.value)} maxLength={80} />}
          </Field>
          <Field label="Engine" hint="e.g. Unity">
            {(props) => <input {...props} value={engine} onChange={(e) => setEngine(e.target.value)} maxLength={40} />}
          </Field>
          <Field label="Status">
            {(props) => (
              <select {...props} value={status} onChange={(e) => setStatus(e.target.value as ProjectStatus)}>
                {(Object.keys(PROJECT_STATUS) as ProjectStatus[]).map((s) => <option key={s} value={s}>{PROJECT_STATUS[s]}</option>)}
              </select>
            )}
          </Field>
          <Field label="Visibility" hint={visibility === "restricted" ? "Only owners, admins and people you add can see it." : "Everyone in the workspace can see it."}>
            {(props) => (
              <select {...props} value={visibility} onChange={(e) => setVisibility(e.target.value as ProjectVisibility)}>
                <option value="workspace">Whole workspace</option>
                <option value="restricted">Restricted</option>
              </select>
            )}
          </Field>
          <Field label="Accent colour">
            {(props) => (
              <select {...props} value={accent} onChange={(e) => setAccent(e.target.value as AccentColor)}>
                {ACCENT_COLORS.map((c) => <option key={c} value={c}>{c[0].toUpperCase() + c.slice(1)}</option>)}
              </select>
            )}
          </Field>
          <Field label="Cover image" hint="Optional https:// image address.">
            {(props) => <input {...props} type="url" value={cover} onChange={(e) => setCover(e.target.value)} placeholder="https://…" />}
          </Field>
        </div>
        {conflict ? (
          <ConflictNotice
            onRefresh={() => {
              void queryClient.invalidateQueries({ queryKey: ["ws", workspaceSlug] });
              onClose();
            }}
          />
        ) : (
          <FormError error={localError ?? save.error} />
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={save.isPending || conflict}>
            {save.isPending ? "Saving…" : project ? "Save project" : "Create project"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
