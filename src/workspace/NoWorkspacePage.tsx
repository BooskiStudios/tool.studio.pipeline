import { useState, type FormEvent } from "react";
import { LogOut, Plus } from "lucide-react";
import { workspaces } from "../api/core";
import { useAuth, useMe } from "../auth/AuthProvider";
import { SplashScreen } from "../auth/RequireAuth";
import { Field, FormError } from "../components/ui";
import { slugify } from "../lib/format";

/**
 * Shown to a signed-in person who belongs to no workspace (for example, after being removed from their
 * only one). They can create a workspace of their own, or ask for an invitation.
 */
export function NoWorkspacePage() {
  const me = useMe();
  const { refresh, logout } = useAuth();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !slug) {
      setError("Enter a name and an address for the workspace.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await workspaces.create(name.trim(), slug);
      await refresh();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <SplashScreen>
      <span className="eyebrow">SIGNED IN AS {me.user.email.toUpperCase()}</span>
      <h1>You're not in a workspace yet</h1>
      <p className="auth-intro">
        Ask a studio owner or admin to invite you, then open the invitation link. Or create a workspace of your own.
      </p>
      <form onSubmit={submit} noValidate className="auth-form">
        <Field label="Workspace name">
          {(props) => (
            <input
              {...props}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (!slugTouched) setSlug(slugify(e.target.value));
              }}
            />
          )}
        </Field>
        <Field label="Address" hint="Lowercase letters, numbers and hyphens.">
          {(props) => (
            <input
              {...props}
              value={slug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(e.target.value.toLowerCase());
              }}
            />
          )}
        </Field>
        <FormError error={error} />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={() => void logout()}>
            <LogOut size={13} aria-hidden="true" /> Sign out
          </button>
          <button type="submit" className="primary-btn" disabled={busy}>
            <Plus size={14} aria-hidden="true" /> {busy ? "Creating…" : "Create workspace"}
          </button>
        </div>
      </form>
    </SplashScreen>
  );
}
