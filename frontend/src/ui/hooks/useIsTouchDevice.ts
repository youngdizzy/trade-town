import { useEffect, useState } from "react";

/**
 * Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations.
 * A real, live `(pointer: coarse)` media-query read (touchscreen with no
 * precise pointer), not a user-agent sniff — so a touch-capable laptop
 * with a mouse attached still gets desktop controls, and the check stays
 * live if a device's input capability changes (e.g. a tablet docked to a
 * mouse mid-session).
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(() => window.matchMedia("(pointer: coarse)").matches);

  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse)");
    const onChange = () => setIsTouch(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return isTouch;
}
