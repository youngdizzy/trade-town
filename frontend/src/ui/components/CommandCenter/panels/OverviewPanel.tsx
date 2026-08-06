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
          <TerminalLabel>AI Academy</TerminalLabel>
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
