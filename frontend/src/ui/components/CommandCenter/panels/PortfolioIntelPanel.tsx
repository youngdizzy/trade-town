import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { EventBus } from "@/game/systems/EventBus";
import { computePeriodFinancials } from "../lib/financials";
import { formatMoney, riskLevel } from "../lib/derive";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

/**
 * v0.7 Feature 56 — Enterprise Portfolio Intelligence
 * (backend/app/portfolio_intelligence.py). Recomputed fresh every tick,
 * the same "cheap, always current, never a stale second copy" convention
 * companyHealth/marketIntelligence already use. Portfolio Heat here is a
 * real, visible READING — never an automatic corrective action (see
 * docs/ROADMAP.md's own v0.8 stop condition); nothing on this panel
 * places, closes, or resizes an order.
 */
const HEAT_TONE: Record<"cool" | "warm" | "hot" | "overheated", "green" | "cyan" | "amber" | "red"> = {
  cool: "cyan",
  warm: "green",
  hot: "amber",
  overheated: "red",
};

function strategyLabel(id: string | null, strategies: { id: string; name: string }[]): string {
  if (id === null) return "No strategy attributed";
  return strategies.find((s) => s.id === id)?.name ?? id;
}

const RISK_TONE: Record<"green" | "yellow" | "red", "green" | "amber" | "red"> = { green: "green", yellow: "amber", red: "red" };

/**
 * CEO directive "Portfolio Construction, Capital Allocation & Execution
 * Realism," Phase 11 — the directive's own "don't create another giant
 * tab collection" rule means this is an ADDITION to the existing
 * PORTFOLIO tab (already the closest real match per the Phase 1 audit),
 * not a new one. Every number here reuses an already-computed source
 * (PortfolioIntelligence, the same computePeriodFinancials() the
 * Performance tab already uses, the same riskLevel() the Risk tab
 * already uses) — nothing new is calculated. The cross-link buttons
 * point at the real detail sections this directive's own earlier phases
 * already built (Strategy Capital Allocation/Degradation Watch on
 * PERFORMANCE, Active Warnings/No-Trade Reasons on RISK) rather than
 * duplicating their content here.
 */
