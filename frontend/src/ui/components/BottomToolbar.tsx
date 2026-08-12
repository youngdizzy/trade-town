import { useGameStore } from "@/ui/hooks/useGameStore";
import { SaveManager } from "@/game/systems/SaveManager";
import { GameManager } from "@/game/systems/GameManager";
import { EventBus } from "@/game/systems/EventBus";
import { SettingsManager } from "@/game/systems/SettingsManager";
import { useIsTouchDevice } from "@/ui/hooks/useIsTouchDevice";

export function BottomToolbar() {
  const { save, currentScene, paused, settings } = useGameStore();
  const isTouch = useIsTouchDevice();
  const inGame = currentScene !== "MainMenuScene";
  if (!inGame) return null;

  // Design Bible Chapter 73.5 — on a touch device this row sits above
  // MobileTouchControls' joystick/interact band (which owns the true
  // bottom edge) instead of overlapping it, and shows only what a CEO
  // actually needs one tap from while away from the computer — Command
  // Center (the primary mobile surface), Search, and Pause. Save/Load/
  // Memory/Coach/Dashboard/Settings/Work Mode stay exactly as they are
  // on desktop, just not duplicated into this already-crowded mobile
  // band; every one of them is still reachable, either automatically
  // (autosave/load-on-boot) or through the Command Center itself.
  return (
    <div
      className={`pointer-events-none absolute left-0 right-0 flex items-center justify-center gap-2 bg-gradient-to-t from-black/70 to-transparent px-4 py-3 font-pixel text-[11px] ${
        isTouch ? "bottom-[152px]" : "bottom-0"
      }`}
    >
      <div className="pointer-events-auto flex flex-wrap items-center justify-center gap-2 rounded bg-panel/90 px-3 py-2 shadow-pixel">
        {!isTouch && (
          <>
            <ToolbarButton label="Save" onClick={() => void SaveManager.save()} />
            <ToolbarButton label="Load" onClick={() => void SaveManager.load()} />
            <ToolbarButton label="Memory" onClick={() => EventBus.emit("ui:companyMemory", { open: true })} />
            <ToolbarButton label="Coach" onClick={() => EventBus.emit("ui:coachDashboard", { open: true })} />
            <ToolbarButton label="Dashboard" onClick={() => EventBus.emit("ui:brainRoomHud", { open: true })} />
          </>
        )}
        <ToolbarButton label="Command ⌁" onClick={() => EventBus.emit("ui:commandCenter", { open: true, mode: "quick" })} />
        <ToolbarButton label="Search 🔍" onClick={() => EventBus.emit("ui:commandPalette", { open: true })} />
        {!isTouch && <ToolbarButton label="Settings" onClick={() => EventBus.emit("ui:settings", { open: true })} />}
        <ToolbarButton label={paused ? "Resume" : "Pause"} onClick={() => GameManager.getInstance()?.togglePause()} />
        {!isTouch && <WorkModeToggle workMode={settings.workMode} />}
        <SaveStatusIndicator status={save.status} error={save.error} />
      </div>
    </div>
  );
}

/** v0.7 Feature 37 — the Work Mode System. Always visible, persistent
 * until the CEO changes it (never an automatic timer) — a real,
 * client-authoritative settings field the same way operatingMode/
 * companyPriority already are, read every tick by nexus.py's tick(). */
function WorkModeToggle({ workMode }: { workMode: "work" | "rest" }) {
  const isWork = workMode === "work";
  return (
    <button
      type="button"
      onClick={() => SettingsManager.update({ workMode: isWork ? "rest" : "work" })}
      title={isWork ? "Switch to Rest Mode" : "Switch to Work Mode"}
      className={`rounded px-3 py-1.5 shadow-pixel transition-colors active:translate-y-px ${
        isWork ? "bg-bullish/80 text-ink hover:bg-bullish" : "bg-indigo-400/80 text-ink hover:bg-indigo-400"
      }`}
    >
      {isWork ? "🟢 WORK MODE ACTIVE" : "🌙 REST MODE ACTIVE"}
    </button>
  );
}

function ToolbarButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-[44px] rounded bg-panelLight px-3 py-1.5 text-parchment shadow-pixel transition-colors hover:bg-gold hover:text-ink active:translate-y-px sm:min-h-0"
    >
      {label}
    </button>
  );
}

function SaveStatusIndicator({ status, error }: { status: string; error: string | null }) {
  const text = status === "saving" ? "Saving…" : status === "saved" ? "Saved" : status === "error" ? "Save failed" : "";
  if (!text) return null;
  return (
    <span className={`px-2 ${status === "error" ? "text-bearish" : "text-bullish"}`} title={error ?? undefined}>
      {text}
    </span>
  );
}
