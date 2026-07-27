import { useEffect } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { useCloseOnEscape } from "@/ui/hooks/useCloseOnEscape";
import { EventBus } from "@/game/systems/EventBus";
import { QuickView } from "./QuickView";
import { FullCommandCenter } from "./FullCommandCenter";

/**
 * The Global Command Center (v0.6.1) — an application-level overlay
 * reachable from anywhere in the game (Lobby, any office, Brain Room),
 * not a room-specific panel. It's a pure React layer over the existing
 * `world:overlayOpen`/`GameManager.worldActive` mechanism every other
 * menu (Newspaper, Company Memory, Coach Dashboard, Brain Room HUD)
 * already uses — see gameStore.ts's `setOverlay` — so opening it never
 * touches the running Phaser scene: no reload, no player-position reset,
 * no agent-state reset, and the world behind it is provably inert (the
 * scene's own `update()` skips input processing entirely while any
 * overlay is open) rather than merely hidden behind a dimmed backdrop.
 *
 * Tab toggles it open/closed from any screen; Escape (via
 * useCloseOnEscape, same hook every other overlay uses) always closes it.
 * Tab's browser-native behavior (focus navigation) is suppressed with
 * preventDefault so it doesn't fight the toggle.
 */
export function CommandCenter() {
  const { commandCenterOpen, commandCenterMode } = useGameStore();
  const close = () => EventBus.emit("ui:commandCenter", { open: false });
  const openQuick = () => EventBus.emit("ui:commandCenter", { open: true, mode: "quick" });
  const openFull = () => EventBus.emit("ui:commandCenter", { open: true, mode: "full" });

  useCloseOnEscape(commandCenterOpen, close);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== "Tab") return;
      e.preventDefault();
      if (commandCenterOpen) close();
      else openQuick();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [commandCenterOpen]);

  if (!commandCenterOpen) return null;

  return (
    <div className="pointer-events-auto absolute inset-0 z-50 flex items-center justify-center bg-black/70 p-[6vh] font-cmdmono text-[11px] text-cmd-text">
      <div className="relative flex h-full w-full max-w-[1400px] flex-col overflow-hidden rounded-md border border-cmd-cyan/30 bg-cmd-bg shadow-cmd-cyan">
        <ScanlineOverlay />
        {commandCenterMode === "quick" ? <QuickView onExpand={openFull} /> : <FullCommandCenter onCollapse={openQuick} onClose={close} />}
      </div>
    </div>
  );
}

/** Faint static scanline texture — decorative only, `pointer-events-none` so it never intercepts clicks meant for the panels underneath. */
function ScanlineOverlay() {
  return (
    <div
      className="pointer-events-none absolute inset-0 opacity-[0.04]"
      style={{
        backgroundImage: "repeating-linear-gradient(0deg, #fff 0px, #fff 1px, transparent 1px, transparent 3px)",
      }}
    />
  );
}
