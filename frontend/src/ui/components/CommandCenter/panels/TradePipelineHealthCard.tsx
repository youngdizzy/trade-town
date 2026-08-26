import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { TradePipelineHealthSnapshot } from "@/types";
import { Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * CEO directive "Professional Quant Firm Phase 41-45," Critical Task
 * #0 — the real trade-flow funnel diagnostic (backend/app/trade_
 * pipeline_health.py). On-demand, no WS-broadcast field backs it (the
 * same pattern DisciplinePanel's Exit Efficiency card already uses).
 * DIAGNOSTIC ONLY — this never gates, scores, or influences any real
 * trading decision; see the snapshot's own dataHonestyNote for exactly
 * which counts are capped rolling windows rather than full-lifetime
 * totals.
 *
 * Extracted from RiskPanel.tsx (CEO directive "Live Desk + Trade
 * Observability") so the Live Desk can answer "why aren't we trading
 * right now?" (Phase 11/12's ask) with this exact real diagnostic
 * instead of a second, parallel implementation.
 */
export function TradePipelineHealthCard() {
  const [snapshot, setSnapshot] = useState<TradePipelineHealthSnapshot | null>(null);
  useEffect(() => {
    api.getPipelineHealth().then(setSnapshot).catch(() => undefined);
  }, []);

  if (!snapshot) return null;

  const funnel: [string, number][] = [
    ["Research Signals", snapshot.completedResearchSignals],
    ["Pending Proposals", snapshot.pendingProposals],
    ["Resolved Decisions", snapshot.resolvedDecisions],
    ["Trades Executed", snapshot.tradesExecuted],
    ["No-Trade Decisions", snapshot.noTradeDecisions],
    ["Opportunity Rejections", snapshot.opportunityRejections],
    ["Gatekeeper Rejections", snapshot.gatekeeperRejections],
  ];
  const maxCount = Math.max(1, ...funnel.map(([, count]) => count));
  const topReasons = [...snapshot.reasonCodeBreakdown].sort((a, b) => b.count - a.count).slice(0, 8);

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Trade Pipeline Health — real funnel diagnostics</TerminalLabel>
        <StatusPill tone="neutral">diagnostic only</StatusPill>
      </div>
      <div className="space-y-1">
        {funnel.map(([label, count]) => (
          <div key={label} className="flex items-center gap-2 text-[9px]">
            <span className="w-32 shrink-0 text-cmd-textDim">{label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-sm bg-cmd-bg/60">
              <div className="h-full bg-cmd-cyan/60" style={{ width: `${(count / maxCount) * 100}%` }} />
            </div>
            <span className="w-8 shrink-0 text-right tabular-nums text-cmd-text">{count}</span>
          </div>
        ))}
      </div>
      {topReasons.length > 0 && (
        <div className="mt-2">
          <div className="mb-1 text-[9px] text-cmd-textDim">Most common no-trade reasons</div>
          <div className="flex flex-wrap gap-1">
            {topReasons.map((t) => (
              <span key={t.code} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-1.5 py-0.5 text-[8px] text-cmd-textDim">
                {t.code} <span className="text-cmd-text">×{t.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{snapshot.dataHonestyNote}</p>
    </Glass>
  );
}
