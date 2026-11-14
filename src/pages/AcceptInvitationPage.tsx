import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { MailCheck } from "lucide-react";
import logo from "../assets/booski-logo.png";
import { invitations } from "../api/core";
import type { InvitationPreview } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Field, FormError } from "../components/ui";
import { formatDateTime } from "../lib/format";
import { paths } from "../routes";
import { ROLE_LABELS } from "../workspace/roles";
import { rememberWorkspace } from "../workspace/WorkspaceProvider";

const MIN_PASSWORD = 12;

/**
 * `/join` — accept an invitation. The invitation code is pasted into the form (it is never put in a URL,
 * where it would end up in browser history and server logs). New people choose a name and password
 * here; people who already have an account sign in first.
 */
export function AcceptInvitationPage() {
  const { state, adoptSession, refresh } = useAuth();
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const signedInEmail = state.status === "authenticated" ? state.me.user.email : null;

  const check = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!token.trim()) return setError("Paste the invitation code you were sent.");
    setBusy(true);
    try {
      setPreview(await invitations.preview(token.trim()));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const accept = async (event: FormEvent) => {
    event.preventDefault();
    if (!preview) return;
    setError(null);
    const newAccount = !preview.account_exists;
    if (newAccount) {
      if (!name.trim()) return setError("Enter your name as teammates should see it.");
      if (password.length < MIN_PASSWORD) return setError(`Choose a password of at least ${MIN_PASSWORD} characters.`);
      if (password !== confirm) return setError("The two passwords don't match.");
    }
    setBusy(true);
    try {
      const accepted = await invitations.accept(token.trim(), newAccount ? { display_name: name.trim(), password } : undefined);
      rememberWorkspace(accepted.workspace.slug);
      if (accepted.signed_in) await adoptSession(accepted.csrf_token);
      else await refresh();
      navigate(paths.home, { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const wrongAccount = preview?.account_exists && signedInEmail && signedInEmail !== preview.email;
  const needsSignIn = preview?.account_exists && !signedInEmail;

  return (
    <main className="auth-page">
      <section className="auth-card panel" aria-labelledby="join-title">
        <img className="auth-logo" src={logo} alt="Booski Studios" />
        <span className="eyebrow">BOOSKI STUDIOS / INVITATION</span>
        <h1 id="join-title">Join a workspace</h1>

        {!preview ? (
          <form onSubmit={check} noValidate>
            <p className="auth-intro">Paste the invitation code a studio owner or admin shared with you.</p>
            <Field label="Invitation code">
              {(props) => <input {...props} value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" autoFocus />}
            </Field>
            <FormError error={error} />
            <button type="submit" className="primary-btn auth-submit" disabled={busy}>
              {busy ? "Checking…" : "Continue"}
            </button>
          </form>
        ) : (
          <form onSubmit={accept} noValidate>
            <div className="auth-notice">
              <MailCheck size={15} aria-hidden="true" /> <b>{preview.workspace_name}</b> invited <b>{preview.email}</b> as{" "}
              {ROLE_LABELS[preview.role]}. The invitation expires {formatDateTime(preview.expires_at)}.
            </div>
            {needsSignIn && (
              <p className="auth-intro">
                You already have an account. <Link to={paths.login} state={{ from: { pathname: paths.join } }}>Sign in</Link> as{" "}
                {preview.email}, then come back here and paste the code again.
              </p>
            )}
            {wrongAccount && (
              <p className="form-error" role="alert">
                You're signed in as {signedInEmail}. Sign out and sign in as {preview.email} to accept this invitation.
              </p>
            )}
            {!preview.account_exists && (
              <>
                <p className="auth-intro">Create your account to join.</p>
                <Field label="Your name">
                  {(props) => <input {...props} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />}
                </Field>
                <Field label="Password" hint={`At least ${MIN_PASSWORD} characters.`}>
                  {(props) => (
                    <input {...props} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
                  )}
                </Field>
                <Field label="Repeat password">
                  {(props) => (
                    <input {...props} type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
                  )}
                </Field>
              </>
            )}
            <FormError error={error} />
            <div className="modal-actions">
              <button type="button" className="secondary-btn" onClick={() => { setPreview(null); setError(null); }}>Back</button>
              <button type="submit" className="primary-btn" disabled={busy || Boolean(needsSignIn) || Boolean(wrongAccount)}>
                {busy ? "Joining…" : "Join workspace"}
              </button>
            </div>
          </form>
        )}
        <p className="auth-footnote">
          Already a member? <Link to={paths.login}>Sign in</Link>
        </p>
      </section>
    </main>
  );
}
