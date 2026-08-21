import { useEffect, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import { ConfirmDialog } from "./ConfirmDialog";

/**
 * Safe "New Game" confirmation — protects a player from accidentally
 * losing their place mid-click on the title screen. Rendered as a
 * top-level overlay in App.tsx, same pattern as EmergencyStopConfirm.tsx
 * (a Phaser-scene-triggered React dialog): MainMenuScene.ts owns the real
 * save-exists check and the actual scene transition; this component only
 * owns the dialog itself and reports the player's choice back over
 * EventBus, exactly the request/response shape "ui:emergencyStopConfirm"
 * already established.
 *
 * IMPORTANT — what this dialog can honestly claim: research before
 * building this confirmed "New Game" does not call any backend endpoint
 * today — MainMenuScene.startNewGame() only starts LobbyScene client-side
 * (see that file). The backend's company/agents/strategies/trades are a
 * single always-on save that is never reset, deleted, or overwritten by
 * this flow, confirmed or cancelled. This dialog's copy reflects that
 * real behavior — it warns about the *visible* disorientation of landing
 * back at a fresh Lobby (and about the next autosave overwriting the
 * player's saved position/scene), never a fabricated "your company will
 * be deleted" claim that isn't true in this codebase.
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
      body={`You have an existing company in progress (Day ${day}). Starting a new game takes you to a fresh Lobby view — it does not delete or reset your company (your agents, strategies, and trades keep running exactly as they are), but your saved player position will be overwritten the next time the game autosaves. Choose Cancel and use Continue instead if you want to return to where you left off.`}
      confirmLabel="START NEW GAME"
      tone="gold"
      onConfirm={() => respond(true)}
      onCancel={() => respond(false)}
    />
  );
}
