import { useState, type FormEvent } from "react";
import { ArrowUpRight, Copy, LogOut, Settings, Trash2, UserPlus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import * as core from "../api/core";
import { useInvitations, useMembers, useWorkspaceMutation } from "../api/hooks";
import type { AssignableRole, InvitationCreated, Role } from "../api/types";
import { useAuth, useMe } from "../auth/AuthProvider";
import { PageHeading } from "../components/common";
import { Field, FormError, QueryView } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { formatDateTime } from "../lib/format";
import { MANAGEABLE_ROLES, ROLE_LABELS } from "../workspace/roles";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const PLANNED = [
  { title: "AI providers", detail: "Choose and configure model providers (Phase 3)" },
  { title: "Integrations", detail: "Unity, GitHub, MCP servers and external APIs (later phase)" },
  { title: "Appearance", detail: "Branding, theme and interface preferences (later phase)" },
];

function AccountSection() {
  const me = useMe();
  const { logout } = useAuth();
  const notify = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const sessions = useQuery({ queryKey: ["auth", "sessions"], queryFn: ({ signal }) => core.auth.sessions(signal) });
  const change = useWorkspaceMutation((_ws, vars: { current: string; next: string }) => core.auth.changePassword(vars.current, vars.next));
  const revoke = useWorkspaceMutation((_ws, id: string) => core.auth.revokeSession(id));
  const revokeOthers = useWorkspaceMutation((_ws, _: void) => core.auth.revokeOtherSessions());

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (next.length < 12) return setLocalError("Choose a new password of at least 12 characters.");
    if (next !== confirm) return setLocalError("The new passwords don't match.");
    setLocalError(null);
    change.mutate(
      { current, next },
      {
        onSuccess: (result) => {
          setCurrent("");
          setNext("");
          setConfirm("");
          notify(`Password changed. Signed out ${result.revoked} other ${result.revoked === 1 ? "session" : "sessions"}.`);
          void sessions.refetch();
        },
      },
    );
  };

  return (
    <section className="panel settings-section" aria-labelledby="account-title">
      <div className="panel-title"><h2 id="account-title">Your account</h2></div>
      <dl className="detail-grid">
        <dt>Name</dt><dd>{me.user.display_name}</dd>
        <dt>Email</dt><dd>{me.user.email}</dd>
        <dt>This session ends</dt><dd>after inactivity, by {formatDateTime(me.session.idle_expires_at)}; at the latest {formatDateTime(me.session.absolute_expires_at)}</dd>
      </dl>
      <form onSubmit={submit} noValidate className="settings-form">
        <h3 className="section-title">Change password</h3>
        <Field label="Current password">{(p) => <input {...p} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />}</Field>
        <Field label="New password" hint="At least 12 characters. Your other sessions will be signed out.">
          {(p) => <input {...p} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}
        </Field>
        <Field label="Repeat new password">{(p) => <input {...p} type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
        <FormError error={localError ?? change.error} />
        <div className="modal-actions"><button type="submit" className="primary-btn" disabled={change.isPending}>Change password</button></div>
      </form>
      <h3 className="section-title">Signed-in browsers</h3>
      <QueryView query={sessions} label="sessions">
        {(rows) => (
          <div className="member-table">
            {rows.map((s) => (
              <div className="member-row" key={s.id}>
                <span>
                  <b>{s.current ? "This browser" : s.user_agent?.slice(0, 60) || "Unknown browser"}</b>
                  <small>Signed in {formatDateTime(s.created_at)} · last active {formatDateTime(s.last_seen_at)}{s.ip ? ` · ${s.ip}` : ""}</small>
                </span>
                {!s.current && (
                  <button type="button" className="secondary-btn" onClick={() => revoke.mutate(s.id, { onSuccess: () => void sessions.refetch() })}>
                    Sign out
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </QueryView>
      <FormError error={revoke.error ?? revokeOthers.error} />
      <div className="modal-actions">
        <button type="button" className="secondary-btn" onClick={() => revokeOthers.mutate(undefined, { onSuccess: () => void sessions.refetch() })}>
          Sign out other browsers
        </button>
        <button type="button" className="primary-btn" onClick={() => void logout()}>
          <LogOut size={13} aria-hidden="true" /> Sign out
        </button>
      </div>
    </section>
  );
}

function WorkspaceSection() {
  const me = useMe();
  const notify = useToast();
  const { name, role, can } = useWorkspace();
  const members = useMembers();
  const invitations = useInvitations(can("invitations.manage"));
  const [workspaceName, setWorkspaceName] = useState(name);
  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<AssignableRole>("developer");
  const [created, setCreated] = useState<InvitationCreated | null>(null);
  const rename = useWorkspaceMutation((ws, newName: string) => core.workspaces.rename(ws, newName));
  const changeRole = useWorkspaceMutation((ws, vars: { userId: string; role: AssignableRole }) => core.workspaces.changeRole(ws, vars.userId, vars.role));
  const removeMember = useWorkspaceMutation((ws, userId: string) => core.workspaces.removeMember(ws, userId));
  const invite = useWorkspaceMutation((ws, vars: { email: string; role: AssignableRole }) => core.workspaces.invite(ws, vars.email, vars.role));
  const revokeInvite = useWorkspaceMutation((ws, id: string) => core.workspaces.revokeInvitation(ws, id));
  const manageable = MANAGEABLE_ROLES[role];

  return (
    <section className="panel settings-section" aria-labelledby="workspace-title">
      <div className="panel-title"><h2 id="workspace-title">Workspace: {name}</h2></div>
      <p className="muted-text">Your role: {ROLE_LABELS[role]}.</p>
      {can("workspace.update") && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (workspaceName.trim()) rename.mutate(workspaceName.trim(), { onSuccess: () => notify("Workspace renamed. It updates everywhere after the next refresh.") });
          }}
        >
          <input value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} aria-label="Workspace name" maxLength={80} />
          <button type="submit" className="secondary-btn" disabled={rename.isPending}>Rename</button>
        </form>
      )}
      <FormError error={rename.error} />

      <h3 className="section-title">Members</h3>
      <QueryView query={members} label="members">
        {(rows) => (
          <div className="member-table">
            {rows.map((m) => {
              const canManage = can("members.manage") && m.user_id !== me.user.id && manageable.includes(m.role as Role);
              return (
                <div className="member-row" key={m.user_id}>
                  <span>
                    <b>{m.display_name}{m.user_id === me.user.id ? " (you)" : ""}</b>
                    <small>{m.email} · joined {formatDateTime(m.joined_at)}</small>
                  </span>
                  {canManage ? (
                    <>
                      <select
                        value={m.role}
                        aria-label={`Role for ${m.display_name}`}
                        onChange={(e) => changeRole.mutate({ userId: m.user_id, role: e.target.value as AssignableRole })}
                      >
                        {manageable.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                      </select>
                      <button
                        type="button"
                        className="icon-only"
                        aria-label={`Remove ${m.display_name} from the workspace`}
                        onClick={() => {
                          if (window.confirm(`Remove ${m.display_name} from ${name}? They lose access immediately.`)) removeMember.mutate(m.user_id);
                        }}
                      >
                        <Trash2 size={13} aria-hidden="true" />
                      </button>
                    </>
                  ) : (
                    <span className="pill pill-neutral">{ROLE_LABELS[m.role]}</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </QueryView>
      <FormError error={changeRole.error ?? removeMember.error} />

      {can("invitations.manage") && (
        <>
          <h3 className="section-title">Invite someone</h3>
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (email.trim()) invite.mutate({ email: email.trim(), role: inviteRole }, { onSuccess: (result) => { setCreated(result); setEmail(""); } });
            }}
          >
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@studio.com" aria-label="Email to invite" />
            <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as AssignableRole)} aria-label="Role for the invitation">
              {manageable.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
            <button type="submit" className="primary-btn" disabled={invite.isPending}><UserPlus size={13} aria-hidden="true" /> Invite</button>
          </form>
          <FormError error={invite.error} />
          {created && (
            <div className="invite-token" role="status">
              <p>
                Invitation for <b>{created.invitation.email}</b> created. Send them this code and the address <b>{window.location.origin}/join</b>.
                The code is shown only once and expires {formatDateTime(created.invitation.expires_at)}. Nothing is emailed automatically.
              </p>
              <code data-testid="invitation-token">{created.token}</code>
              <button type="button" className="secondary-btn" onClick={() => void navigator.clipboard?.writeText(created.token).then(() => notify("Invitation code copied."))}>
                <Copy size={13} aria-hidden="true" /> Copy code
              </button>
            </div>
          )}
          <h3 className="section-title">Pending invitations</h3>
          <QueryView query={invitations} label="invitations">
            {(rows) =>
              rows.length === 0 ? (
                <p className="muted-text">No pending invitations.</p>
              ) : (
                <div className="member-table">
                  {rows.map((inv) => (
                    <div className="member-row" key={inv.id}>
                      <span>
                        <b>{inv.email}</b>
                        <small>{ROLE_LABELS[inv.role]} · expires {formatDateTime(inv.expires_at)}</small>
                      </span>
                      <button type="button" className="secondary-btn" onClick={() => revokeInvite.mutate(inv.id)}>Revoke</button>
                    </div>
                  ))}
                </div>
              )
            }
          </QueryView>
          <FormError error={revokeInvite.error} />
        </>
      )}
    </section>
  );
}

/** `/settings` — your account, the workspace's members and invitations, and settings planned for later phases. */
export function SettingsPage() {
  const notify = useToast();
  return (
    <div className="workspace-page">
      <PageHeading eyebrow="BOOSKI STUDIOS" title="Settings" description="Your account, the people in this workspace and how they join." source="live" />
      <div className="settings-columns">
        <AccountSection />
        <WorkspaceSection />
      </div>
      <h2 className="section-title">Planned</h2>
      <div className="utility-grid">
        {PLANNED.map((s) => (
          <button type="button" className="panel utility-card" key={s.title} onClick={() => notify(`${s.title}: ${s.detail}.`)}>
            <span className="work-icon"><Settings size={19} aria-hidden="true" /></span>
            <b>{s.title}</b>
            <small>{s.detail}</small>
            <ArrowUpRight size={16} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
