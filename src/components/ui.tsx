import { useId, type ReactNode } from "react";
import { AlertTriangle, Lock, RefreshCw, WifiOff } from "lucide-react";
import { errorMessage, isApiError } from "../api/client";

// ---------------------------------------------------------------- forms

/** A labelled form control. `children` is the input; `hint` and `error` are announced with it. */
export function Field({ label, hint, error, children, className = "" }: {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  children: (props: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => ReactNode;
  className?: string;
}) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`form-field ${className}`}>
      <label htmlFor={id}>{label}</label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {hint && <small id={hintId} className="form-hint">{hint}</small>}
      {error && <small id={errorId} className="form-error-text">{error}</small>}
    </div>
  );
}

/** A form-level error (from the server or validation), announced to screen readers. */
export function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const message = typeof error === "string" ? error : errorMessage(error);
  return (
    <div className="form-error" role="alert">
      <AlertTriangle size={14} aria-hidden="true" /> {message}
    </div>
  );
}

// ---------------------------------------------------------------- loading / error states

interface QueryLike<T> {
  data: T | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  isFetching?: boolean;
  refetch: () => unknown;
}

/** Explains a failed request in plain language, with the right icon and a retry where it helps. */
export function ErrorState({ error, label, onRetry }: { error: unknown; label: string; onRetry?: () => unknown }) {
  const forbidden = isApiError(error, "forbidden");
  const network = isApiError(error, "network");
  const Icon = forbidden ? Lock : network ? WifiOff : AlertTriangle;
  return (
    <div className="resource-state resource-error" role="alert">
      <div className="state-message">
        <Icon size={20} aria-hidden="true" />
        <b>{forbidden ? `You don't have access to ${label}` : `Couldn't load ${label}`}</b>
        <span>{errorMessage(error)}</span>
        {onRetry && !forbidden && (
          <button type="button" className="secondary-btn" onClick={() => onRetry()}>
            <RefreshCw size={13} aria-hidden="true" /> Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return <div className="resource-state" role="status" aria-live="polite">Loading {label}…</div>;
}

/**
 * Loading / error / ready for a query. Never shows placeholder data while loading: real records only.
 */
export function QueryView<T>({ query, label, children }: {
  query: QueryLike<T>;
  label: string;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) return <LoadingState label={label} />;
  if (query.isError || query.data === undefined) return <ErrorState error={query.error} label={label} onRetry={query.refetch} />;
  return <>{children(query.data)}</>;
}

/** Small "refreshing…" hint for background refetches of data already on screen. */
export function RefreshingHint({ active }: { active: boolean | undefined }) {
  return active ? <span className="refreshing-hint" role="status">Refreshing…</span> : null;
}

/** "Load more" for cursor-paginated lists. */
export function LoadMore({ hasNextPage, isFetchingNextPage, fetchNextPage, error }: {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => unknown;
  error?: unknown;
}) {
  if (!hasNextPage) return null;
  return (
    <div className="load-more">
      {error ? <FormError error={error} /> : null}
      <button type="button" className="secondary-btn" disabled={isFetchingNextPage} onClick={() => fetchNextPage()}>
        {isFetchingNextPage ? "Loading…" : "Load more"}
      </button>
    </div>
  );
}

/** Shown when a save failed because someone else changed the record first (HTTP 409). */
export function ConflictNotice({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="conflict-notice" role="alert">
      <AlertTriangle size={15} aria-hidden="true" />
      <span>
        <b>This record changed while you were editing it.</b> Your change was not saved, so nobody's work was
        overwritten. Refresh to load the latest version, then make your change again.
      </span>
      <button type="button" className="secondary-btn" onClick={onRefresh}>
        <RefreshCw size={13} aria-hidden="true" /> Refresh
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- small display pieces

export function Pill({ tone = "neutral", children }: { tone?: "neutral" | "green" | "orange" | "red" | "blue" | "pink"; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

/** Marks a screen or panel as connected to Booski Core, or as a preview of a future phase. */
export function SourceChip({ source }: { source: "live" | "planned" }) {
  return source === "live" ? (
    <span className="live-chip">LIVE · BOOSKI CORE</span>
  ) : (
    <span className="demo-chip">PREVIEW · PLANNED FOR A LATER PHASE</span>
  );
}

export function ProgressBar({ percent, label }: { percent: number; label: string }) {
  return (
    <div className="progress-line" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
      <span style={{ width: `${percent}%` }} />
    </div>
  );
}
