import { useGameStore } from "@/ui/hooks/useGameStore";
import { TimeManager } from "@/game/systems/TimeManager";

export function TopStatusBar() {
  const { time, scout, netConnected, currentScene } = useGameStore();
  const inGame = currentScene !== "MainMenuScene";
  if (!inGame) return null;

  return (
    <div className="pointer-events-none absolute left-0 right-0 top-0 flex items-center justify-between gap-4 bg-gradient-to-b from-black/70 to-transparent px-4 py-2 font-pixel text-[11px] text-parchment">
      <div className="pointer-events-auto flex items-center gap-3 rounded bg-panel/80 px-3 py-1.5 shadow-pixel">
        <span className="text-gold">TradeTown HQ</span>
        <span className="opacity-70">{TimeManager.formatClock(time)}</span>
      </div>

      {scout && (
        <div className="pointer-events-auto flex items-center gap-4 rounded bg-panel/80 px-3 py-1.5 shadow-pixel">
          <span className="text-gold">Scout</span>
          <StatBar label="Mood" value={scout.mood} color="bg-bullish" />
          <StatBar label="Energy" value={scout.energy} color="bg-gold" />
          <span className="max-w-[220px] truncate opacity-80" title={scout.currentTask}>
            {scout.currentTask}
          </span>
        </div>
      )}

      <div className="pointer-events-auto flex items-center gap-2 rounded bg-panel/80 px-3 py-1.5 shadow-pixel">
        <span
          className={`h-2 w-2 rounded-full ${netConnected ? "bg-bullish" : "bg-bearish"}`}
          title={netConnected ? "Connected to backend" : "Offline (local simulation)"}
        />
        <span className="opacity-70">{netConnected ? "Live" : "Offline"}</span>
      </div>
    </div>
  );
}

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5" title={`${label}: ${Math.round(value)}`}>
      <span className="opacity-60">{label}</span>
      <div className="h-2 w-16 overflow-hidden rounded-sm bg-ink">
        <div className={`h-full ${color}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}
