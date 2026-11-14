import { useEffect, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * While mounted: moves focus into `container`, keeps Tab / Shift+Tab inside it,
 * calls `onEscape` on Escape, and returns focus to the previously focused element
 * on unmount.
 *
 * Initial focus goes to the first element marked `data-autofocus`, otherwise the
 * container itself.
 */
export function useFocusTrap(container: RefObject<HTMLElement | null>, onEscape: () => void) {
  useEffect(() => {
    const root = container.current;
    if (!root) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const initial = root.querySelector<HTMLElement>("[data-autofocus]") ?? root;
    initial.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onEscape();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === root)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [container, onEscape]);
}
