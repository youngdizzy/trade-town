import { useEffect, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";

/**
 * v0.7 — Input Priority fix. "Press E to Talk" — the one piece the
 * interaction system was actually missing (proximity detection, the E
 * key, and real dialogue all already worked everywhere an agent exists;
 * see RoomScene.ts's `nearestAgent()`/`interactPressed`). Driven by
 * RoomScene's `interaction:available` EventBus signal rather than reading
 * the store directly, since this is transient per-frame proximity state,
 * not persisted game state.
 */
export function InteractionPrompt() {
  const [agentName, setAgentName] = useState<string | null>(null);

  useEffect(() => {
    const onAvailable = (payload: { agentName: string } | null) => setAgentName(payload?.agentName ?? null);
    EventBus.on("interaction:available", onAvailable);
    return () => EventBus.off("interaction:available", onAvailable);
  }, []);

  if (!agentName) return null;

  return (
    <div className="pointer-events-none absolute bottom-20 left-0 right-0 flex justify-center font-pixel text-[11px]">
      <div className="rounded border-2 border-gold bg-panel/95 px-4 py-2 text-parchment shadow-pixel">
        <span className="text-gold">[E]</span> Talk to {agentName}
      </div>
    </div>
  );
}
