import { useGameStore } from "@/ui/hooks/useGameStore";
import type { TradeDecision } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { computeNoTradeStats, formatPct, latestDecision, marketRegimeHeuristic, riskLevel, voteDirection } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, RiskDot, TerminalLabel } from "../ui";
import { MarketChartPanel } from "../MarketChartPanel";
import { AgentEnergyWidget } from "../AgentEnergyWidget";
import type { Tab } from "../FullCommandCenter";

/** The landing tab — the small set of numbers most likely to change what the operator does next, pulled from every other panel's real data. */
export function OverviewPanel({ onInspect, onNavigate }: { onInspect: (d: TradeDecision) => void; onNavigate: (t: Tab) => void }) {
  const { companyScore, paperPortfolio, riskWarnings, watchlist, decisions, agents } = useGameStore();
  const level = riskLevel(riskWarnings);
  const regime = marketRegimeHeuristic(watchlist);
  const recent = [...decisions].slice(-5).reverse();
  const noTrade = computeNoTradeStats(decisions);
  const latest = latestDecision(decisions);

  const workingCount = agents ? Object.values(agents).filter((a) => !["lobby", "break-room"].includes(a.location)).length : 0;

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
        <TerminalLabel>Market Regime</TerminalLabel>
        <div className="font-cmdmono text-cmd-text">{regime.label}</div>
        <div className="mt-1 text-[9px] text-cmd-textDim">{regime.detail}</div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Team Status</TerminalLabel>
        <DataRow label="Agents active" value={`${workingCount} / 9`} />
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
