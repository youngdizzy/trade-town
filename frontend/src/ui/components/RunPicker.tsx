import { useEffect, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import type { RunSummary } from "@/types";

/**
 * CEO directive "Proper Multi-Run / Save Isolation System" — "Continue"
 * shows this only when more than one real, persisted run exists (see
 * MainMenuScene.ts's continueGame()); with exactly one it loads that run
 * directly, same minimal-friction behavior as before this feature. Same
 * Phaser-scene-triggered React overlay pattern as NewGameConfirm.tsx/
 * EmergencyStopConfirm.tsx, and the same pixel/parchment visual language
 * ConfirmDialog.tsx already established, reused directly here rather
 * than a new visual style.
 */
export function RunPicker() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    const handler = (payload: { runs: RunSummary[] } | null) => setRuns(payload?.runs ?? null);
    EventBus.on("ui:runPicker", handler);
    return () => EventBus.off("ui:runPicker", handler);
  }, []);

  if (runs === null) return null;

  const choose = (runId: string | null) => {
    setRuns(null);
    EventBus.emit("ui:runPickerResult", { runId });
  };

  return (
    <div className="pointer-events-auto absolute inset-0 z-[60] flex items-center justify-center bg-black/70 font-pixel text-[11px]">
      <div className="w-96 rounded bg-panel p-5 text-parchment shadow-pixel">
        <h2 className="mb-3 text-center text-gold">Continue which run?</h2>
        <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {runs.map((run) => (
            <button
              key={run.runId}
              type="button"
              onClick={() => choose(run.runId)}
              className="rounded bg-panelLight px-3 py-2 text-left shadow-pixel transition-colors hover:bg-panelLight/70"
            >
              <span className="block">{run.displayName}</span>
              <span className="block text-[9px] leading-relaxed opacity-70">
                {run.currentDay !== null ? `Day ${run.currentDay}` : "Day unavailable"} · last played{" "}
                {new Date(run.lastPlayedAt).toLocaleString()}
              </span>
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => choose(null)}
          className="mt-3 w-full rounded bg-panelLight px-3 py-2 text-center text-parchment shadow-pixel transition-colors hover:bg-panelLight/70"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
