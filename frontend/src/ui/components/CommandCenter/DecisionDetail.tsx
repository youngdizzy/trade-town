import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { CandlestickChart } from "./CandlestickChart";
import { bearCaseVotes, bullCaseVotes, exitOrdersForPosition, formatMoney, linkedOrderFor, marketRegimeHeuristic, voteDirection } from "./lib/derive";
import { useCandles } from "./lib/useCandles";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "./ui";

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

/**
 * The "why does the AI want this trade?" drill-down. Every section below
 * maps onto a real TradeDecision field — see types.ts — rather than a
 * fabricated structure: Trade Thesis is `finalReasoning`, Bull/Bear Case are
 * the real per-agent votes split by `supportingAgents`/`opposingAgents`,
 * Market Context is `technicalSummary`/`fundamentalSummary` plus the same
 * regime heuristic used elsewhere, and Invalidation reuses `riskSummary`
 * (TradeTown has no separate "what would disprove this" field, but
 * riskSummary is Guardian/Sentinel's honest answer to "what could go
 * wrong"). Final Decision only ever renders APPROVED or REJECTED — a
 * "REDUCED" state is not implemented because nothing in the backend
 * distinguishes a reduced-size trade from a normal one.
 */
export function DecisionDetail({ decision, onClose }: { decision: TradeDecision; onClose: () => void }) {
  const { watchlist, paperPortfolio } = useGameStore();
  const regime = marketRegimeHeuristic(watchlist);
  const bulls = bullCaseVotes(decision);
  const bears = bearCaseVotes(decision);
  const order = linkedOrderFor(decision, paperPortfolio.orders);
  const position = paperPortfolio.positions.find((p) => p.symbol === decision.symbol) ?? null;
  const exitOrders = position ? exitOrdersForPosition(position.id, paperPortfolio.orders) : [];
  const approved = decision.outcome === "trade" && decision.orderId !== null;

  const [timeframe, setTimeframe] = useState("1h");
  const { candles, loading, error } = useCandles(decision.symbol, timeframe, 80);
  const dataStatus = candles[0]?.dataStatus ?? null;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-cmd-bg/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-sm border border-cmd-border bg-cmd-panel shadow-cmd-cyan"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 flex items-center justify-between border-b border-cmd-border bg-cmd-panel/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="font-cmdmono text-xl text-cmd-cyan">{decision.symbol}</span>
            <span className="text-cmd-textDim">{voteDirection(decision.votes)}</span>
            <StatusPill tone={approved ? "green" : "amber"}>{approved ? "APPROVED" : "REJECTED"}</StatusPill>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
          >
            CLOSE ✕
          </button>
        </header>

        <div className="space-y-3 p-4">
          <Glass className="p-3">
            <TerminalLabel>Trade Thesis</TerminalLabel>
            <p className="text-cmd-text">{decision.finalReasoning}</p>
          </Glass>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Glass className="border-cmd-green/30 p-3">
              <TerminalLabel>Bull Case ({bulls.length})</TerminalLabel>
              {bulls.length === 0 ? (
                <EmptyState>No supporting votes.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {bulls.map((v) => (
                    <div key={v.agentId} className="border-b border-cmd-border/50 pb-1 last:border-0">
                      <div className="text-cmd-green">{AGENT_PROFILES[v.agentId].name}</div>
                      <div className="text-[9px] text-cmd-textDim">{v.reason}</div>
                    </div>
                  ))}
                </div>
              )}
            </Glass>

            <Glass className="border-cmd-red/30 p-3">
              <TerminalLabel>Bear Case ({bears.length})</TerminalLabel>
              {bears.length === 0 ? (
                <EmptyState>No opposing votes.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {bears.map((v) => (
                    <div key={v.agentId} className="border-b border-cmd-border/50 pb-1 last:border-0">
                      <div className="text-cmd-red">{AGENT_PROFILES[v.agentId].name}</div>
                      <div className="text-[9px] text-cmd-textDim">{v.reason}</div>
                    </div>
                  ))}
                </div>
              )}
            </Glass>
          </div>

          <Glass className="p-3">
            <TerminalLabel>Market Context</TerminalLabel>
            <DataRow label="Regime" value={regime.label} />
            <div className="mt-1.5 space-y-1 text-[9px] text-cmd-textDim">
              <div>{regime.detail}</div>
              <div className="text-cmd-text">{decision.technicalSummary}</div>
              <div className="text-cmd-text">{decision.fundamentalSummary}</div>
            </div>
          </Glass>

          <Glass className="p-3">
            <div className="mb-2 flex items-center justify-between">
              <TerminalLabel>Chart — {decision.symbol}</TerminalLabel>
              <div className="flex gap-0.5">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    type="button"
                    onClick={() => setTimeframe(tf)}
                    className={`rounded-sm border px-1.5 py-0.5 text-[9px] uppercase transition-colors ${
                      timeframe === tf ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim hover:text-cmd-text"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
            <CandlestickChart
              candles={candles}
              loading={loading}
              error={error}
              dataStatus={dataStatus}
              height={200}
              overlays={{ entry: order?.price, currentPrice: position?.currentPrice }}
            />
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Confidence</TerminalLabel>
            <div className="mb-1 flex items-center justify-between">
              <span className="font-cmdmono text-cmd-text">{Math.round(decision.confidence)}%</span>
              <span className="text-[9px] text-cmd-textDim">
                {decision.supportingAgents.length} supporting · {decision.opposingAgents.length} opposing
              </span>
            </div>
            <Meter value={decision.confidence} tone={decision.confidence >= 70 ? "green" : decision.confidence >= 50 ? "amber" : "red"} />
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Trade Plan</TerminalLabel>
            {order ? (
              <>
                <DataRow label="Side" value={order.side.toUpperCase()} />
                <DataRow label="Order type" value={order.orderType} />
                <DataRow label="Quantity" value={order.quantity} />
                <DataRow label="Price" value={formatMoney(order.price)} />
                <DataRow label="Placed by" value={AGENT_PROFILES[order.placedBy].name} />
                {exitOrders.length > 0 ? (
                  exitOrders.map((eo) => <DataRow key={eo.id} label={`Exit (${eo.orderType})`} value={`${eo.quantity} @ ${formatMoney(eo.price)}`} />)
                ) : (
                  <div className="mt-1 text-[9px] text-cmd-textDim">No stop-loss or take-profit order attached — TradeTown&apos;s auto-trader doesn&apos;t place exit orders yet.</div>
                )}
              </>
            ) : approved ? (
              <EmptyState>
                Order not found — TradeTown&apos;s order log only keeps the most recent 40 resolved orders (see broker.py&apos;s
                MAX_ORDER_LOG), so an older approved decision&apos;s order may have aged out.
              </EmptyState>
            ) : (
              <EmptyState>No order was placed — this decision was not approved.</EmptyState>
            )}
          </Glass>

          <Glass className="p-3">
            <TerminalLabel>Invalidation — What Would Prove This Thesis Wrong?</TerminalLabel>
            <p className="text-cmd-text">{decision.riskSummary}</p>
          </Glass>

          <Glass className={`p-3 ${approved ? "border-cmd-green/40" : "border-cmd-amber/40"}`}>
            <TerminalLabel>Final Decision</TerminalLabel>
            <div className={`font-cmdmono text-lg ${approved ? "text-cmd-green" : "text-cmd-amber"}`}>{approved ? "APPROVED" : "REJECTED"}</div>
            {!approved && <div className="mt-1 text-cmd-textDim">{decision.finalReasoning}</div>}
          </Glass>
        </div>
      </div>
    </div>
  );
}
