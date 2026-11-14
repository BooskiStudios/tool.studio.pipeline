import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, isApiError, onUnauthorized, setCsrfToken } from "../api/client";
import { auth } from "../api/core";
import type { MeResponse } from "../api/types";

/** Why the user is signed out, so the sign-in page can explain it. */
export type SignedOutReason = "expired" | "signed_out" | null;

export type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; me: MeResponse }
  | { status: "unauthenticated"; reason: SignedOutReason }
  /** Booski Core couldn't be reached while checking the session. */
  | { status: "unreachable"; error: ApiError };

export interface AuthContextValue {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-reads the session (e.g. after accepting an invitation or creating a workspace). */
  refresh: () => Promise<void>;
  /** Accept a session that was just created elsewhere (invitation acceptance). */
  adoptSession: (csrfToken: string | null | undefined) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Who is signed in. Established from `GET /auth/me` on start-up; the session itself lives in an
 * HttpOnly cookie the frontend can't read, so nothing secret is kept in JavaScript or browser storage.
 *
 * If any API call later answers 401 (session expired, revoked from another browser, or the account
 * was deactivated), every cached record is dropped and the app returns to the sign-in page.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading" });
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const signOutLocally = useCallback(
    (reason: SignedOutReason) => {
      setCsrfToken(null);
      queryClient.clear(); // no data from this session survives into the next
      setState({ status: "unauthenticated", reason });
    },
    [queryClient],
  );

  const loadSession = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const me = await auth.me(signal);
        setState({ status: "authenticated", me });
      } catch (error) {
        if (signal?.aborted) return;
        if (isApiError(error, "unauthenticated")) {
          const wasSignedIn = stateRef.current.status === "authenticated";
          signOutLocally(wasSignedIn ? "expired" : null);
        } else if (error instanceof ApiError) {
          setState({ status: "unreachable", error });
        } else {
          throw error;
        }
      }
    },
    [signOutLocally],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadSession(controller.signal);
    return () => controller.abort();
  }, [loadSession]);

  // A 401 from any request while signed in means the session ended underneath us.
  useEffect(() => {
    onUnauthorized(() => {
      if (stateRef.current.status === "authenticated") signOutLocally("expired");
    });
    return () => onUnauthorized(null);
  }, [signOutLocally]);

  // When the person comes back to the tab, confirm the session still exists (it may have been
  // revoked elsewhere). Only on return, never on a timer, so an idle tab can't keep a session alive.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible" && stateRef.current.status === "authenticated") void loadSession();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [loadSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await auth.login(email, password);
      setCsrfToken(response.csrf_token);
      queryClient.clear();
      await loadSession();
    },
    [loadSession, queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } catch (error) {
      // Already signed out on the server is fine; anything else is still a local sign-out, but say so.
      if (!isApiError(error, "unauthenticated")) console.warn("Sign-out request failed", error);
    }
    signOutLocally("signed_out");
  }, [signOutLocally]);

  const adoptSession = useCallback(
    async (token: string | null | undefined) => {
      if (token) setCsrfToken(token);
      queryClient.clear();
      await loadSession();
    },
    [loadSession, queryClient],
  );

  const refresh = useCallback(() => loadSession(), [loadSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ state, login, logout, refresh, adoptSession }),
    [state, login, logout, refresh, adoptSession],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}

/** The signed-in user's details. Only use below <RequireAuth>. */
export function useMe(): MeResponse {
  const { state } = useAuth();
  if (state.status !== "authenticated") throw new Error("useMe needs a signed-in user");
  return state.me;
}
