import { useGameStore } from "@/ui/hooks/useGameStore";
import { EventBus } from "@/game/systems/EventBus";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { RISK_LEVEL_LABEL, formatMoney, formatPct, riskTextClass } from "./lib/derive";
import { simMonthNumber } from "./lib/financials";
import { useDashboardData } from "./lib/useDashboardData";
import { DataRow, EmptyState, Glass, RiskDot, StatusPill, TerminalLabel } from "./ui";

/** Fast-glance status card — everything a player needs to decide whether to open the Full Command Center, without leaving Quick View's single screen. Shares its data with OverviewPanel via useDashboardData() rather than recomputing it. */
export function QuickView({ onExpand }: { onExpand: () => void }) {
  const { paperPortfolio, riskLimits, riskWarnings } = useGameStore();
  const { equity, month, level, status, regime, opportunity, latest: decision, noTrade } = useDashboardData();

  const recommendation = decision === null ? "WAITING" : decision.outcome === "trade" ? "TRADE" : "NO TRADE";
  const recommendationTone = recommendation === "TRADE" ? "text-cmd-green" : recommendation === "NO TRADE" ? "text-cmd-amber" : "text-cmd-textDim";

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-cmdmono text-sm tracking-[0.2em] text-cmd-cyan">COMMAND CENTER</div>
          <div className="text-[9px] uppercase tracking-widest text-cmd-textDim">Quick View</div>
        </div>
        <StatusPill tone={status === "RISK LOCK" ? "red" : status === "ANALYZING" ? "cyan" : status === "ACTIVE" ? "green" : "neutral"}>{status}</StatusPill>
      </div>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Portfolio — Simulated Month {simMonthNumber(month.dayRange[0])}</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">Sim Day {month.dayRange[1]}</span>
        </div>
        <DataRow label="Account Value" value={formatMoney(equity)} />
        <DataRow label="Month Net P&L" value={formatMoney(month.netPnl)} valueClassName={month.netPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Month Return" value={formatPct(month.returnPct)} valueClassName={month.returnPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Month Max Drawdown" value={`${month.maxDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
        <DataRow label="Open Positions" value={`${paperPortfolio.positions.length} / ${riskLimits.maxOpenPositions}`} />
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Market Regime</TerminalLabel>
        <div className="font-cmdmono text-cmd-text">{regime.label}</div>
        <div className="mt-0.5 text-[9px] text-cmd-textDim">{regime.detail}</div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Top Opportunity</TerminalLabel>
        {opportunity === null ? (
          <EmptyState>No opportunity flagged yet.</EmptyState>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="font-cmdmono text-cmd-cyan">{opportunity.symbol ?? opportunity.title}</span>
              <span className="text-cmd-text">{Math.round(opportunity.confidence)}% confidence</span>
            </div>
            <div className="mt-0.5 text-[10px] text-cmd-textDim">
              {opportunity.title} — {AGENT_PROFILES[opportunity.assignedAgent].name} · {opportunity.status.replace("_", " ")}
            </div>
          </>
        )}
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Risk Alerts</TerminalLabel>
          <span className={`flex items-center gap-1 text-[9px] uppercase ${riskTextClass(level)}`}>
            <RiskDot level={level} /> {RISK_LEVEL_LABEL[level]}
          </span>
        </div>
        {riskWarnings.length === 0 ? (
          <EmptyState>No active risk warnings.</EmptyState>
        ) : (
          <div className="space-y-1">
            {riskWarnings.slice(0, 3).map((w) => (
              <div key={w.id} className={w.severity === "critical" ? "text-cmd-red" : "text-cmd-amber"}>
                [{w.symbol}] {w.message}
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>System Recommendation</TerminalLabel>
        <div className={`font-cmdmono text-lg tracking-wider ${recommendationTone}`}>{recommendation}</div>
        <div className="mt-0.5 text-[9px] text-cmd-textDim">
          {decision === null
            ? "No trade decisions recorded yet."
            : decision.outcome === "trade"
              ? decision.finalReasoning
              : `${decision.finalReasoning} — ${noTrade.noTradeCount} of ${noTrade.total} decisions were NO TRADE.`}
        </div>
      </Glass>

      <div className="mt-auto flex gap-2 pt-1">
        <button
          type="button"
          onClick={onExpand}
          className="flex-1 rounded-sm border border-cmd-cyan/50 bg-cmd-cyan/10 py-2 font-cmdmono text-[11px] tracking-wider text-cmd-cyan shadow-cmd-cyan transition-colors hover:bg-cmd-cyan/20"
        >
          EXPAND — FULL COMMAND CENTER
        </button>
        <button
          type="button"
          onClick={() => EventBus.emit("ui:campusMap", { open: true })}
          className="rounded-sm border border-cmd-border px-4 py-2 text-[11px] text-cmd-textDim transition-colors hover:border-cmd-cyan/50 hover:text-cmd-cyan"
          title="Company Campus Map (M)"
        >
          🗺 CAMPUS
        </button>
        <button
          type="button"
          onClick={() => EventBus.emit("ui:commandCenter", { open: false })}
          className="rounded-sm border border-cmd-border px-4 py-2 text-[11px] text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
        >
          CLOSE
        </button>
      </div>
    </div>
  );
}
