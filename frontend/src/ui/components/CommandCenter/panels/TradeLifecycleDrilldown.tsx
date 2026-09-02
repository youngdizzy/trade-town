import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { TradeLifecycleRecord } from "@/types";
import { EmptyState, StatusPill, TerminalLabel } from "../ui";

/** CEO directive "TradeTown — Paper Trading Performance & Evidence
 * Reporting 1.0," Phase 18 — "Selecting a trade should connect to...
 * Reuse the existing Canonical Trade Lifecycle API. Do not create a
 * second trade-detail system." This is that reuse: the real
 * GET /api/trades/{tradeId}/lifecycle endpoint (built by the Canonical
 * Trade Lifecycle 1.0 milestone, never surfaced in the frontend across
 * two prior milestones) rendered inline, one stage at a time, with the
 * same honest available/unavailable framing the backend itself already
 * discloses — never a fabricated stage or timestamp.
 */
const STATUS_TONE = {
  closed: "green",
  open: "cyan",
  rejected: "red",
  pending: "amber",
} as const;

export function TradeLifecycleDrilldown({ tradeId, onClose }: { tradeId: string; onClose: () => void }) {
  const [record, setRecord] = useState<TradeLifecycleRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRecord(null);
    setError(null);
    api
      .getTradeLifecycle(tradeId)
      .then((r) => !cancelled && setRecord(r))
      .catch(() => !cancelled && setError("Could not load a lifecycle for this trade."));
    return () => {
      cancelled = true;
    };
  }, [tradeId]);

  return (
    <div className="mt-1 rounded-sm border border-cmd-cyan/30 bg-cmd-bg/60 p-2 text-[9px]">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Trade Lifecycle</TerminalLabel>
        <button type="button" onClick={onClose} className="text-cmd-textDim hover:text-cmd-text">
          Close ✕
        </button>
      </div>
      {error !== null ? (
        <div className="text-cmd-red">{error}</div>
      ) : record === null ? (
        <EmptyState>Loading…</EmptyState>
      ) : (
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-cmdmono text-cmd-cyan">{record.symbol}</span>
            <StatusPill tone={STATUS_TONE[record.status]}>{record.status.toUpperCase()}</StatusPill>
            <span className="text-cmd-textDim">root id: {record.tradeRootId}</span>
          </div>
          <div className="space-y-1">
            {record.stages.map((s) => (
              <div key={s.stage} className="flex items-start gap-2">
                <span className={s.available ? "text-cmd-green" : "text-cmd-textDim"}>{s.available ? "✓" : "—"}</span>
                <div className="flex-1">
                  <div className={s.available ? "text-cmd-text" : "text-cmd-textDim"}>
                    {s.label}
                    {s.occurredAt !== null && <span className="ml-2 text-cmd-textDim">{new Date(s.occurredAt).toLocaleString()}</span>}
                  </div>
                  <div className="text-cmd-textDim">{s.note}</div>
                </div>
              </div>
            ))}
          </div>
          {record.institutionalMemory.length > 0 && (
            <div className="border-t border-cmd-border/50 pt-1 text-cmd-textDim">
              {record.institutionalMemory.length} institutional-memory entr{record.institutionalMemory.length === 1 ? "y" : "ies"} promoted from this trade&apos;s outcome.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
