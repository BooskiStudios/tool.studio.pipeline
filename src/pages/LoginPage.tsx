import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router";
import { LogIn } from "lucide-react";
import logo from "../assets/booski-logo.png";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Field, FormError } from "../components/ui";
import { paths } from "../routes";

interface FromState {
  from?: { pathname: string; search?: string };
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Where to go after signing in: back to the page that sent you here, if it was inside the app. */
export function returnPath(state: unknown): string {
  const from = (state as FromState | null)?.from;
  if (!from?.pathname || !from.pathname.startsWith("/") || from.pathname.startsWith("//")) return paths.home;
  if (from.pathname === paths.login) return paths.home;
  return `${from.pathname}${from.search ?? ""}`;
}

/** `/login` — sign in with an account created by the owner or by accepting an invitation. */
export function LoginPage() {
  const { state, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (state.status === "authenticated") return <Navigate to={returnPath(location.state)} replace />;

  const reason = state.status === "unauthenticated" ? state.reason : null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const errors: typeof fieldErrors = {};
    if (!EMAIL_PATTERN.test(email.trim())) errors.email = "Enter the email address you were invited with.";
    if (!password) errors.password = "Enter your password.";
    setFieldErrors(errors);
    setError(null);
    if (errors.email || errors.password) return;
    setSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch (caught) {
      setError(errorMessage(caught));
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card panel" aria-labelledby="login-title">
        <img className="auth-logo" src={logo} alt="Booski Studios" />
        <span className="eyebrow">BOOSKI STUDIOS / STUDIO OS</span>
        <h1 id="login-title">Sign in</h1>
        <p className="auth-intro">Use the account your studio owner created for you, or the one you set up from an invitation.</p>

        {reason === "expired" && (
          <div className="auth-notice" role="status">Your session has ended. Please sign in again to continue.</div>
        )}
        {reason === "signed_out" && <div className="auth-notice" role="status">You've signed out.</div>}
        {state.status === "unreachable" && (
          <div className="form-error" role="alert">{state.error.message}</div>
        )}

        <form onSubmit={submit} noValidate>
          <Field label="Email" error={fieldErrors.email}>
            {(props) => (
              <input
                {...props}
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-autofocus
                autoFocus
              />
            )}
          </Field>
          <Field label="Password" error={fieldErrors.password}>
            {(props) => (
              <input
                {...props}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Field>
          <FormError error={error} />
          <button type="submit" className="primary-btn auth-submit" disabled={submitting}>
            <LogIn size={15} aria-hidden="true" /> {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-footnote">
          No account? Ask your studio owner for an invitation. There is no public sign-up.
        </p>
      </section>
    </main>
  );
}