export function PortfolioCommandCenterStrip() {
  const { portfolioIntelligence: pi, paperPortfolio, time, strategies, riskWarnings } = useGameStore();
  const openUnrealized = paperPortfolio.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const today = computePeriodFinancials("today", paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);
  const allTime = computePeriodFinancials("allTime", paperPortfolio.tradeHistory, paperPortfolio.startingBalance, time, openUnrealized);
  const level = riskLevel(riskWarnings);
  const activeStrategies = strategies.filter((s) => s.stage !== "retired").length;

  return (
    <Glass className="border border-cmd-cyan/30 p-3 lg:col-span-2">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Portfolio Command Center</TerminalLabel>
        <StatusPill tone={RISK_TONE[level]}>{level === "green" ? "NORMAL" : level === "yellow" ? "ELEVATED" : "RESTRICTED"}</StatusPill>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
        <DataRow label="Equity" value={formatMoney(pi.equity)} />
        <DataRow label="Daily P&amp;L" value={formatMoney(today.netPnl)} valueClassName={today.netPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Total P&amp;L" value={formatMoney(allTime.netPnl)} valueClassName={allTime.netPnl >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Open Positions" value={paperPortfolio.positions.length} />
        <DataRow label="Gross Exposure" value={`${formatMoney(pi.exposure.grossExposure)} (${pi.exposure.grossExposurePct.toFixed(0)}%)`} />
        <DataRow label="Net Exposure" value={`${formatMoney(pi.exposure.netExposure)} (${pi.exposure.netExposurePct.toFixed(0)}%)`} />
        <DataRow label="Active Strategies" value={activeStrategies} />
        <DataRow label="Risk Utilization (Heat)" value={`${pi.heat.totalCapitalAtRiskPct.toFixed(0)}%`} valueClassName={HEAT_TONE[pi.heat.tier] === "red" ? "text-cmd-red" : undefined} />
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[9px]">
        <button type="button" onClick={() => EventBus.emit("ui:commandCenterJump", { tab: "PERFORMANCE" })} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Top Strategies (Capital Allocation)
        </button>
        <button type="button" onClick={() => EventBus.emit("ui:commandCenterJump", { tab: "PERFORMANCE" })} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Strategy Health (Degradation Watch)
        </button>
        <button type="button" onClick={() => EventBus.emit("ui:commandCenterJump", { tab: "RISK" })} className="text-cmd-cyan underline decoration-dotted hover:text-cmd-text">
          → Risk Alerts &amp; No-Trade Reasons
        </button>
      </div>
    </Glass>
  );
}

export function PortfolioIntelPanel() {
  const { portfolioIntelligence: pi, strategies } = useGameStore();

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <PortfolioCommandCenterStrip />

      <Glass className="p-3">
        <TerminalLabel>Capital Allocation</TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
          <DataRow label="Equity" value={`$${pi.equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
          <DataRow label="Cash" value={`$${pi.cashBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
          <DataRow label="Cash % of Equity" value={`${pi.cashPctOfEquity.toFixed(0)}%`} />
          <DataRow label="Deployed % of Equity" value={`${pi.deployedPctOfEquity.toFixed(0)}%`} />
        </div>
        <p className="mt-2 text-[9px] text-cmd-textDim">{pi.opportunityCost}</p>
      </Glass>

      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Portfolio Heat — a reading, never an automatic action</TerminalLabel>
          <StatusPill tone={HEAT_TONE[pi.heat.tier]}>{pi.heat.tier.toUpperCase()}</StatusPill>
        </div>
        <div className="space-y-2">
          <div>
            <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
              <span title="Gross notional exposure (quantity × price, every open position) as a % of equity — the tier thresholds below are calibrated for this scale.">Gross Notional Exposure</span>
              <span className="tabular-nums text-cmd-text">{pi.heat.totalCapitalAtRiskPct.toFixed(0)}%</span>
            </div>
            <Meter value={pi.heat.totalCapitalAtRiskPct} tone={HEAT_TONE[pi.heat.tier]} />
          </div>
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow label="Unrealized Drawdown" value={`${pi.heat.unrealizedDrawdownPct.toFixed(1)}%`} valueClassName={pi.heat.unrealizedDrawdownPct > 0 ? "text-cmd-red" : "text-cmd-text"} />
            <DataRow label="Largest Position" value={`${pi.heat.largestPositionPct.toFixed(0)}%`} />
            {pi.heat.hottestCategory && <DataRow label="Hottest Category" value={`${pi.heat.hottestCategory} (${pi.heat.hottestCategoryPct.toFixed(0)}%)`} />}
            {/* CEO directive "Portfolio Risk Engine + Firm-Wide Risk
                Governance, 11/10 Professional Quant Implementation," Phase
                2 — the real, separate, stop-distance-based reading,
                distinct from the notional exposure above. */}
            <DataRow label="Est. Capital at Risk (modeled)" value={`${pi.heat.estimatedCapitalAtRiskPct.toFixed(1)}%`} />
          </div>
          {pi.heat.capitalAtRiskDetail && <p className="text-[8px] italic text-cmd-textDim">{pi.heat.capitalAtRiskDetail}</p>}
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Exposure — real long / short / net / gross</TerminalLabel>
        <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
          <DataRow label={`Long (${pi.exposure.longPositionCount})`} value={`$${pi.exposure.longValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} valueClassName="text-cmd-green" />
          <DataRow label={`Short (${pi.exposure.shortPositionCount})`} value={`$${pi.exposure.shortValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} valueClassName="text-cmd-red" />
          <DataRow label="Net Exposure" value={`$${pi.exposure.netExposure.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${pi.exposure.netExposurePct.toFixed(0)}%)`} />
          <DataRow label="Gross Exposure" value={`$${pi.exposure.grossExposure.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${pi.exposure.grossExposurePct.toFixed(0)}%)`} />
        </div>
        <p className="mt-1.5 text-[9px] text-cmd-textDim">Net = directional bias (long − short). Gross = total capital genuinely at work, regardless of direction.</p>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Strategy Exposure — live, open positions only</TerminalLabel>
        {pi.strategyExposure.length === 0 ? (
          <EmptyState>No open positions — nothing to break down by strategy yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {pi.strategyExposure.map((exposure) => (
              <div key={exposure.strategyId ?? "unattributed"} className="text-[9px]">
                <div className="mb-0.5 flex items-center justify-between text-cmd-textDim">
                  <span className={exposure.strategyId === null ? "italic text-cmd-textDim" : "text-cmd-cyan"}>{strategyLabel(exposure.strategyId, strategies)}</span>
                  <span className="tabular-nums">
                    {exposure.positionCount} position{exposure.positionCount === 1 ? "" : "s"} · {exposure.pctOfEquity.toFixed(0)}% · risk {exposure.capitalAtRiskPctOfEquity.toFixed(1)}%
                  </span>
                </div>
                <Meter value={exposure.pctOfEquity} tone={exposure.strategyId === null ? "amber" : "cyan"} />
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Agent Exposure — live, open positions only</TerminalLabel>
        {pi.agentExposure.length === 0 ? (
          <EmptyState>No open positions — nothing to break down by agent yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {pi.agentExposure.map((exposure) => (
              <div key={exposure.agentId} className="text-[9px]">
                <div className="mb-0.5 flex items-center justify-between text-cmd-textDim">
                  <span className="text-cmd-cyan">{AGENT_PROFILES[exposure.agentId].name}</span>
                  <span className="tabular-nums">
                    {exposure.positionCount} position{exposure.positionCount === 1 ? "" : "s"} · {exposure.pctOfEquity.toFixed(0)}% · risk {exposure.capitalAtRiskPctOfEquity.toFixed(1)}%
                  </span>
                </div>
                <Meter value={exposure.pctOfEquity} tone="cyan" />
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Category Exposure — this codebase's honest stand-in for &quot;sector&quot;</TerminalLabel>
        {pi.categoryExposure.length === 0 ? (
          <EmptyState>No open positions — nothing to break down by category yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {pi.categoryExposure.map((exposure) => (
              <div key={exposure.category} className="text-[9px]">
                <div className="mb-0.5 flex items-center justify-between text-cmd-textDim">
                  <span className="capitalize text-cmd-text">{exposure.category}</span>
                  <span className="tabular-nums">
                    {exposure.positionCount} position{exposure.positionCount === 1 ? "" : "s"} · {exposure.pctOfEquity.toFixed(0)}% · risk {exposure.capitalAtRiskPctOfEquity.toFixed(1)}%
                  </span>
                </div>
                <Meter value={exposure.pctOfEquity} tone="cyan" />
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Correlation Intelligence — real Pearson correlation, held symbols only</TerminalLabel>
        {pi.correlationPairs.length === 0 ? (
          <EmptyState>No two currently-held symbols clear the correlation threshold — this portfolio's real exposure is genuinely diversified right now.</EmptyState>
        ) : (
          <div className="space-y-1">
            {pi.correlationPairs.map((pair) => (
              <div key={`${pair.symbolA}-${pair.symbolB}`} className="flex items-center justify-between rounded-sm border border-cmd-border/40 bg-cmd-bg/60 p-1.5 text-[9px]">
                <span className="text-cmd-text">
                  {pair.symbolA} ↔ {pair.symbolB}
                </span>
                <StatusPill tone={pair.direction === "positive" ? "amber" : "cyan"}>
                  {pair.direction} {pair.correlation.toFixed(2)}
                </StatusPill>
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Capital Efficiency — real profit per dollar, closed trades only</TerminalLabel>
        {pi.capitalEfficiency.tradesMeasured === 0 ? (
          <EmptyState>No closed trades yet — nothing to measure capital efficiency against.</EmptyState>
        ) : (
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow
              label="Profit per Dollar"
              value={`${pi.capitalEfficiency.profitPerDollar >= 0 ? "+" : ""}${(pi.capitalEfficiency.profitPerDollar * 100).toFixed(2)}%`}
              valueClassName={pi.capitalEfficiency.profitPerDollar >= 0 ? "text-cmd-green" : "text-cmd-red"}
            />
            <DataRow
              label="Profit per Dollar-Hour"
              value={`${pi.capitalEfficiency.profitPerDollarHour >= 0 ? "+" : ""}${(pi.capitalEfficiency.profitPerDollarHour * 100).toFixed(3)}%`}
              valueClassName={pi.capitalEfficiency.profitPerDollarHour >= 0 ? "text-cmd-green" : "text-cmd-red"}
            />
            <DataRow label="Trades Measured" value={pi.capitalEfficiency.tradesMeasured} />
          </div>
        )}
      </Glass>
    </div>
  );
}
