import { useGameStore } from "@/ui/hooks/useGameStore";
import { GameManager } from "@/game/systems/GameManager";
import { SaveManager } from "@/game/systems/SaveManager";
import { EventBus } from "@/game/systems/EventBus";

export function PauseMenu() {
  const { paused } = useGameStore();
  if (!paused) return null;

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 font-pixel text-[11px]">
      <div className="w-72 rounded bg-panel p-5 text-center text-parchment shadow-pixel">
        <h2 className="mb-4 text-gold">Paused</h2>
        <div className="flex flex-col gap-2">
          <MenuButton label="Resume" onClick={() => GameManager.getInstance()?.togglePause()} />
          <MenuButton label="Save" onClick={() => void SaveManager.save()} />
          <MenuButton label="Campus Map" onClick={() => EventBus.emit("ui:campusMap", { open: true })} />
          <MenuButton label="Settings" onClick={() => EventBus.emit("ui:settings", { open: true })} />
        </div>
      </div>
    </div>
  );
}

function MenuButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded bg-panelLight px-3 py-2 text-parchment shadow-pixel transition-colors hover:bg-gold hover:text-ink"
    >
      {label}
    </button>
  );
}
