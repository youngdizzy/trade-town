/**
 * True while a real text input has keyboard focus (an `<input>`,
 * `<textarea>`, or `<select>`) — used to give a focused form field
 * priority over WASD movement across every Command Center panel (Mentor's
 * QOTD textarea, Calendar's event form, Treasury's amount inputs, the
 * Knowledge Graph search box, ...) with one generic DOM check instead of
 * per-component wiring. See GameManager.ts's `movementActive`.
 */
export function isTypingInTextField(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}
