import { useCallback, useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PriorityTier, SituationRoomField, SituationRoomSeverity, SituationRoomState } from "@/types";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations
 * (backend/app/situation_room.py). The Executive Situation Room: a
 * single screen answering "what needs my attention right now." Eleven
 * of its thirteen fields reuse an already-real single computed source
 * verbatim; only Pending CEO Decisions and Executive Consensus are
 * computed fresh server-side. Has no WS-broadcast field (computed per
 * request, same on-demand pattern Chapter 73's CompliancePanel already
 * established) — fetched here, with a manual refresh since "what needs
 * my attention" is exactly the kind of read a CEO would want current
 * on demand rather than polled on a timer.
 */

const BAND_TONE: Record<SituationRoomSeverity, "green" | "cyan" | "amber" | "red"> = {
  good: "green",
  caution: "cyan",
  elevated: "amber",
  severe: "red",
  critical: "red",
};

const PRIORITY_TONE: Record<PriorityTier, "red" | "amber" | "cyan" | "neutral"> = {
  critical: "red",
  high: "amber",
  medium: "cyan",
  low: "neutral",
};

function Field({ field }: { field: SituationRoomField }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
      <div className="mb-1 flex items-center justify-between">
        <span className="uppercase tracking-wide text-cmd-textDim">{field.label}</span>
        <StatusPill tone={BAND_TONE[field.band]}>{field.band.toUpperCase()}</StatusPill>
      </div>
      <div className="mb-0.5 font-cmdmono text-cmd-text">{field.value}</div>
      <div className="text-cmd-textDim">{field.detail}</div>
    </div>
  );
}

export function SituationRoomPanel() {
  const { companyHealth, portfolioIntelligence, emergencyStop, tradeProposals, dailyCircuitBreaker } = useGameStore();
  const [room, setRoom] = useState<SituationRoomState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getSituationRoom()
      .then(setRoom)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load the Situation Room."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyHealth.updatedAt, portfolioIntelligence.updatedAt, emergencyStop.active, tradeProposals.length, dailyCircuitBreaker.tier]);

  if (room === null) {
    return error ? (
      <Glass className="p-3">
        <div className="text-[9px] text-cmd-red">{error}</div>
      </Glass>
    ) : (
      <EmptyState>Loading the Executive Situation Room…</EmptyState>
    );
  }

  const fields: SituationRoomField[] = [
    room.companyHealth,
    room.portfolioHealth,
    room.cashPosition,
    room.openRisk,
    room.marketRegime,
    room.tradingMode,
    room.economicHealth,
    room.blackSwanRisk,
    room.executiveConsensus,
    room.pendingCeoDecisions,
    room.brokerStatus,
    room.automationStatus,
    room.emergencyAlerts,
  ];

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Executive Situation Room — complete company awareness, one screen</TerminalLabel>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="rounded-sm border border-cmd-cyan/50 px-2 py-0.5 text-[9px] uppercase tracking-wide text-cmd-cyan hover:bg-cmd-cyan/10 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((f) => (
            <Field key={f.label} field={f} />
          ))}
        </div>
        <div className="mt-2 text-[9px] text-cmd-textDim">Generated {new Date(room.generatedAt).toLocaleString()}</div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>CEO Priority Engine — what needs attention right now</TerminalLabel>
        {room.priorities.length === 0 ? (
          <EmptyState>Nothing needs the CEO's attention right now.</EmptyState>
        ) : (
          <div className="max-h-96 space-y-1.5 overflow-y-auto">
            {room.priorities.map((p) => (
              <div key={p.id} className="flex items-start gap-2 border-b border-cmd-border/50 pb-1.5 last:border-0 text-[9px]">
                <StatusPill tone={PRIORITY_TONE[p.tier]}>{p.tier.toUpperCase()}</StatusPill>
                <div>
                  <div className="text-cmd-text">{p.title}</div>
                  <div className="text-cmd-textDim">{p.detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
