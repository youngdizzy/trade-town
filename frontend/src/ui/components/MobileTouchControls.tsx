import { useRef, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useIsTouchDevice } from "@/ui/hooks/useIsTouchDevice";
import { requestTouchInteract, setTouchMoveVector } from "@/game/systems/TouchMoveState";

const BASE_RADIUS = 52;
const KNOB_RADIUS = 24;

/**
 * Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations.
 * A real on-screen joystick + interact button for touch devices, feeding
 * the exact same MoveVector/interact-pressed interface WASD/E already
 * do (see InputManager.ts) — never a second, competing movement system,
 * and never any change to existing collision/steering code. Only ever
 * rendered on a real `(pointer: coarse)` touch device (useIsTouchDevice)
 * and hidden behind any real overlay, matching "no keyboard/mouse
 * required, but don't clutter the screen while a dialog is open."
 */
export function MobileTouchControls() {
  const isTouch = useIsTouchDevice();
  const {
    currentScene,
    paused,
    settingsOpen,
    newspaperOpen,
    companyMemoryOpen,
    alertCenterOpen,
    coachDashboardOpen,
    brainRoomHudOpen,
    commandCenterOpen,
    campusMapOpen,
    breakthroughOpen,
    executiveVotingOpen,
  } = useGameStore();

  const anyOverlayOpen =
    paused ||
    settingsOpen ||
    newspaperOpen ||
    companyMemoryOpen ||
    alertCenterOpen ||
    coachDashboardOpen ||
    brainRoomHudOpen ||
    commandCenterOpen ||
    campusMapOpen ||
    breakthroughOpen ||
    executiveVotingOpen;

  const baseRef = useRef<HTMLDivElement | null>(null);
  const [knob, setKnob] = useState({ x: 0, y: 0 });
  const activePointerId = useRef<number | null>(null);

  if (!isTouch || currentScene === "MainMenuScene" || anyOverlayOpen) return null;

  const updateFromPointer = (clientX: number, clientY: number) => {
    const base = baseRef.current;
    if (!base) return;
    const rect = base.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let dx = clientX - cx;
    let dy = clientY - cy;
    const dist = Math.hypot(dx, dy);
    const clamped = Math.min(dist, BASE_RADIUS);
    if (dist > 0) {
      dx = (dx / dist) * clamped;
      dy = (dy / dist) * clamped;
    }
    setKnob({ x: dx, y: dy });
    setTouchMoveVector(dist > 0 ? dx / BASE_RADIUS : 0, dist > 0 ? dy / BASE_RADIUS : 0);
  };

  const endDrag = () => {
    activePointerId.current = null;
    setKnob({ x: 0, y: 0 });
    setTouchMoveVector(0, 0);
  };

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-40 flex items-end justify-between px-6 pb-8">
      <div
        ref={baseRef}
        className="pointer-events-auto relative touch-none select-none rounded-full border-2 border-parchment/40 bg-black/35 backdrop-blur-sm"
        style={{ width: BASE_RADIUS * 2, height: BASE_RADIUS * 2 }}
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture(e.pointerId);
          activePointerId.current = e.pointerId;
          updateFromPointer(e.clientX, e.clientY);
        }}
        onPointerMove={(e) => {
          if (activePointerId.current !== e.pointerId) return;
          updateFromPointer(e.clientX, e.clientY);
        }}
        onPointerUp={(e) => {
          if (activePointerId.current !== e.pointerId) return;
          endDrag();
        }}
        onPointerCancel={endDrag}
        aria-label="Move"
        role="button"
      >
        <div
          className="absolute rounded-full bg-parchment/70 shadow-pixel"
          style={{
            width: KNOB_RADIUS * 2,
            height: KNOB_RADIUS * 2,
            left: BASE_RADIUS - KNOB_RADIUS + knob.x,
            top: BASE_RADIUS - KNOB_RADIUS + knob.y,
          }}
        />
      </div>
      <button
        type="button"
        className="pointer-events-auto touch-none select-none rounded-full border-2 border-gold/70 bg-black/35 font-pixel text-parchment shadow-pixel backdrop-blur-sm active:bg-gold/30"
        style={{ width: 72, height: 72 }}
        onPointerDown={(e) => {
          e.preventDefault();
          requestTouchInteract();
        }}
      >
        E
      </button>
    </div>
  );
}
