/**
 * Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations.
 * A tiny, reactive-free singleton bridging the on-screen touch joystick
 * (a React component, MobileTouchControls.tsx) into InputManager's
 * existing MoveVector — the exact same interface WASD/arrows already
 * feed, so PlayerController/collision/animation code needs zero changes
 * to support touch. Never a second movement system.
 */

const state = { x: 0, y: 0 };
let interactRequested = false;

export function setTouchMoveVector(x: number, y: number): void {
  state.x = x;
  state.y = y;
}

export function getTouchMoveVector(): { x: number; y: number } {
  return state;
}

export function requestTouchInteract(): void {
  interactRequested = true;
}

/** Same one-shot semantics as Phaser's Key.JustDown — cleared on read. */
export function consumeTouchInteract(): boolean {
  if (!interactRequested) return false;
  interactRequested = false;
  return true;
}
