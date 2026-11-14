import { useEffect, useState, type DependencyList } from "react";

export type Resource<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; error: Error };

/**
 * Loads async data (usually a `studioApi` call) and tracks its loading / error state.
 * Re-runs when `deps` change; ignores results from superseded requests.
 *
 * @example const decisions = useResource(() => studioApi.listDecisions(), []);
 */
export function useResource<T>(load: () => Promise<T>, deps: DependencyList): Resource<T> {
  const [resource, setResource] = useState<Resource<T>>({ status: "loading" });

  useEffect(() => {
    let current = true;
    setResource({ status: "loading" });
    load().then(
      (data) => current && setResource({ status: "ready", data }),
      (error: unknown) =>
        current && setResource({ status: "error", error: error instanceof Error ? error : new Error(String(error)) }),
    );
    return () => {
      current = false;
    };
    // `load` is intentionally excluded: callers pass an inline closure and declare its inputs in `deps`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return resource;
}
