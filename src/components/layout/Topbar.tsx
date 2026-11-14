import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Bell, Code2, Gauge, ListTodo, Search, Send, Settings, Sparkles, WandSparkles, X, type LucideIcon } from "lucide-react";
import { useApprovalList } from "../../api/hooks";
import { useMe } from "../../auth/AuthProvider";
import { useToast } from "../../context/ToastContext";
import { paths } from "../../routes";

const quickActions: { label: string; prefix: string; icon: LucideIcon }[] = [
  { label: "Research", prefix: "Research ", icon: Search },
  { label: "Create", prefix: "Create ", icon: WandSparkles },
  { label: "Analyse", prefix: "Analyse ", icon: Gauge },
  { label: "Build", prefix: "Build ", icon: Code2 },
  { label: "Plan", prefix: "Plan ", icon: ListTodo },
];

/**
 * AI command bar and top-right actions.
 *
 * PREVIEW: the AI command bar arrives with AI orchestration (Phase 3). Commands are echoed back here
 * and not sent anywhere. Notifications show approval requests waiting for you (live).
 */
export function Topbar() {
  const navigate = useNavigate();
  const notify = useToast();
  const me = useMe();
  const pending = useApprovalList({ status: ["pending"], limit: 50 });
  const waiting = pending.items.filter((a) => a.can_decide).length;
  const initials = me.user.display_name.split(/s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
  const inputRef = useRef<HTMLInputElement>(null);
  const popoverId = useId();
  const [command, setCommand] = useState("");
  const [lastCommand, setLastCommand] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    if (!showNotifications) return;
    const onKeyDown = (event: KeyboardEvent) => event.key === "Escape" && setShowNotifications(false);
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [showNotifications]);

  const submit = () => {
    const text = command.trim();
    if (!text) return;
    setLastCommand(text);
    notify("Preview: the AI command bar arrives with AI orchestration in Phase 3. Nothing was sent.");
    setCommand("");
  };

  const startCommand = (prefix: string) => {
    setCommand(prefix);
    inputRef.current?.focus();
  };

  return (
    <>
      <header className="topbar">
        <div className="command-panel">
          <div className="command-input">
            <Sparkles size={18} aria-hidden="true" />
            <input
              ref={inputRef}
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="Ask Booski anything or give it a task... (AI arrives in Phase 3)"
              aria-label="Ask Booski anything or give it a task (preview: AI arrives in Phase 3)"
            />
            <button type="button" className="send-button" onClick={submit} aria-label="Send command">
              <Send size={20} aria-hidden="true" />
            </button>
          </div>
          <div className="command-actions">
            {quickActions.map(({ label, prefix, icon: ActionIcon }) => (
              <button type="button" key={label} onClick={() => startCommand(prefix)}>
                <ActionIcon size={14} aria-hidden="true" /> {label}
              </button>
            ))}
          </div>
        </div>
        <div className="top-actions">
          <button
            type="button"
            className="icon-button"
            onClick={() => setShowNotifications((open) => !open)}
            aria-label={waiting ? `Notifications: ${waiting} approval requests waiting for you` : "Notifications"}
            aria-expanded={showNotifications}
            aria-controls={popoverId}
          >
            <Bell size={19} aria-hidden="true" />
            {waiting > 0 && <i aria-hidden="true" />}
          </button>
          <button type="button" className="icon-button" onClick={() => navigate(paths.settings)} aria-label="Settings">
            <Settings size={19} aria-hidden="true" />
          </button>
          <div className="mini-avatar" aria-hidden="true">{initials || "♛"}</div>
          {showNotifications && (
            <div className="notification-pop" id={popoverId} role="region" aria-label="Notifications">
              <b>Notifications</b>
              {waiting > 0 ? (
                <p>
                  <button type="button" className="inline-link" onClick={() => { setShowNotifications(false); navigate(paths.approvals); }}>
                    {waiting} approval {waiting === 1 ? "request is" : "requests are"} waiting for your review
                  </button>
                </p>
              ) : (
                <p>Nothing is waiting for you.</p>
              )}
            </div>
          )}
        </div>
      </header>
      {lastCommand && (
        <div className="last-command">
          <Sparkles size={15} aria-hidden="true" /> Preview only, not sent: <b>{lastCommand}</b>
          <button type="button" onClick={() => setLastCommand("")} aria-label="Dismiss last command">
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}
    </>
  );
}
