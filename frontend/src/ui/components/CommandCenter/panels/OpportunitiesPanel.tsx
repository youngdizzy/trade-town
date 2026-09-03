import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type {
  OpportunityFeed,
  OpportunityFeedEntry,
  OpportunityFeedStatus,
  OpportunityGateCalibrationExperimentReport,
  SymbolTrendRanking,
  TradeDecision,
  WatchlistEligibilitySummary,
  WatchlistTier,
} from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import { SIGNAL_STATE_LABEL, SIGNAL_STATE_TONE, voteDirection } from "../lib/derive";
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

const TIER_TONE: Record<WatchlistTier, "green" | "cyan" | "red" | "neutral"> = {
  proven: "green",
  developing: "cyan",
  unproven: "neutral",
  cautionary: "red",
};
const TIER_LABEL: Record<WatchlistTier, string> = {
  proven: "PROVEN",
  developing: "DEVELOPING",
  unproven: "UNPROVEN",
  cautionary: "CAUTIONARY",
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
 * CEO directive "Professional Quant Trading Core," Phase B P2 item — a
 * standing, per-symbol Watchlist Eligibility Tier, distinct from the
 * feed above's per-candidate status: this is the symbol's own whole
 * real track record (see backend/app/watchlist_eligibility.py's module
 * docstring), never a fabricated score for a symbol with no real trades.
 */
function WatchlistEligibilitySection() {
  const [summary, setSummary] = useState<WatchlistEligibilitySummary | null>(null);
  useEffect(() => {
    api.getWatchlistEligibility().then(setSummary).catch(() => undefined);
  }, []);

  if (!summary || summary.reads.length === 0) return null;

  return (
    <div className="space-y-2">
      <TerminalLabel>Watchlist Eligibility — real per-symbol track record</TerminalLabel>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {summary.reads.map((r) => (
          <Glass key={r.symbol} className="p-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-cmdmono text-cmd-cyan">{r.symbol}</span>
              <StatusPill tone={TIER_TONE[r.tier]}>{TIER_LABEL[r.tier]}</StatusPill>
            </div>
            <div className="text-[9px] text-cmd-textDim">{r.detail}</div>
          </Glass>
        ))}
      </div>
    </div>
  );
}

/**
 * CEO directive "Professional Quant Trading Core," Phase B's last P2
 * item — the Asset Discovery Engine (see backend/app/asset_discovery.py's
 * own module docstring). Real cross-sectional trend evidence over
 * symbols the CEO hasn't added to the watchlist yet — a Research Desk
 * read only, never an automatic trade selection or an automatic add.
 */
function AssetDiscoverySection() {
  const [rankings, setRankings] = useState<SymbolTrendRanking[] | null>(null);
  useEffect(() => {
    api.getAssetDiscovery().then(setRankings).catch(() => undefined);
  }, []);

  if (!rankings || rankings.length === 0) return null;

  return (
    <div className="space-y-2">
      <TerminalLabel>Asset Discovery — real trend evidence beyond the current watchlist</TerminalLabel>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {rankings.map((r) => (
          <Glass key={r.symbol} className="p-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-cmdmono text-cmd-cyan">{r.symbol}</span>
              <span className="text-[9px] uppercase tracking-wide text-cmd-textDim">{r.category}</span>
            </div>
            <div className="mb-1">
              <StatusPill tone={SIGNAL_STATE_TONE[r.signalState]}>{SIGNAL_STATE_LABEL[r.signalState]}</StatusPill>
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[9px] text-cmd-textDim">
              <span>Composite: <span className={r.compositeScore >= 0 ? "text-cmd-green" : "text-cmd-red"}>{r.compositeScore.toFixed(1)}</span></span>
              <span>Persistence: <span className="text-cmd-text">{r.trendPersistenceBars}</span></span>
              <span>Risk-Adj: <span className="text-cmd-text">{r.riskAdjustedScore.toFixed(2)}</span></span>
            </div>
          </Glass>
        ))}
      </div>
      <p className="text-[8px] italic text-cmd-textDim">
        Not on the watchlist — evidence only, never an automatic trade or an automatic add. Use a Watch This Symbol action to start tracking one.
      </p>
    </div>
  );
}

const MODEL_LABEL: Record<string, string> = {
  liquidity_excluded: "B: Liquidity-Excluded",
  capped_penalty: "C: Capped-Penalty",
  weighted_equal_weight: "D: Weighted (equal)",
  weighted_reduced_liquidity_weight: "D: Weighted (reduced liquidity)",
  weighted_increased_liquidity_weight: "D: Weighted (increased liquidity)",
};

/**
 * CEO directive "Opportunity Gate Calibration Experiment 1.0" — a pure,
 * read-only shadow-scoring diagnostic. See backend/app/opportunity_gate_
 * calibration_experiment.py's own module docstring for the full real
 * methodology, its disclosed limitations (the rescued-candidate
 * population only has real data for rejections created after this
 * directive's own instrumentation shipped), and why this lives here
 * rather than on a new top-level tab: this IS the existing Opportunity
 * Gatekeeper surface. SHADOW EXPERIMENT — DOES NOT CONTROL TRADING;
 * nothing here feeds evaluate_opportunity() or any live gate decision.
 */
function OpportunityGateCalibrationExperimentSection() {
  const [report, setReport] = useState<OpportunityGateCalibrationExperimentReport | null>(null);
  useEffect(() => {
    api.getOpportunityGateCalibrationExperiment().then(setReport).catch(() => undefined);
  }, []);

  if (!report) return null;

  return (
    <div className="space-y-2">
      <TerminalLabel>Opportunity Gate Calibration Experiment — shadow scoring, research only</TerminalLabel>
      <Glass className="space-y-2 border border-cmd-amber/50 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <StatusPill tone="amber">SHADOW EXPERIMENT — DOES NOT CONTROL TRADING</StatusPill>
          <span className="text-[9px] text-cmd-textDim">{report.experimentVersion}</span>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[9px] text-cmd-textDim sm:grid-cols-4">
          <span>Eligible rejections: <span className="text-cmd-text">{report.eligibleRejectionsWithCapture}</span></span>
          <span>Ineligible (pre-instrumentation): <span className="text-cmd-text">{report.ineligibleRejectionsNoCapture}</span></span>
          <span>Approved sessions: <span className="text-cmd-text">{report.totalApprovedWarRoomSessions}</span></span>
          <span>
            Control equivalence:{" "}
            <span className={report.controlEquivalenceMismatches === 0 ? "text-cmd-green" : "text-cmd-red"}>
              {report.controlEquivalenceChecked - report.controlEquivalenceMismatches}/{report.controlEquivalenceChecked}
            </span>
          </span>
        </div>
        {report.groupCounts.length === 0 ? (
          <EmptyState>No eligible candidates yet — the rescued-candidate population only accumulates from rejections created after this experiment shipped.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[9px]">
              <thead>
                <tr className="text-cmd-textDim">
                  <th className="p-1 text-left">Model</th>
                  <th className="p-1 text-right">Rescued</th>
                  <th className="p-1 text-right">Confirmed Reject</th>
                  <th className="p-1 text-right">Confirmed Approve</th>
                  <th className="p-1 text-right">Shadow Would Reject</th>
                </tr>
              </thead>
              <tbody>
                {report.groupCounts.map((g) => (
                  <tr key={g.modelId} className="border-t border-cmd-border/50">
                    <td className="p-1 text-cmd-text">{MODEL_LABEL[g.modelId] ?? g.modelId}</td>
                    <td className="p-1 text-right text-cmd-green">{g.rescuedCount}</td>
                    <td className="p-1 text-right text-cmd-text">{g.confirmedRejectCount}</td>
                    <td className="p-1 text-right text-cmd-text">{g.confirmedApproveCount}</td>
                    <td className="p-1 text-right text-cmd-red">{g.shadowWouldRejectCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-[8px] italic text-cmd-textDim">{report.liquidityAnalysisNote}</p>
        <p className="text-[8px] italic text-cmd-textDim">{report.dataHonestyNote}</p>
      </Glass>
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

      <WatchlistEligibilitySection />

      <AssetDiscoverySection />

      <OpportunityGateCalibrationExperimentSection />

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
