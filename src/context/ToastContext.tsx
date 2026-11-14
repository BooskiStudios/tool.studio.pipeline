import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { ShieldCheck } from "lucide-react";

const TOAST_DURATION_MS = 2800;

type Notify = (message: string) => void;

const ToastContext = createContext<Notify | null>(null);

/**
 * Shows one short status message at a time. A new message replaces the current
 * one and restarts the timer, so an earlier timer can never hide a later message.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  const timer = useRef<number | undefined>(undefined);

  const notify = useCallback<Notify>((next) => {
    window.clearTimeout(timer.current);
    setMessage(next);
    timer.current = window.setTimeout(() => setMessage(""), TOAST_DURATION_MS);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {message && (
          <div className="toast">
            <ShieldCheck size={16} aria-hidden="true" />
            {message}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Notify {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error("useToast must be used inside <ToastProvider>");
  return notify;
}
