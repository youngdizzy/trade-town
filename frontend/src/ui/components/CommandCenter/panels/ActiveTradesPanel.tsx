import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { AgentId, OrderSide, PaperPosition } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * CEO directive "Professional Quant Live Trading Desk," Phase 4-7 — the
 * Active Trades panel. Phase 0 audit found every open PaperPosition's
 * rich real fields (agent, confidence, MAE/MFE, strategy, trading
 * style, entry cost/slippage) already exist, but no component anywhere
 * displays the full open-position list — every existing panel collapses
 * to a count or an aggregate, and the one row-level view (BrainRoomHud)
 * is capped at 6 rows with only symbol/qty/entry/pnlPct. This shows
 * EVERY open position, all real fields, filterable — never just the
 * most recent or a summary count (per the directive's own explicit
 * "if 20 positions exist, show all 20" requirement).
 *
 * There is genuinely no stop-loss/take-profit order concept anywhere in
 * this codebase's live risk engine (already disclosed to the CEO
 * elsewhere, see ExecutiveVoting.tsx) — shown here as an honest "No
 * stop order placed" rather than omitted or fabricated.
 *
 * Multiple positions can exist on the same symbol from different agents
 * (the backend never nets — app/portfolio.py's open_position() always
 * appends) — this panel lists every one independently, never collapsing
 * same-symbol positions the way a naive `.find()` lookup elsewhere in
 * this codebase does.
 */
export function ActiveTradesPanel({ onSelect, selectedId }: { onSelect: (position: PaperPosition) => void; selectedId: string | null }) {
  const { paperPortfolio, strategies } = useGameStore();
  const positions = paperPortfolio.positions;

  const [agentFilter, setAgentFilter] = useState<AgentId | "all">("all");
  const [symbolFilter, setSymbolFilter] = useState<string>("all");
  const [sideFilter, setSideFilter] = useState<OrderSide | "all">("all");

  const agentOptions = useMemo(() => Array.from(new Set(positions.map((p) => p.openedBy))).sort(), [positions]);
  const symbolOptions = useMemo(() => Array.from(new Set(positions.map((p) => p.symbol))).sort(), [positions]);

  const filtered = positions.filter(
    (p) => (agentFilter === "all" || p.openedBy === agentFilter) && (symbolFilter === "all" || p.symbol === symbolFilter) && (sideFilter === "all" || p.side === sideFilter)
  );

  const strategyName = (strategyId: string | null) => (strategyId ? (strategies.find((s) => s.id === strategyId)?.name ?? strategyId) : "Unattributed");

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TerminalLabel>Active Trades ({filtered.length}{filtered.length !== positions.length ? ` of ${positions.length}` : ""})</TerminalLabel>
        <div className="flex flex-wrap gap-1.5">
          <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value as AgentId | "all")} className="rounded-sm border border-cmd-border bg-cmd-bg px-1.5 py-0.5 text-[9px] text-cmd-text">
            <option value="all">All agents</option>
            {agentOptions.map((a) => (
              <option key={a} value={a}>
                {AGENT_PROFILES[a].name}
              </option>
            ))}
          </select>
          <select value={symbolFilter} onChange={(e) => setSymbolFilter(e.target.value)} className="rounded-sm border border-cmd-border bg-cmd-bg px-1.5 py-0.5 text-[9px] text-cmd-text">
            <option value="all">All symbols</option>
            {symbolOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select value={sideFilter} onChange={(e) => setSideFilter(e.target.value as OrderSide | "all")} className="rounded-sm border border-cmd-border bg-cmd-bg px-1.5 py-0.5 text-[9px] text-cmd-text">
            <option value="all">Long &amp; short</option>
            <option value="buy">Long only</option>
            <option value="sell">Short only</option>
          </select>
        </div>
      </div>

      {positions.length === 0 ? (
        <EmptyState>No open positions right now.</EmptyState>
      ) : filtered.length === 0 ? (
        <EmptyState>No open positions match this filter.</EmptyState>
      ) : (
        <div className="space-y-1.5">
          {filtered.map((p) => {
            const isLong = p.side === "buy";
            const isSelected = p.id === selectedId;
            return (
              <button key={p.id} type="button" onClick={() => onSelect(p)} className="block w-full text-left">
                <Glass className={`p-2.5 transition-colors hover:border-cmd-cyan/50 ${isSelected ? "border-cmd-cyan" : ""}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-medium text-cmd-textDim">{AGENT_PROFILES[p.openedBy].name}</span>
                      <StatusPill tone={isLong ? "green" : "red"}>{isLong ? "LONG" : "SHORT"}</StatusPill>
                      <span className="font-cmdmono text-cmd-cyan">{p.symbol}</span>
                    </div>
                    <span className={`tabular-nums font-medium ${p.unrealizedPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                      {p.unrealizedPnl >= 0 ? "+" : ""}
                      {p.unrealizedPnl.toFixed(2)} ({p.unrealizedPnlPct >= 0 ? "+" : ""}
                      {p.unrealizedPnlPct.toFixed(2)}%)
                    </span>
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[9px] text-cmd-textDim sm:grid-cols-4">
                    <span>
                      Strategy: <span className="text-cmd-text">{strategyName(p.strategyId)}</span>
                    </span>
                    <span>
                      Entry: <span className="tabular-nums text-cmd-text">${p.entryPrice.toFixed(2)}</span>
                    </span>
                    <span>
                      Current: <span className="tabular-nums text-cmd-text">${p.currentPrice.toFixed(2)}</span>
                    </span>
                    <span>
                      Qty: <span className="tabular-nums text-cmd-text">{p.quantity}</span>
                    </span>
                    <span>
                      Confidence: <span className="tabular-nums text-cmd-text">{Math.round(p.confidence)}%</span>
                    </span>
                    <span>
                      MAE / MFE: <span className="tabular-nums text-cmd-text">{p.maePct.toFixed(1)}% / {p.mfePct.toFixed(1)}%</span>
                    </span>
                    {p.tradingStyle && (
                      <span>
                        Style: <span className="text-cmd-text">{p.tradingStyle === "day" ? "Day" : "Swing"}</span>
                      </span>
                    )}
                    <span className="italic text-cmd-textDim">No stop order placed</span>
                  </div>
                </Glass>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
