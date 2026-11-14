/**
 * The one place the frontend talks to Booski Core.
 *
 * - Same-origin requests to `/api/v1` (Vite proxies them in development; in production the API serves
 *   the app), so the browser sends the HttpOnly session cookie automatically. No token is ever stored
 *   in localStorage or sessionStorage.
 * - Every POST/PUT/PATCH/DELETE carries the session's CSRF token in `X-CSRF-Token`. The token comes from
 *   the sign-in response and from the readable `__Host-booski_csrf` cookie (after a page reload).
 * - Failures become an `ApiError` with a user-facing message; technical details stay in the console.
 */

export const API_BASE = "/api/v1";
const CSRF_COOKIE = "__Host-booski_csrf";
const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export type ApiErrorKind =
  | "network"
  | "unauthenticated"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "rate_limited"
  | "bad_request"
  | "server";

export interface FieldError {
  /** e.g. ["body", "title"] */
  loc: (string | number)[];
  msg: string;
}

interface ProblemBody {
  title?: string;
  detail?: string;
  request_id?: string;
  errors?: FieldError[];
  current_version?: number;
}

const GENERIC_VALIDATION = "The request is invalid.";

function kindFor(status: number): ApiErrorKind {
  if (status === 0) return "network";
  if (status === 401) return "unauthenticated";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 422) return "validation";
  if (status === 429) return "rate_limited";
  if (status >= 500) return "server";
  return "bad_request";
}

function fieldName(loc: (string | number)[]): string {
  const name = loc.filter((part) => part !== "body" && part !== "query" && typeof part === "string").join(" ");
  return name.replace(/_/g, " ");
}

/** Plain-language text for a failure. Booski Core's own `detail` messages are written for people. */
function messageFor(kind: ApiErrorKind, problem: ProblemBody): string {
  switch (kind) {
    case "network":
      return "Booski Core can't be reached. Check that it's running and your connection, then try again.";
    case "unauthenticated":
      return problem.detail ?? "Your session has ended. Please sign in again.";
    case "forbidden":
      return problem.detail ?? "You don't have permission to do that.";
    case "not_found":
      return problem.detail ?? "This item doesn't exist, or you no longer have access to it.";
    case "conflict":
      return problem.detail ?? "Someone else changed this while you were editing it.";
    case "validation": {
      if (problem.detail && problem.detail !== GENERIC_VALIDATION) return problem.detail;
      const first = problem.errors?.[0];
      if (!first) return "Some details aren't valid. Check the form and try again.";
      const field = fieldName(first.loc);
      return field ? `${field[0].toUpperCase()}${field.slice(1)}: ${first.msg}` : first.msg;
    }
    case "rate_limited":
      return problem.detail ?? "Too many attempts. Wait a few minutes and try again.";
    case "server":
      return "Something went wrong in Booski Core. Please try again." +
        (problem.request_id ? ` If it keeps happening, quote reference ${problem.request_id}.` : "");
    default:
      return problem.detail ?? "The request couldn't be completed.";
  }
}

export class ApiError extends Error {
  readonly status: number;
  readonly kind: ApiErrorKind;
  readonly requestId: string | undefined;
  readonly fieldErrors: FieldError[];
  /** For 409 conflicts on versioned records: the version now stored on the server. */
  readonly currentVersion: number | undefined;

  constructor(status: number, problem: ProblemBody = {}) {
    const kind = kindFor(status);
    super(messageFor(kind, problem));
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
    this.requestId = problem.request_id;
    this.fieldErrors = problem.errors ?? [];
    this.currentVersion = problem.current_version;
  }
}

export function isApiError(error: unknown, kind?: ApiErrorKind): error is ApiError {
  return error instanceof ApiError && (kind === undefined || error.kind === kind);
}

/** Text to show a person for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something unexpected went wrong. Please try again.";
}

// ---------------------------------------------------------------- CSRF token

let csrfFromSignIn: string | null = null;

/** Remember the token from the sign-in (or invitation) response. `null` on sign-out. */
export function setCsrfToken(token: string | null): void {
  csrfFromSignIn = token;
}

export function readCsrfCookie(cookies: string = typeof document === "undefined" ? "" : document.cookie): string | null {
  for (const part of cookies.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === CSRF_COOKIE) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export function csrfToken(): string | null {
  // The cookie is authoritative (it always belongs to the current session); memory covers browsers
  // that don't expose Secure cookies to scripts on http://localhost.
  return readCsrfCookie() ?? csrfFromSignIn;
}

// ---------------------------------------------------------------- session expiry hook

type UnauthorizedListener = () => void;
let unauthorizedListener: UnauthorizedListener | null = null;

/** The auth provider registers here to hear about sessions that end while the app is open. */
export function onUnauthorized(listener: UnauthorizedListener | null): void {
  unauthorizedListener = listener;
}

// ---------------------------------------------------------------- requests

export type QueryValue = string | number | boolean | null | undefined | readonly (string | number)[];

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
  /** Don't report a 401 as an expired session (sign-in and the initial session check). */
  expectUnauthenticated?: boolean;
}

export function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => params.append(key, String(item)));
    else params.append(key, String(value));
  }
  const search = params.toString();
  return `${API_BASE}${path}${search ? `?${search}` : ""}`;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!SAFE_METHODS.has(method)) {
    const token = csrfToken();
    if (token) headers[CSRF_HEADER] = token;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "same-origin",
      signal: options.signal,
    });
  } catch (error) {
    if (options.signal?.aborted) throw error; // cancelled on purpose: let the caller ignore it
    throw new ApiError(0);
  }

  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") ?? "";
  const data: unknown = type.includes("json") ? await response.json().catch(() => ({})) : undefined;

  if (!response.ok) {
    const error = new ApiError(response.status, (data ?? {}) as ProblemBody);
    if (error.kind === "unauthenticated" && !options.expectUnauthenticated) unauthorizedListener?.();
    throw error;
  }
  return data as T;
}
