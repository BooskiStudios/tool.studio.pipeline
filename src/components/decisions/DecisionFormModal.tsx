import { useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { isApiError } from "../../api/client";
import * as core from "../../api/core";
import { useDepartments, useDocumentList, useProjectList, useWorkspaceMutation } from "../../api/hooks";
import type { Decision, DecisionInput, DecisionOption, DecisionStatus } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { DECISION_STATUS } from "../../lib/format";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { Modal } from "../Modal";
import { ConflictNotice, Field, FormError } from "../ui";

export interface DecisionDefaults {
  project_id?: string | null;
  department_id?: string | null;
  supersedes?: Decision;
}

/**
 * Record a decision (or edit one). A recorded decision is never deleted; to change course, record a new
 * decision that supersedes it, so the history of what was decided and why stays intact.
 */
export function DecisionFormModal({ decision, defaults = {}, onClose }: {
  decision?: Decision;
  defaults?: DecisionDefaults;
  onClose: () => void;
}) {
  const { slug } = useWorkspace();
  const queryClient = useQueryClient();
  const notify = useToast();
  const projects = useProjectList();
  const departments = useDepartments();
  const documents = useDocumentList({ sort: "title", limit: 200 });
  const source = decision ?? defaults.supersedes;
  const [title, setTitle] = useState(decision?.title ?? "");
  const [context, setContext] = useState(source?.context ?? "");
  const [options, setOptions] = useState<DecisionOption[]>(source?.options.length ? source.options : [{ title: "" }, { title: "" }]);
  const [outcome, setOutcome] = useState(decision?.outcome ?? "");
  const [rationale, setRationale] = useState(decision?.rationale ?? "");
  const [status, setStatus] = useState<DecisionStatus>(decision?.status ?? "proposed");
  const [projectId, setProjectId] = useState(decision?.project_id ?? defaults.project_id ?? source?.project_id ?? "");
  const [departmentId, setDepartmentId] = useState(decision?.department_id ?? defaults.department_id ?? source?.department_id ?? "");
  const [documentIds, setDocumentIds] = useState<string[]>(decision?.document_ids ?? []);
  const [localError, setLocalError] = useState<string | null>(null);

  const save = useWorkspaceMutation((ws, input: DecisionInput) =>
    decision ? core.decisions.update(ws, decision.id, input) : core.decisions.create(ws, input),
  );
  const conflict = isApiError(save.error, "conflict");
  const writableProjects = (projects.data ?? []).filter((p) => p.capabilities.includes("decisions.write") || p.id === projectId);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return setLocalError("Give the decision a title.");
    setLocalError(null);
    const cleanOptions = options
      .map((o) => ({ title: o.title.trim(), summary: o.summary?.trim() || undefined }))
      .filter((o) => o.title);
    const input: DecisionInput = {
      title: title.trim(),
      context,
      options: cleanOptions,
      outcome,
      rationale,
      status,
      department_id: departmentId || null,
      document_ids: documentIds,
    };
    const body: DecisionInput = decision
      ? { ...input, version: decision.version }
      : { ...input, project_id: projectId || null, supersedes_decision_id: defaults.supersedes?.id ?? null };
    save.mutate(body, {
      onSuccess: (saved) => {
        notify(decision ? "Decision updated." : `Decision recorded: ${saved.title}`);
        onClose();
      },
    });
  };

  const setOption = (index: number, patch: Partial<DecisionOption>) =>
    setOptions((list) => list.map((o, i) => (i === index ? { ...o, ...patch } : o)));

  return (
    <Modal
      eyebrow="DECISION LOG"
      title={decision ? "Edit decision" : defaults.supersedes ? "Supersede decision" : "Record a decision"}
      description={
        defaults.supersedes
          ? `This new decision replaces “${defaults.supersedes.title}”. Once accepted, the earlier decision is marked superseded.`
          : "What was decided, the options considered and why. Decisions are kept permanently."
      }
      onClose={onClose}
      size="wide"
    >
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <Field label="Decision" className="span-2">
            {(props) => <input {...props} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} data-autofocus />}
          </Field>
          <Field label="Context" className="span-2" hint="What prompted this decision?">
            {(props) => <textarea {...props} rows={3} value={context} onChange={(e) => setContext(e.target.value)} />}
          </Field>
          <fieldset className="form-field span-2 options-fieldset">
            <legend>Options considered</legend>
            {options.map((option, i) => (
              <div className="option-row" key={i}>
                <input
                  value={option.title}
                  onChange={(e) => setOption(i, { title: e.target.value })}
                  placeholder={`Option ${i + 1}`}
                  aria-label={`Option ${i + 1}`}
                  maxLength={200}
                />
                <input
                  value={option.summary ?? ""}
                  onChange={(e) => setOption(i, { summary: e.target.value })}
                  placeholder="Pros, cons, cost…"
                  aria-label={`Option ${i + 1} notes`}
                />
                <button type="button" className="icon-only" onClick={() => setOptions((l) => l.filter((_, j) => j !== i))} aria-label={`Remove option ${i + 1}`}>
                  <X size={13} aria-hidden="true" />
                </button>
              </div>
            ))}
            <button type="button" className="inline-add" onClick={() => setOptions((l) => [...l, { title: "" }])}>
              <Plus size={13} aria-hidden="true" /> Add option
            </button>
          </fieldset>
          <Field label="Outcome" className="span-2" hint="The option chosen, or what was decided.">
            {(props) => <textarea {...props} rows={2} value={outcome} onChange={(e) => setOutcome(e.target.value)} />}
          </Field>
          <Field label="Rationale" className="span-2">
            {(props) => <textarea {...props} rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} />}
          </Field>
          <Field label="Status">
            {(props) => (
              <select {...props} value={status} onChange={(e) => setStatus(e.target.value as DecisionStatus)}>
                {(["proposed", "accepted", "rejected"] as DecisionStatus[]).map((s) => <option key={s} value={s}>{DECISION_STATUS[s]}</option>)}
                {decision?.status === "superseded" && <option value="superseded">{DECISION_STATUS.superseded}</option>}
              </select>
            )}
          </Field>
          <Field label="Project">
            {(props) => (
              <select {...props} value={projectId} disabled={Boolean(decision)} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">Studio-wide</option>
                {writableProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Department">
            {(props) => (
              <select {...props} value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                <option value="">No department</option>
                {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Supporting documents" hint="Hold Ctrl (⌘ on Mac) to choose several.">
            {(props) => (
              <select
                {...props}
                multiple
                size={4}
                value={documentIds}
                onChange={(e) => setDocumentIds(Array.from(e.target.selectedOptions, (o) => o.value))}
              >
                {documents.items.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
              </select>
            )}
          </Field>
        </div>
        {conflict ? (
          <ConflictNotice
            onRefresh={() => {
              void queryClient.invalidateQueries({ queryKey: ["ws", slug] });
              onClose();
            }}
          />
        ) : (
          <FormError error={localError ?? save.error} />
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={save.isPending || conflict}>
            {save.isPending ? "Saving…" : decision ? "Save decision" : "Record decision"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
