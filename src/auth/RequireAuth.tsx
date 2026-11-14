import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { RefreshCw, WifiOff } from "lucide-react";
import logo from "../assets/booski-logo.png";
import { paths } from "../routes";
import { useAuth } from "./AuthProvider";

/** Full-screen message used while the session is checked or when Booski Core can't be reached. */
export function SplashScreen({ children }: { children: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-card panel splash-card">
        <img className="auth-logo" src={logo} alt="Booski Studios" />
        {children}
      </section>
    </main>
  );
}

/** Renders `children` only for a signed-in user; everyone else is sent to the sign-in page. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { state, refresh } = useAuth();
  const location = useLocation();

  if (state.status === "loading") {
    return (
      <SplashScreen>
        <p role="status">Checking your session…</p>
      </SplashScreen>
    );
  }
  if (state.status === "unreachable") {
    return (
      <SplashScreen>
        <WifiOff size={22} aria-hidden="true" />
        <p role="alert">{state.error.message}</p>
        <button type="button" className="secondary-btn" onClick={() => void refresh()}>
          <RefreshCw size={13} aria-hidden="true" /> Try again
        </button>
      </SplashScreen>
    );
  }
  if (state.status === "unauthenticated") {
    return <Navigate to={paths.login} replace state={{ from: { pathname: location.pathname, search: location.search } }} />;
  }
  return <>{children}</>;
}
