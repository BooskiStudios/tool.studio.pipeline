import { useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "../hooks/useFocusTrap";

interface ModalProps {
  title: string;
  eyebrow?: string;
  description?: ReactNode;
  /** Must be stable (e.g. from useCallback or a state setter) to avoid re-running focus setup. */
  onClose: () => void;
  children?: ReactNode;
  /** "wide" for detail views and longer forms. */
  size?: "normal" | "wide";
}

/**
 * Accessible dialog: labelled for assistive tech, traps focus, closes on Escape
 * or backdrop click, and restores focus when closed. Mark the element that
 * should receive initial focus with `data-autofocus`.
 */
export function Modal({ title, eyebrow, description, onClose, children, size = "normal" }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  useFocusTrap(dialogRef, onClose);

  return (
    <div
      className="modal-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={size === "wide" ? "modal modal-wide" : "modal"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
      >
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog">
          <X size={18} aria-hidden="true" />
        </button>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2 id={titleId}>{title}</h2>
        {description && <p id={descriptionId}>{description}</p>}
        {children}
      </div>
    </div>
  );
}
