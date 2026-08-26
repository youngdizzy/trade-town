import { useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { PaperPosition, TradeDecision } from "@/types";
import { MarketChartPanel } from "../MarketChartPanel";
import { DecisionDetail } from "../DecisionDetail";
import { EmptyState, Glass, TerminalLabel } from "../ui";
import { ActiveTradesPanel } from "./ActiveTradesPanel";

/**
 * CEO directive "Professional Quant Live Trading Desk" — the primary
 * desk view (Phase 26): main chart + every active trade + trade detail,
 * without navigating through a dozen tabs. Composes three already-real
 * pieces rather than building a second implementation of any of them:
 * MarketChartPanel (now controllable, see its own docstring), the new
 * ActiveTradesPanel (Phase 4-7's real gap — see its own docstring), and
 * DecisionDetail (the existing "why does the AI want this trade"
 * drill-down, reused here rather than rebuilt — Phase 7/13's ask,
 * except its position lookup is now correctly keyed off the real
 * PaperPosition.proposalId link instead of a symbol guess).
 *
 * Clicking an active trade re-centers the chart on that trade's symbol
 * AND opens its full decision detail when a matching TradeDecision is
 * still on record — honestly unavailable (never guessed) if it isn't
 * (the decisions list is a capped, rotating window — see
 * app/nexus.py's MAX_DECISIONS).
 */
export function LiveDeskPanel() {
  const { paperPortfolio, decisions } = useGameStore();
  const [focusedSymbol, setFocusedSymbol] = useState<string | null>(null);
  const [focusedTimeframe, setFocusedTimeframe] = useState("1h");
  const [selectedPosition, setSelectedPosition] = useState<PaperPosition | null>(null);
  const [inspecting, setInspecting] = useState<TradeDecision | null>(null);

  const handleSelect = (position: PaperPosition) => {
    setSelectedPosition(position);
    setFocusedSymbol(position.symbol);
    const decisionId = position.proposalId ? `decision-${position.proposalId}` : null;
    const decision = decisionId ? (decisions.find((d) => d.id === decisionId) ?? null) : null;
    setInspecting(decision);
  };

  return (
    <div className="relative space-y-3">
      <MarketChartPanel symbol={focusedSymbol ?? undefined} onSymbolChange={setFocusedSymbol} timeframe={focusedTimeframe} onTimeframeChange={setFocusedTimeframe} />

      {selectedPosition && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Selected Trade — {selectedPosition.symbol}</TerminalLabel>
            {!inspecting && (
              <span className="text-[9px] italic text-cmd-textDim">
                Decision record unavailable — {selectedPosition.proposalId === null ? "this position predates trade-lineage tracking." : "the decision log has rotated past it."}
              </span>
            )}
          </div>
          {!inspecting && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[9px] text-cmd-textDim sm:grid-cols-4">
              <span>
                Entry: <span className="tabular-nums text-cmd-text">${selectedPosition.entryPrice.toFixed(2)}</span>
              </span>
              <span>
                Current: <span className="tabular-nums text-cmd-text">${selectedPosition.currentPrice.toFixed(2)}</span>
              </span>
              <span>
                P&amp;L: <span className={`tabular-nums ${selectedPosition.unrealizedPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{selectedPosition.unrealizedPnl >= 0 ? "+" : ""}{selectedPosition.unrealizedPnl.toFixed(2)}</span>
              </span>
              <span>
                Confidence: <span className="tabular-nums text-cmd-text">{Math.round(selectedPosition.confidence)}%</span>
              </span>
            </div>
          )}
        </Glass>
      )}

      <ActiveTradesPanel onSelect={handleSelect} selectedId={selectedPosition?.id ?? null} />

      {paperPortfolio.positions.length === 0 && (
        <EmptyState>No open positions right now — the chart above is browsing the watchlist. Select a symbol to look at any tracked market.</EmptyState>
      )}

      {inspecting && <DecisionDetail decision={inspecting} onClose={() => setInspecting(null)} />}
    </div>
  );
}
