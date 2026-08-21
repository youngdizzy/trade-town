import { useEffect, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import { ConfirmDialog } from "./ConfirmDialog";

/**
 * Safe "New Game" confirmation — protects a player from accidentally
 * leaving the run they're currently on. Rendered as a top-level overlay
 * in App.tsx, same pattern as EmergencyStopConfirm.tsx (a Phaser-scene-
 * triggered React dialog): MainMenuScene.ts owns the real run-listing
 * check and the actual run creation/scene transition; this component
 * only owns the dialog itself and reports the player's choice back over
 * EventBus, exactly the request/response shape "ui:emergencyStopConfirm"
 * already established.
 *
 * CEO directive "Proper Multi-Run / Save Isolation System" — "New Game"
 * now genuinely creates a separate, independently-persisted run
 * (POST /api/runs) rather than the earlier purely-cosmetic scene
 * transition, so this dialog's copy changed to match: it no longer needs
 * to reassure the player nothing was ever actually at risk (that
 * reassurance is real infrastructure now, not just true by accident) —
 * it states plainly that a new, separate run is being created and the
 * current one stays fully intact and reachable via Continue.
 */
export function NewGameConfirm() {
  const [day, setDay] = useState<number | null>(null);

  useEffect(() => {
    const handler = (payload: { day: number } | null) => setDay(payload?.day ?? null);
    EventBus.on("ui:newGameConfirm", handler);
    return () => EventBus.off("ui:newGameConfirm", handler);
  }, []);

  if (day === null) return null;

  const respond = (confirmed: boolean) => {
    setDay(null);
    EventBus.emit("ui:newGameConfirmResult", { confirmed });
  };

  return (
    <ConfirmDialog
      title="Start a new game?"
      body={`You currently have a run at Day ${day}. Starting a new game creates a separate, independent Day 1 run — your current run is not deleted, reset, or modified in any way, and stays reachable from Continue.`}
      confirmLabel="START NEW GAME"
      tone="gold"
      onConfirm={() => respond(true)}
      onCancel={() => respond(false)}
    />
  );
}
