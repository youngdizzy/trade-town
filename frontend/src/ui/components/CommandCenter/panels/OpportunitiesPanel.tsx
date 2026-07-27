import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { voteDirection } from "../lib/derive";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * "Opportunities" reuses the same TradeDecision records the Decisions tab
 * shows in full — TradeTown's backend resolves a candidate the moment
 * research crosses the confidence threshold (see decision.py), so there
 * is no separate "still under consideration" object distinct from a
 * TradeDecision. This view is the recent/actionable slice: the last 12,
 * newest first, as clickable cards rather than a dense table.
 */
export function OpportunitiesPanel({ onInspect }: { onInspect: (d: TradeDecision) => void }) {
  const { decisions, paperPortfolio } = useGameStore();
  const recent = [...decisions].slice(-12).reverse();

  return (
    <div className="space-y-2">
      <TerminalLabel>Recent Opportunities ({recent.length})</TerminalLabel>
      {recent.length === 0 ? (
        <EmptyState>No opportunities evaluated yet — research hasn&apos;t crossed the trade-candidate confidence threshold.</EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {recent.map((d) => {
            const openPosition = paperPortfolio.positions.find((p) => p.symbol === d.symbol);
            return (
              <button key={d.id} type="button" onClick={() => onInspect(d)} className="text-left">
                <Glass className="h-full p-3 transition-colors hover:border-cmd-cyan/50">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-cmdmono text-cmd-cyan">{d.symbol}</span>
                    <StatusPill tone={d.outcome === "trade" ? "green" : "amber"}>{d.outcome === "trade" ? "TRADE" : "NO TRADE"}</StatusPill>
                  </div>
                  <div className="flex items-center justify-between text-cmd-textDim">
                    <span>{voteDirection(d.votes)}</span>
                    <span>{Math.round(d.confidence)}% confidence</span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-[9px] text-cmd-textDim">{d.finalReasoning}</div>
                  <div className="mt-1.5 flex items-center justify-between text-[9px]">
                    <span className="text-cmd-textDim">{d.supportingAgents.length ? AGENT_PROFILES[d.supportingAgents[0]!].name : "—"}</span>
                    {openPosition && <StatusPill tone="purple">OPEN POSITION</StatusPill>}
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
