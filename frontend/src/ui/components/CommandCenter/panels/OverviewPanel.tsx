import { useGameStore } from "@/ui/hooks/useGameStore";
import type { CompanyHealthTier, MarketEnvironmentRegime, TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { formatPct, voteDirection } from "../lib/derive";
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

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
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
