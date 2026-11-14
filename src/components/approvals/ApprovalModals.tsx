import { useState, type FormEvent } from "react";
import { Ban, Check, MessageSquare, RotateCcw, X } from "lucide-react";
import { useMe } from "../../auth/AuthProvider";
import * as core from "../../api/core";
import { useApproval, useMemberNames, useMembers, useProjectIndex, useProjectList, useReviews, useWorkspaceMutation } from "../../api/hooks";
import type { Approval, ApprovalInput, ApprovalKind, ReviewAction } from "../../api/types";
import { useToast } from "../../context/ToastContext";
import { APPROVAL_KIND, APPROVAL_STATUS, formatDateTime, REVIEW_ACTION } from "../../lib/format";
import { ROLE_CAPABILITIES } from "../../workspace/roles";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { Modal } from "../Modal";
import { Field, FormError, QueryView } from "../ui";

export function statusTone(status: Approval["status"]): "orange" | "green" | "red" | "neutral" | "blue" {
  if (status === "approved") return "green";
  if (status === "rejected") return "red";
  if (status === "pending") return "orange";
  if (status === "changes_requested") return "blue";
  return "neutral";
}

/** Ask for an approval. Recording a request doesn't run anything; the approval is a decision record. */
export function ApprovalRequestModal({ defaults = {}, onClose }: { defaults?: Partial<ApprovalInput>; onClose: () => void }) {
  const me = useMe();
  const notify = useToast();
  const projects = useProjectList();
  const members = useMembers();
  const [kind, setKind] = useState<ApprovalKind>(defaults.kind ?? "general");
  const [title, setTitle] = useState(defaults.title ?? "");
  const [description, setDescription] = useState(defaults.description ?? "");
  const [projectId, setProjectId] = useState(defaults.project_id ?? "");
  const [reviewer, setReviewer] = useState("");
  const [due, setDue] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const create = useWorkspaceMutation((ws, body: ApprovalInput) => core.approvals.create(ws, body));
  // People who can review: anyone whose role can review assigned approvals, except you.
  const reviewers = (members.data ?? []).filter(
    (m) => m.user_id !== me.user.id && ROLE_CAPABILITIES[m.role].has("approvals.review_assigned"),
  );
  const writableProjects = (projects.data ?? []).filter((p) => p.capabilities.includes("approvals.request"));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return setLocalError("Describe what needs approving.");
    setLocalError(null);
    create.mutate(
      {
        kind,
        title: title.trim(),
        description,
        project_id: projectId || null,
        subject_type: defaults.subject_type ?? null,
        subject_id: defaults.subject_id ?? null,
        reviewer_user_id: reviewer || null,
        due_at: due ? new Date(`${due}T17:00:00`).toISOString() : null,
      },
      {
        onSuccess: (a) => {
          notify(`Approval requested: ${a.title}`);
          onClose();
        },
      },
    );
  };

  return (
    <Modal
      eyebrow="APPROVALS CENTRE"
      title="Request approval"
      description="Ask a reviewer to approve, reject or request changes. Approving records the decision; it doesn't carry out the work automatically."
      onClose={onClose}
      size="wide"
    >
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <Field label="What needs approving?" className="span-2">
            {(props) => <input {...props} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} data-autofocus />}
          </Field>
          <Field label="Details" className="span-2">
            {(props) => <textarea {...props} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />}
          </Field>
          <Field label="Type">
            {(props) => (
              <select {...props} value={kind} onChange={(e) => setKind(e.target.value as ApprovalKind)}>
                {(Object.keys(APPROVAL_KIND) as ApprovalKind[]).map((k) => <option key={k} value={k}>{APPROVAL_KIND[k]}</option>)}
              </select>
            )}
          </Field>
          <Field label="Project">
            {(props) => (
              <select {...props} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">Studio-wide</option>
                {writableProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Reviewer" hint="Optional. Owners and admins can decide any request.">
            {(props) => (
              <select {...props} value={reviewer} onChange={(e) => setReviewer(e.target.value)}>
                <option value="">Any owner or admin</option>
                {reviewers.map((m) => <option key={m.user_id} value={m.user_id}>{m.display_name}</option>)}
              </select>
            )}
          </Field>
          <Field label="Needed by">
            {(props) => <input {...props} type="date" value={due} onChange={(e) => setDue(e.target.value)} />}
          </Field>
        </div>
        <FormError error={localError ?? create.error} />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={create.isPending}>{create.isPending ? "Sending…" : "Request approval"}</button>
        </div>
      </form>
    </Modal>
  );
}

type Action = ReviewAction | "resubmit" | "cancel";
const NEEDS_COMMENT: Action[] = ["reject", "request_changes", "comment"];

/** One approval request: its details, the full review history, and the actions open to you. */
export function ApprovalDetailModal({ approvalId, onClose }: { approvalId: string; onClose: () => void }) {
  const me = useMe();
  const { can } = useWorkspace();
  const notify = useToast();
  const approval = useApproval(approvalId);
  const reviews = useReviews(approvalId);
  const nameOf = useMemberNames();
  const projects = useProjectIndex();
  const [comment, setComment] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const act = useWorkspaceMutation((ws, vars: { action: Action; comment: string }) => {
    if (vars.action === "resubmit") return core.approvals.resubmit(ws, approvalId, vars.comment);
    if (vars.action === "cancel") return core.approvals.cancel(ws, approvalId, vars.comment);
    return core.approvals.review(ws, approvalId, vars.action, vars.comment);
  });

  const run = (action: Action) => {
    if (NEEDS_COMMENT.includes(action) && !comment.trim()) {
      setLocalError(action === "comment" ? "Write a comment first." : "Add a comment explaining what needs to change or why it's rejected.");
      return;
    }
    setLocalError(null);
    act.mutate(
      { action, comment: comment.trim() },
      {
        onSuccess: (result) => {
          setComment("");
          notify(`${result.title}: ${APPROVAL_STATUS[result.status].toLowerCase()}.`);
        },
      },
    );
  };

  return (
    <Modal eyebrow="APPROVALS CENTRE" title={approval.data?.title ?? "Approval request"} onClose={onClose} size="wide">
      <QueryView query={approval} label="this approval request">
        {(a) => {
          const mine = a.requested_by_user_id === me.user.id;
          const open = a.status === "pending" || a.status === "changes_requested";
          const canResubmit = mine && a.status === "changes_requested";
          const canCancel = open && (mine || can("approvals.decide"));
          const project = a.project_id ? projects.get(a.project_id) : undefined;
          return (
            <>
              <div className="tags">
                <span className={`pill pill-${statusTone(a.status)}`}>{APPROVAL_STATUS[a.status]}</span>
                <span>{APPROVAL_KIND[a.kind]}</span>
                <span>{project?.name ?? "Studio-wide"}</span>
              </div>
              <dl className="detail-grid">
                <dt>Requested by</dt><dd>{nameOf(a.requested_by_user_id) ?? "Former member"}{mine ? " (you)" : ""}</dd>
                <dt>Reviewer</dt><dd>{a.reviewer_user_id ? nameOf(a.reviewer_user_id) ?? "Former member" : "Any owner or admin"}</dd>
                <dt>Requested</dt><dd>{formatDateTime(a.created_at)}</dd>
                <dt>Needed by</dt><dd>{formatDateTime(a.due_at)}</dd>
                {a.resolved_at && <><dt>Resolved</dt><dd>{formatDateTime(a.resolved_at)} by {nameOf(a.resolved_by_user_id) ?? "Former member"}</dd></>}
              </dl>
              {a.description && <p className="detail-text">{a.description}</p>}
              <p className="small-note">An approval records a decision. Nothing is executed or published automatically when a request is approved.</p>

              <h3 className="section-title">Review history</h3>
              <QueryView query={reviews} label="reviews">
                {(rows) =>
                  rows.length === 0 ? (
                    <p className="muted-text">No reviews yet.</p>
                  ) : (
                    <ol className="review-list">
                      {rows.map((r) => (
                        <li key={r.id}>
                          <b>{REVIEW_ACTION[r.action]}</b> · {nameOf(r.actor_user_id) ?? "Former member"} · {formatDateTime(r.created_at)}
                          {r.comment && <p>{r.comment}</p>}
                        </li>
                      ))}
                    </ol>
                  )
                }
              </QueryView>

              {(a.can_decide || canResubmit || canCancel) && (
                <div className="review-box">
                  <label htmlFor="review-comment">Comment</label>
                  <textarea
                    id="review-comment"
                    rows={3}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder={a.can_decide ? "Required when rejecting or requesting changes" : "Optional"}
                  />
                  <FormError error={localError ?? act.error} />
                  <div className="modal-actions wrap">
                    {canCancel && (
                      <button type="button" className="secondary-btn" disabled={act.isPending} onClick={() => run("cancel")}>
                        <Ban size={13} aria-hidden="true" /> Cancel request
                      </button>
                    )}
                    {canResubmit && (
                      <button type="button" className="primary-btn" disabled={act.isPending} onClick={() => run("resubmit")}>
                        <RotateCcw size={13} aria-hidden="true" /> Resubmit
                      </button>
                    )}
                    {a.can_decide && (
                      <>
                        <button type="button" className="secondary-btn" disabled={act.isPending} onClick={() => run("comment")}>
                          <MessageSquare size={13} aria-hidden="true" /> Comment
                        </button>
                        <button type="button" className="secondary-btn" disabled={act.isPending} onClick={() => run("request_changes")}>
                          <RotateCcw size={13} aria-hidden="true" /> Request changes
                        </button>
                        <button type="button" className="secondary-btn danger" disabled={act.isPending} onClick={() => run("reject")}>
                          <X size={13} aria-hidden="true" /> Reject
                        </button>
                        <button type="button" className="primary-btn" disabled={act.isPending} onClick={() => run("approve")}>
                          <Check size={13} aria-hidden="true" /> Approve
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
              {mine && open && !a.can_decide && (
                <p className="small-note">You can't decide your own request; a reviewer or admin will respond.</p>
              )}
            </>
          );
        }}
      </QueryView>
    </Modal>
  );
}
