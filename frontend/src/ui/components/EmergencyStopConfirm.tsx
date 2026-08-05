import { useEffect, useState } from "react";
import { EventBus } from "@/game/systems/EventBus";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import { ConfirmDialog } from "./ConfirmDialog";

/**
 * Design Bible Chapter 67 (TTOS) Part 3 — owns the actual Emergency Stop
 * confirmation dialog and the activate/resume API calls, rendered as a
 * top-level overlay in App.tsx (same pattern as CommandCenter/
 * ExecutiveVoting: a full-viewport absolute overlay needs a full-viewport
 * positioned ancestor, which App.tsx's own root div is — TopStatusBar's
 * small flex row is not). EmergencyStopControl.tsx (rendered inside
 * TopStatusBar) only ever emits "ui:emergencyStopConfirm" to open this.
 */
export function EmergencyStopConfirm() {
  const [pending, setPending] = useState<"activate" | "resume" | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const handler = ({ pending }: { pending: "activate" | "resume" | null }) => setPending(pending);
    EventBus.on("ui:emergencyStopConfirm", handler);
    return () => EventBus.off("ui:emergencyStopConfirm", handler);
  }, []);

  if (pending === null) return null;

  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res = pending === "activate" ? await api.activateEmergencyStop() : await api.resumeTradingAfterEmergencyStop();
      NexusManager.setEmergencyStop(res.emergencyStop);
    } finally {
      setBusy(false);
      setPending(null);
    }
  };

  return pending === "activate" ? (
    <ConfirmDialog
      title="Activate Emergency Stop?"
      body="This immediately halts all new trading — no new trade proposals will be generated, and every pending proposal (including your own manual calls) stays frozen until you resume. Research, monitoring, dashboards, and notifications keep running. Only you can resume trading."
      confirmLabel="ACTIVATE EMERGENCY STOP"
      tone="red"
      onConfirm={() => void confirm()}
      onCancel={() => setPending(null)}
    />
  ) : (
    <ConfirmDialog
      title="Resume trading?"
      body="This lifts the Emergency Stop — new trade proposals resume, and every proposal frozen while it was active becomes actionable again."
      confirmLabel="RESUME TRADING"
      tone="gold"
      onConfirm={() => void confirm()}
      onCancel={() => setPending(null)}
    />
  );
}
