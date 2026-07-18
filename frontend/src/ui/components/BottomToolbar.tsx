import { useGameStore } from "@/ui/hooks/useGameStore";
import { SaveManager } from "@/game/systems/SaveManager";
import { GameManager } from "@/game/systems/GameManager";
import { EventBus } from "@/game/systems/EventBus";

export function BottomToolbar() {
  const { save, currentScene, paused } = useGameStore();
  const inGame = currentScene !== "MainMenuScene";
  if (!inGame) return null;

  return (
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 flex items-center justify-center gap-2 bg-gradient-to-t from-black/70 to-transparent px-4 py-3 font-pixel text-[11px]">
      <div className="pointer-events-auto flex items-center gap-2 rounded bg-panel/90 px-3 py-2 shadow-pixel">
        <ToolbarButton label="Save" onClick={() => void SaveManager.save()} />
        <ToolbarButton label="Load" onClick={() => void SaveManager.load()} />
        <ToolbarButton label="Memory" onClick={() => EventBus.emit("ui:companyMemory", { open: true })} />
        <ToolbarButton label="Coach" onClick={() => EventBus.emit("ui:coachDashboard", { open: true })} />
        <ToolbarButton label="Settings" onClick={() => EventBus.emit("ui:settings", { open: true })} />
        <ToolbarButton label={paused ? "Resume" : "Pause"} onClick={() => GameManager.getInstance()?.togglePause()} />
        <SaveStatusIndicator status={save.status} error={save.error} />
      </div>
    </div>
  );
}

function ToolbarButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded bg-panelLight px-3 py-1.5 text-parchment shadow-pixel transition-colors hover:bg-gold hover:text-ink active:translate-y-px"
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
