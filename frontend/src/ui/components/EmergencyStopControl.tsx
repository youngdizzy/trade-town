import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency Stop
 * button, rendered in TopStatusBar so it stays visible from every scene,
 * never inside a Command Center tab (see this chapter's own migration
 * plan for why). Only opens the confirmation dialog — the actual
 * activate/resume call lives in the top-level EmergencyStopConfirm
 * overlay (see that component's own doc comment for why it can't live
 * nested here: an absolute inset-0 dialog needs a full-viewport
 * positioned ancestor, not TopStatusBar's own small flex row).
 */
export function EmergencyStopControl() {
  const { emergencyStop } = useGameStore();

  return emergencyStop.active ? (
    <button
      type="button"
      onClick={() => EventBus.emit("ui:emergencyStopConfirm", { pending: "resume" })}
      className="pointer-events-auto flex min-h-[44px] animate-pulse items-center gap-1.5 rounded bg-bearish px-3 py-1.5 text-ink shadow-pixel sm:min-h-0"
      title="Emergency Stop is active — trading is halted. Only the CEO can resume."
    >
      <span className="h-2 w-2 rounded-full bg-ink" />
      EMERGENCY — RESUME TRADING
    </button>
  ) : (
    <button
      type="button"
      onClick={() => EventBus.emit("ui:emergencyStopConfirm", { pending: "activate" })}
      className="pointer-events-auto flex min-h-[44px] items-center rounded border border-bearish/60 px-3 py-1.5 text-bearish shadow-pixel transition-colors hover:bg-bearish hover:text-ink sm:min-h-0"
      title="Halt all trading immediately"
    >
      EMERGENCY STOP
    </button>
  );
}
