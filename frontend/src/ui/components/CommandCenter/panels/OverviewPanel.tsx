import { useEffect, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type {
  AgentTradingStatusRead,
  CompanyHealthTier,
  MarketEnvironmentRegime,
  StrategyDegradationSummary,
  StrategyMatch,
  StrategyPerformanceSummary,
  TradeDecision,
  UnattributedTradeMonitor,
} from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import { formatMoney, formatPct, voteDirection } from "../lib/derive";
import { computePeriodFinancials } from "../lib/financials";
import { useDashboardData } from "../lib/useDashboardData";
import { DataRow, EmptyState, Glass, Meter, RiskDot, StatusPill, TerminalLabel } from "../ui";
import { MarketChartPanel } from "../MarketChartPanel";
import { AgentEnergyWidget } from "../AgentEnergyWidget";
import type { Tab } from "../FullCommandCenter";

const TIER_TONE: Record<CompanyHealthTier, "green" | "cyan" | "amber" | "red"> = {
  excellent: "green",
  good: "green",
  stable: "cyan",
  needs_attention: "amber",
  critical: "red",
};
const REGIME_TONE: Record<MarketEnvironmentRegime, "green" | "red" | "amber" | "cyan" | "neutral"> = {
  bull: "green",
  bear: "red",
  sideways: "neutral",
  high_volatility: "amber",
  low_volatility: "cyan",
};

/** The landing tab — the small set of numbers most likely to change what the operator does next, pulled from every other panel's real data. Shares its data with QuickView via useDashboardData() rather than recomputing it. */
export function OverviewPanel({ onInspect, onNavigate }: { onInspect: (d: TradeDecision) => void; onNavigate: (t: Tab) => void }) {
  const { companyScore, companyHealth, marketEnvironment, academyState, paperPortfolio, riskWarnings } = useGameStore();
  const { level, recentDecisions: recent, noTrade, latest, workingCount } = useDashboardData();
  const [tradingStatus, setTradingStatus] = useState<AgentTradingStatusRead[]>([]);

  // CEO directive "Command Center + Professional Quant Trading Firm
  // Upgrade," Phase 2 — real agent-thesis roll-up, reusing the same
  // GET /api/agents/trading-status the AI Desk's Roster tab already
  // fetches (see AgentsPanel.tsx).
  useEffect(() => {
    api.getAgentTradingStatus().then(setTradingStatus).catch(() => undefined);
  }, []);
  const waitingAgents = tradingStatus.filter((a) => a.status === "waiting");
  const scanningCount = tradingStatus.filter((a) => a.status === "scanning").length;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <TradingIntelligenceStrip onNavigate={onNavigate} />

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Company Score</TerminalLabel>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="font-cmdmono text-2xl text-cmd-cyan">{Math.round(companyScore.overall)}</span>
          <span className="text-cmd-textDim">/ 100</span>
        </div>
        <Meter value={companyScore.overall} tone="cyan" />
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
          <ScoreCell label="Research" value={companyScore.researchQuality} />
          <ScoreCell label="Decisions" value={companyScore.decisionQuality} />
          <ScoreCell label="Risk" value={companyScore.riskManagement} />
          <ScoreCell label="Paper P&L" value={companyScore.paperTradingPerformance} />
          <ScoreCell label="Teamwork" value={companyScore.teamCoordination} />
          <ScoreCell label="Simulation" value={companyScore.simulationSuccess} />
        </div>
      </Glass>

      <Glass className={`p-3 ${level === "red" ? "border-cmd-red/50" : level === "yellow" ? "border-cmd-amber/50" : ""}`}>
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Risk Status</TerminalLabel>
          <RiskDot level={level} />
        </div>
        <DataRow label="Open positions" value={paperPortfolio.positions.length} />
        <DataRow label="Active warnings" value={riskWarnings.length} valueClassName={riskWarnings.length ? "text-cmd-amber" : "text-cmd-text"} />
        <DataRow label="Total P&L" value={formatPct(paperPortfolio.totalPnlPct)} valueClassName={paperPortfolio.totalPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <button type="button" onClick={() => onNavigate("RISK")} className="mt-2 w-full rounded-sm border border-cmd-border py-1 text-cmd-textDim hover:text-cmd-cyan">
          View Risk Panel →
        </button>
      </Glass>

      <FailureBoundaryCard onNavigate={onNavigate} />

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Market Environment</TerminalLabel>
          <StatusPill tone={REGIME_TONE[marketEnvironment.current]}>{marketEnvironment.label}</StatusPill>
        </div>
        <div className="text-[9px] text-cmd-textDim">{marketEnvironment.detail}</div>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Company Health</TerminalLabel>
          <StatusPill tone={TIER_TONE[companyHealth.tier]}>{Math.round(companyHealth.overall)}</StatusPill>
        </div>
        <Meter value={companyHealth.overall} tone={TIER_TONE[companyHealth.tier]} />
        <button type="button" onClick={() => onNavigate("COMPANY")} className="mt-2 w-full rounded-sm border border-cmd-border py-1 text-cmd-textDim hover:text-cmd-cyan">
          View Company →
        </button>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          {/* Design Bible Chapter 67 (TTOS) Part 3 — Navigation polish. Was
              "AI Academy", which collided with the real, unrelated ACADEMY
              tab (the pre-existing Trading Academy lesson/quiz curriculum)
              this card doesn't navigate to — it navigates to KNOWLEDGE
              (v0.7 Feature 25's actual AI Academy & Knowledge Network).
              Renamed to the same term the KNOWLEDGE tab's own content
              already uses for this ("Academy Progression" — see
              AcademyPanel.tsx), the same disambiguation
              MentorLibraryPanel.tsx's own "(KNOWLEDGE tab)" aside already
              established, not an invented label. */}
          <TerminalLabel>Academy Progression</TerminalLabel>
          <StatusPill tone="cyan">LVL {academyState.level}</StatusPill>
        </div>
        <div className="mb-2 text-[9px] text-cmd-textDim">{academyState.levelLabel}</div>
        <Meter value={(academyState.level / 5) * 100} tone="cyan" />
        <button type="button" onClick={() => onNavigate("KNOWLEDGE")} className="mt-2 w-full rounded-sm border border-cmd-border py-1 text-cmd-textDim hover:text-cmd-cyan">
          View Knowledge →
        </button>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Team Status</TerminalLabel>
        <DataRow label="Agents active" value={`${workingCount} / 10`} />
        <DataRow label="No-trade rate" value={noTrade.total ? `${Math.round((noTrade.noTradeCount / noTrade.total) * 100)}%` : "N/A"} />
        {tradingStatus.length > 0 && (
          <>
            <DataRow label="Currently researching" value={scanningCount} />
            <DataRow label="Awaiting your decision" value={waitingAgents.length} valueClassName={waitingAgents.length > 0 ? "text-cmd-amber" : "text-cmd-text"} />
            {waitingAgents.length > 0 && (
              <div className="mt-1.5 space-y-1 border-t border-cmd-border/60 pt-1.5">
                {waitingAgents.map((a) => (
                  <div key={a.agentId} className="truncate text-[9px] text-cmd-textDim">
                    <span className="text-cmd-cyan">{AGENT_PROFILES[a.agentId].name}</span> — {a.headline}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        <button type="button" onClick={() => onNavigate("AGENTS")} className="mt-2 w-full rounded-sm border border-cmd-border py-1 text-cmd-textDim hover:text-cmd-cyan">
          View Agents →
        </button>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Latest Recommendation</TerminalLabel>
        {latest === null ? (
          <EmptyState>No decisions yet.</EmptyState>
        ) : (
          <>
            <div className={`font-cmdmono ${latest.outcome === "trade" ? "text-cmd-green" : "text-cmd-amber"}`}>
              {latest.symbol} — {latest.outcome === "trade" ? "TRADE" : "NO TRADE"}
            </div>
            <div className="mt-0.5 truncate text-[9px] text-cmd-textDim">{latest.finalReasoning}</div>
          </>
        )}
      </Glass>

      <div className="lg:col-span-3">
        <AgentEnergyWidget />
      </div>

      <div className="lg:col-span-3">
        <MarketChartPanel />
      </div>

      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Recent Decisions</TerminalLabel>
          <button type="button" onClick={() => onNavigate("DECISIONS")} className="text-cmd-textDim hover:text-cmd-cyan">
            View all →
          </button>
        </div>
        {recent.length === 0 ? (
          <EmptyState>No decisions recorded yet.</EmptyState>
        ) : (
          <div className="divide-y divide-cmd-border/60">
            {recent.map((d) => (
              <button key={d.id} type="button" onClick={() => onInspect(d)} className="flex w-full items-center justify-between gap-2 py-1.5 text-left hover:bg-cmd-panelLight/60">
                <span className="font-cmdmono text-cmd-cyan">{d.symbol}</span>
                <span className="text-cmd-textDim">{voteDirection(d.votes)}</span>
                <span className="text-cmd-textDim">{Math.round(d.confidence)}%</span>
                <span className={d.outcome === "trade" ? "text-cmd-green" : "text-cmd-amber"}>{d.outcome === "trade" ? "TRADE" : "NO TRADE"}</span>
                <span className="truncate text-cmd-textDim">{AGENT_PROFILES[d.supportingAgents[0] ?? "atlas"].name}</span>
              </button>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

/**
 * CEO directive "Complete Trade Provenance + Session/Regime Intelligence
 * + Evidence-Based Attribution," Part 16 — Command Center UX. The
 * directive's own rule: "DO NOT create another maze of tabs. Integrate
 * this into the existing Command Center." Research (see docs/
 * Architecture.md's Part 16 section) found OverviewPanel already IS
 * this codebase's "small set of numbers most likely to change what the
 * operator does next" landing pattern (see this file's own docstring
 * above) and PortfolioIntelPanel.tsx's PortfolioCommandCenterStrip
 * already established the "compact cross-cutting strip + cross-link
 * buttons, reusing already-computed sources" shape — so this is an
 * addition to the existing OVERVIEW tab, not a new one, following that
 * exact template.
 *
 * Every tile reuses an already-real, already-computed source: active
 * strategy count and open exposure come from the same WS-broadcast
 * `strategies`/`portfolioIntelligence` PortfolioCommandCenterStrip
 * already reads; trades-today reuses the same `computePeriodFinancials`
 * every other panel's "today" figure already comes from; session/regime
 * are the real backend-computed MarketIntelligenceState fields (not a
 * client heuristic); eligibility, strategy P&L, degradation warnings,
 * and unattributed-trade count are the real endpoints this directive's
 * earlier parts (13/17) and the prior "Live Trade → Strategy
 * Provenance" directive (Phase 9) already built and exposed, just never
 * wired to a summary view before now.
 *
 * NON-COMPLIANT TRADES is deliberately never rendered as a real number.
 * Part 3 of this same directive (Strategy Compliance at Execution) was
 * researched and explicitly deferred — a live TradeProposal never
 * carries a link to the compiled Strategy rules that produced it, so
 * there is no real signal anywhere in this codebase that could back a
 * per-trade compliance verdict. Showing "0" here would be a fabricated
 * claim of verified compliance; this tile honestly discloses that gap
 * instead, per this directive's own Absolute Rule #3.
 */
function TradingIntelligenceStrip({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const { strategies, paperPortfolio, time, marketIntelligence, portfolioIntelligence: pi } = useGameStore();
  const [eligibility, setEligibility] = useState<StrategyMatch | null>(null);
  const [strategyPerf, setStrategyPerf] = useState<StrategyPerformanceSummary | null>(null);
  const [degradation, setDegradation] = useState<StrategyDegradationSummary | null>(null);
  const [unattributed, setUnattributed] = useState<UnattributedTradeMonitor | null>(null);

  useEffect(() => {
    api.getLiveStrategyEligibility().then(setEligibility).catch(() => undefined);
    api.getPerformanceByStrategy().then(setStrategyPerf).catch(() => undefined);
    api.getStrategyDegradation().then(setDegradation).catch(() => undefined);
    api.getUnattributedTradeMonitor().then(setUnattributed).catch(() => undefined);
  }, []);

  const activeStrategies = strategies.filter((s) => s.stage !== "retired").length;
  const openUnrealized = paperPortfolio.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const today = computePeriodFinancials("today", paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);
  const totalStrategyPnl = strategyPerf ? strategyPerf.reads.reduce((s, r) => s + r.totalPnl, 0) : null;
  const warningCount = degradation ? degradation.reads.filter((r) => r.level === "critical_degradation" || r.level === "possible_degradation").length : null;

  return (
    <Glass className="border border-cmd-cyan/30 p-3 lg:col-span-3">
      <TerminalLabel>Trading Intelligence</TerminalLabel>
      <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-5">
        <DataRow label="Active Strategies" value={activeStrategies} />
        <DataRow label="Eligible Now" value={eligibility ? eligibility.recommendedStrategyIds.length : "…"} />
        <DataRow label="Trades Today" value={today.tradeCount} />
        <DataRow label="Open Exposure" value={`${formatMoney(pi.exposure.grossExposure)} (${pi.exposure.grossExposurePct.toFixed(0)}%)`} valueClassName="tabular-nums" />
        <DataRow
          label="Strategy P&L"
          value={totalStrategyPnl === null ? "…" : formatMoney(totalStrategyPnl)}
          valueClassName={totalStrategyPnl === null ? undefined : totalStrategyPnl >= 0 ? "text-cmd-green" : "text-cmd-red"}
        />
        <DataRow label="Session" value={marketIntelligence.session.label} />
        <DataRow label="Regime" value={marketIntelligence.regimeLabel} />
        <DataRow
          label="Unattributed Trades"
          value={unattributed ? `${unattributed.unattributedCount} (${unattributed.unattributedPct.toFixed(0)}%)` : "…"}
          valueClassName={unattributed && unattributed.unattributedCount > 0 ? "text-cmd-amber" : undefined}
        />
        <DataRow label="Non-Compliant Trades" value="Not tracked" valueClassName="text-cmd-textDim italic" />
        <DataRow
          label="Strategy Warnings"
          value={warningCount === null ? "…" : warningCount}
          valueClassName={warningCount !== null && warningCount > 0 ? "text-cmd-amber" : undefined}
        />
      </div>
      <p className="mt-1.5 text-[8px] italic text-cmd-textDim">
        Non-Compliant Trades has no real signal to report yet — live trades aren&apos;t linked to compiled Strategy rules at execution time (a disclosed, deferred gap — see docs/Architecture.md&apos;s Part 3).
      </p>
      <div className="mt-2 flex flex-wrap gap-3 text-[9px]">
        <button type="button" onClick={() => onNavigate("PERFORMANCE")} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Strategy Performance &amp; Warnings
        </button>
        <button type="button" onClick={() => onNavigate("MARKETINTEL")} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Session &amp; Regime Detail
        </button>
        <button type="button" onClick={() => onNavigate("VAULT")} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Trade-by-Trade Provenance
        </button>
        <button type="button" onClick={() => onNavigate("OPPORTUNITIES")} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Opportunity Feed
        </button>
      </div>
    </Glass>
  );
}

function ScoreCell({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">{label}</div>
      <div className="text-cmd-text">{Math.round(value)}</div>
    </div>
  );
}

/**
 * CEO directive "Command Center + Professional Quant Trading Firm
 * Upgrade," Phase 2 (Risk Visualization) — "the user should immediately
 * know: how close are we to blowing the account?" Every real value here
 * already existed (`riskBudgetStatus`, WS-broadcast, computed by
 * backend/app/risk_engine.py's compute_risk_budget_status()) but had
 * never been surfaced as a standing card anywhere — the only prior UI
 * for it lived inside ExecutiveVoting's own pre-trade popup. No new
 * backend field, no new arithmetic beyond what that endpoint already
 * returns: `remainingDrawdownBudgetPct` already IS "distance to
 * failure" (its own docstring: "limit minus current usage, floored at
 * 0") — this card just gives it a permanent home.
 */
function FailureBoundaryCard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const { riskBudgetStatus } = useGameStore();
  const usedPct = riskBudgetStatus.maxDrawdownPct > 0 ? Math.min(100, (riskBudgetStatus.lifetimeDrawdownPct / riskBudgetStatus.maxDrawdownPct) * 100) : 0;
  const tone: "green" | "amber" | "red" = usedPct >= 75 ? "red" : usedPct >= 40 ? "amber" : "green";

  return (
    <Glass className={`p-3 ${tone === "red" ? "border-cmd-red/50" : tone === "amber" ? "border-cmd-amber/50" : ""}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Failure Boundary</TerminalLabel>
        {riskBudgetStatus.tradingHalted && <StatusPill tone="red">HALTED</StatusPill>}
      </div>
      <div className="mb-1 flex items-baseline justify-between text-[9px]">
        <span className="text-cmd-textDim">Lifetime drawdown used</span>
        <span className={tone === "red" ? "text-cmd-red" : tone === "amber" ? "text-cmd-amber" : "text-cmd-text"}>
          {riskBudgetStatus.lifetimeDrawdownPct.toFixed(1)}% of {riskBudgetStatus.maxDrawdownPct.toFixed(1)}% max
        </span>
      </div>
      <Meter value={usedPct} tone={tone} />
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
        <DataRow label="Equity" value={`$${riskBudgetStatus.equity.toFixed(0)}`} />
        <DataRow label="Distance to failure" value={`${riskBudgetStatus.remainingDrawdownBudgetPct.toFixed(1)}%`} valueClassName={tone === "red" ? "text-cmd-red" : undefined} />
        <DataRow label="Today's loss budget left" value={`${riskBudgetStatus.remainingDailyLossBudgetPct.toFixed(1)}%`} />
        <DataRow label="Trading days tracked" value={riskBudgetStatus.tradingDaysCount} />
      </div>
      {riskBudgetStatus.haltReason && <div className="mt-1.5 text-[9px] text-cmd-amber">{riskBudgetStatus.haltReason}</div>}
      <button type="button" onClick={() => onNavigate("RISK")} className="mt-2 w-full rounded-sm border border-cmd-border py-1 text-cmd-textDim hover:text-cmd-cyan">
        View Risk Panel →
      </button>
    </Glass>
  );
}
