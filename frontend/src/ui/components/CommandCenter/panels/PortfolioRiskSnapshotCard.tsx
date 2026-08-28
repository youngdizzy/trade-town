import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { PortfolioRiskSnapshot, PortfolioRiskState } from "@/types";
import { formatMoney } from "../lib/derive";
import { DataRow, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const STATE_TONE: Record<PortfolioRiskState, "green" | "amber" | "red"> = {
  normal: "green",
  warning: "amber",
  restricted: "amber",
  halted: "red",
};

const STATE_LABEL: Record<PortfolioRiskState, string> = {
  normal: "NORMAL",
  warning: "WARNING",
  restricted: "RESTRICTED",
  halted: "HALTED",
};

/**
 * CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance" —
 * the canonical, real, danger-first portfolio risk read
 * (backend/app/portfolio_risk.py::compute_portfolio_risk_snapshot()).
 * Composed entirely from already-real state (portfolio exposure,
 * correlation, the real fixed peak-to-trough drawdown, the real daily
 * circuit breaker, the real Emergency Stop flag) — never a second risk
 * computation and never an automatic corrective action. Placed first in
 * the RISK tab, ahead of every other card, matching the directive's own
 * explicit priority order: danger, then exposure, then P&L, then
 * available risk, then explanation.
 */
export function PortfolioRiskSnapshotCard() {
  const [snapshot, setSnapshot] = useState<PortfolioRiskSnapshot | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => api.getPortfolioRiskSnapshot().then((res) => !cancelled && setSnapshot(res)).catch(() => undefined);
    load();
    const interval = setInterval(load, 15_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!snapshot) return null;

  const drawdownPct = snapshot.maxDrawdownLimitPct > 0 ? (snapshot.currentDrawdownPct / snapshot.maxDrawdownLimitPct) * 100 : 0;
  const drawdownTone = drawdownPct >= 100 ? "red" : drawdownPct >= 75 ? "amber" : "cyan";

  return (
    <Glass className={`border p-3 ${snapshot.riskState === "halted" ? "border-cmd-red/50 bg-cmd-red/5" : snapshot.riskState !== "normal" ? "border-cmd-amber/50 bg-cmd-amber/5" : ""}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Portfolio Risk Engine — canonical firm-wide read</TerminalLabel>
        <StatusPill tone={STATE_TONE[snapshot.riskState]}>{STATE_LABEL[snapshot.riskState]}</StatusPill>
      </div>

      {snapshot.riskStateReasons.length > 0 && (
        <div className="mb-2 space-y-0.5">
          {snapshot.riskStateReasons.map((reason, i) => (
            <div key={i} className="text-[9px] text-cmd-amber">
              ⚠ {reason}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
        <DataRow label="Equity" value={formatMoney(snapshot.equity)} />
        <DataRow label="Gross Exposure" value={`${formatMoney(snapshot.grossExposureUsd)} (${snapshot.grossExposurePct.toFixed(0)}%)`} />
        <DataRow label="Net Exposure" value={`${formatMoney(snapshot.netExposureUsd)} (${snapshot.netExposurePct.toFixed(0)}%)`} />
        <DataRow label="Leverage" value={`${snapshot.leverage.toFixed(2)}x`} />
        <DataRow label="Open Positions" value={`${snapshot.openPositionsCount} / ${snapshot.maxOpenPositions}`} />
        <DataRow label="Daily P&amp;L" value={`${snapshot.dailyPnlPct >= 0 ? "+" : ""}${snapshot.dailyPnlPct.toFixed(1)}%`} valueClassName={snapshot.dailyPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
        <DataRow label="Daily Circuit Breaker" value={snapshot.dailyCircuitBreakerTier.toUpperCase()} />
        <DataRow label="Emergency Stop" value={snapshot.emergencyStopActive ? "ACTIVE" : "off"} valueClassName={snapshot.emergencyStopActive ? "text-cmd-red" : undefined} />
      </div>

      <div className="mt-2">
        <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
          <span>Real Drawdown (from own real peak equity)</span>
          <span className="tabular-nums text-cmd-text">
            {snapshot.currentDrawdownPct.toFixed(1)}% / {snapshot.maxDrawdownLimitPct.toFixed(0)}% limit
          </span>
        </div>
        <Meter value={drawdownPct} tone={drawdownTone} />
      </div>

      {snapshot.correlatedClusters.length > 0 && (
        <div className="mt-2">
          <div className="mb-1 text-[9px] text-cmd-textDim">
            Correlated exposure clusters — largest is {snapshot.largestCorrelatedClusterPct.toFixed(1)}% of equity
          </div>
          <div className="space-y-1">
            {snapshot.correlatedClusters.map((cluster) => (
              <div key={cluster.symbols.join("-")} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="flex items-center justify-between">
                  <span className="text-cmd-cyan">{cluster.symbols.join(" + ")}</span>
                  <span className="tabular-nums text-cmd-text">
                    {formatMoney(cluster.totalExposureUsd)} ({cluster.totalExposurePct.toFixed(1)}%)
                  </span>
                </div>
                <div className="mt-0.5 text-cmd-textDim">{cluster.detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Glass>
  );
}
