import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { OpportunityFeed, OpportunityFeedEntry, OpportunityFeedStatus, TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import { voteDirection } from "../lib/derive";
import { EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

const STATUS_TONE: Record<OpportunityFeedStatus, "green" | "cyan" | "red" | "neutral"> = {
  eligible: "green",
  conditionally_eligible: "cyan",
  not_eligible: "red",
  insufficient_evidence: "neutral",
};
const STATUS_LABEL: Record<OpportunityFeedStatus, string> = {
  eligible: "ELIGIBLE",
  conditionally_eligible: "CONDITIONAL",
  not_eligible: "NOT ELIGIBLE",
  insufficient_evidence: "INSUFFICIENT EVIDENCE",
};

function OpportunityFeedRow({ entry }: { entry: OpportunityFeedEntry }) {
  return (
    <Glass className="p-2">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="font-cmdmono text-cmd-cyan">{entry.symbol}</span>
        <StatusPill tone={STATUS_TONE[entry.status]}>{STATUS_LABEL[entry.status]}</StatusPill>
      </div>
      <div className="line-clamp-2 text-[9px] text-cmd-textDim">{entry.headline}</div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[9px] text-cmd-textDim">
        <span>Decision Score: <span className="text-cmd-text">{entry.decisionScore === null ? "—" : Math.round(entry.decisionScore)}</span></span>
        <span>EV: <span className={entry.expectedValuePct === null ? "text-cmd-text" : entry.expectedValuePct >= 0 ? "text-cmd-green" : "text-cmd-red"}>{entry.expectedValuePct === null ? "—" : `${entry.expectedValuePct.toFixed(1)}%`}</span></span>
        {entry.confidence !== null && <span>Confidence: <span className="text-cmd-text">{Math.round(entry.confidence)}%</span></span>}
      </div>
    </Glass>
  );
}

/**
 * CEO directive "Professional Quant Trading Core," Rule 25/26 — the CEO
 * Opportunity Feed. A Phase A audit found the scoring/evidence this
 * needs (Decision Score, Expected Value, rejection reasons) already
 * computed live every tick by the Opportunity Gatekeeper with zero UI
 * surface anywhere — this ranks and displays it, computing nothing new
 * (see backend/app/opportunity_feed.py's own module docstring). NOT a
 * whole-universe proactive scan — see `feed.dataHonestyNote`.
 */
function OpportunityFeedSection() {
  const [feed, setFeed] = useState<OpportunityFeed | null>(null);
  useEffect(() => {
    api.getOpportunityFeed().then(setFeed).catch(() => undefined);
  }, []);

  if (!feed) return null;

  return (
    <div className="space-y-2">
      <TerminalLabel>CEO Opportunity Feed — live, evidence-ranked</TerminalLabel>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="space-y-1.5">
          <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Best Current Opportunities ({feed.bestOpportunities.length})</div>
          {feed.bestOpportunities.length === 0 ? (
            <EmptyState>No candidate is currently past the opportunity gate.</EmptyState>
          ) : (
            feed.bestOpportunities.map((e) => <OpportunityFeedRow key={e.id} entry={e} />)
          )}
        </div>
        <div className="space-y-1.5">
          <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Watchlist ({feed.watchlist.length})</div>
          {feed.watchlist.length === 0 ? (
            <EmptyState>No research currently in progress.</EmptyState>
          ) : (
            feed.watchlist.map((e) => <OpportunityFeedRow key={e.id} entry={e} />)
          )}
        </div>
        <div className="space-y-1.5">
          <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Avoid — recently rejected ({feed.avoid.length})</div>
          {feed.avoid.length === 0 ? (
            <EmptyState>Nothing has been rejected recently.</EmptyState>
          ) : (
            feed.avoid.map((e) => <OpportunityFeedRow key={e.id} entry={e} />)
          )}
        </div>
      </div>
      <p className="text-[8px] italic text-cmd-textDim">{feed.dataHonestyNote}</p>
    </div>
  );
}

/**
 * "Recent Decisions" (the original per-tab content) reuses the same
 * TradeDecision records the Decisions tab shows in full — TradeTown's
 * backend resolves a candidate the moment research crosses the
 * confidence threshold (see decision.py), so there is no separate
 * "still under consideration" object distinct from a TradeDecision.
 * This view is the recent/actionable slice: the last 12, newest first,
 * as clickable cards rather than a dense table.
 */
export function OpportunitiesPanel({ onInspect }: { onInspect: (d: TradeDecision) => void }) {
  const { decisions, paperPortfolio } = useGameStore();
  const recent = [...decisions].slice(-12).reverse();

  return (
    <div className="space-y-4">
      <OpportunityFeedSection />

      <div className="space-y-2">
        <TerminalLabel>Recent Decisions — resolved ({recent.length})</TerminalLabel>
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
    </div>
  );
}
