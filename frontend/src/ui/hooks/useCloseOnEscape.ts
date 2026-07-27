import { useEffect } from "react";

/** Lets a full-screen overlay close with Escape, not just a mouse click on its Close button — see Newspaper/CompanyMemory/CoachDashboard. */
export function useCloseOnEscape(isOpen: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);
}
