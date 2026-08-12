import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { useGameStore } from "@/ui/hooks/useGameStore";
import type { BehavioralCircuitBreakerStatus, DailyCircuitBreakerTier, ProcessAdherenceSummaryRead } from "@/types";
import {
  computeDrawdownSummary,
  computeRiskComplianceSummary,
  computeStrategyExpectancySummary,
  recentStrategyHealthByStrategy,
  strategyHealthTone,
  type RiskComplianceStatus,
} from "../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * Trading Psychology & Discipline, Piece G — the final piece of the
 * CEO's trading-psychology roadmap: one dashboard tab surfacing the
 * seven metrics named in the brief (Process Adherence, Behavioral Risk,
 * Loss Streak, Risk Compliance, Strategy Expectancy, Drawdown, Recent
 * Strategy Performance). This is a synthesis view, not a re-
 * implementation — every number here already exists somewhere real in
 * this codebase:
 *   - Behavioral Risk and Loss Streak already have their own real,
 *     WS-broadcast fields (see TradingModesPanel.tsx, which remains the
 *     full-detail view for both).
 *   - Risk Compliance, Strategy Expectancy, Drawdown, and Recent
 *     Strategy Performance are pure client-side compositions of
 *     already-real WS state (lib/derive.ts) — the same "derive from the
 *     wire, never round-trip the backend for a number already there"
 *     convention lib/financials.ts established.
 *   - Process Adherence is the one metric with no existing company-wide
 *     aggregate (every other consumer reads a single decision by id),
 *     so it's the one real new backend endpoint this piece adds
 *     (GET /api/executive/process-adherence-summary).
 */

const TIER_LABEL: Record<DailyCircuitBreakerTier, string> = {
  none: "Normal",
  tier1: "Tier 1",
  tier2: "Tier 2",
  tier3: "Tier 3",
  tier4: "Tier 4",
};

function tierTone(tier: DailyCircuitBreakerTier): "green" | "cyan" | "amber" | "red" {
  if (tier === "none") return "green";
  if (tier === "tier1") return "cyan";
  if (tier === "tier2" || tier === "tier3") return "amber";
  return "red";
}

function behavioralTone(status: BehavioralCircuitBreakerStatus): "green" | "amber" | "red" {
  if (status === "clear") return "green";
  if (status === "warning") return "amber";
  return "red";
}

function riskComplianceTone(status: RiskComplianceStatus): "green" | "amber" | "red" {
  if (status === "compliant") return "green";
  if (status === "warning") return "amber";
  return "red";
}

export function PsychologyDashboardPanel() {
  const { behavioralCircuitBreaker, losingStreak, dailyCircuitBreaker, riskWarnings, paperPortfolio, riskLimits, strategies, simulationResults, performanceSnapshots, strategyHealthAssessments } =
    useGameStore();

  const [processAdherenceSummary, setProcessAdherenceSummary] = useState<ProcessAdherenceSummaryRead | null>(null);

  useEffect(() => {
    api.getProcessAdherenceSummary().then(setProcessAdherenceSummary).catch(() => setProcessAdherenceSummary(null));
  }, []);

  const riskCompliance = computeRiskComplianceSummary(dailyCircuitBreaker, riskWarnings, paperPortfolio, riskLimits);
  const expectancy = computeStrategyExpectancySummary(strategies, simulationResults);
  const drawdown = computeDrawdownSummary(paperPortfolio, riskLimits, performanceSnapshots);
  const recentStrategyHealth = recentStrategyHealthByStrategy(strategyHealthAssessments).slice(0, 5);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <TerminalLabel>Process Adherence — average over the most recent decisions</TerminalLabel>
          {processAdherenceSummary === null ? (
            <EmptyState>Loading…</EmptyState>
          ) : (
            <div className="text-[9px]">
              <div className="mb-1 flex items-center gap-1.5">
                <StatusPill tone={processAdherenceSummary.averageScorePct !== null && processAdherenceSummary.averageScorePct >= 70 ? "green" : processAdherenceSummary.averageScorePct !== null ? "amber" : "neutral"}>
                  {processAdherenceSummary.averageScorePct !== null ? `${processAdherenceSummary.averageScorePct.toFixed(0)}%` : "N/A"}
                </StatusPill>
                <span className="text-cmd-textDim">
                  {processAdherenceSummary.decisionsWithVerifiedChecks} of {processAdherenceSummary.decisionsReviewed} recent decisions had verifiable checks
                </span>
              </div>
              <p className="text-cmd-textDim">See the DECISIONS tab for any individual decision's own real, per-check breakdown.</p>
            </div>
          )}
        </Glass>

        <Glass className="p-3">
          <div className="mb-1 flex items-center justify-between">
            <TerminalLabel>Behavioral Risk — revenge-trading detector</TerminalLabel>
            <StatusPill tone={behavioralTone(behavioralCircuitBreaker.status)}>{behavioralCircuitBreaker.status.toUpperCase()}</StatusPill>
          </div>
          {behavioralCircuitBreaker.status === "clear" ? (
            <EmptyState>No behavioral risk detected.</EmptyState>
          ) : (
            <div className="text-[9px]">
              {behavioralCircuitBreaker.reasons.map((reason, i) => (
                <p key={i} className="text-cmd-textDim">
                  {reason}
                </p>
              ))}
            </div>
          )}
          <p className="mt-1 text-cmd-textDim">See TRADINGMODES for the full read.</p>
        </Glass>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <div className="mb-1 flex items-center justify-between">
            <TerminalLabel>Loss Streak</TerminalLabel>
            {losingStreak.pauseActive && <StatusPill tone="amber">PAUSED</StatusPill>}
          </div>
          <div className="text-[9px]">
            <DataRow label="Consecutive Losses" value={losingStreak.consecutiveLosses} valueClassName={losingStreak.consecutiveLosses > 0 ? "text-cmd-amber" : "text-cmd-text"} />
            <DataRow label="Pause Threshold" value={losingStreak.pauseThreshold} />
            <DataRow label="Emergency Stop Threshold" value={losingStreak.suspendThreshold} />
          </div>
        </Glass>

        <Glass className="p-3">
          <div className="mb-1 flex items-center justify-between">
            <TerminalLabel>Risk Compliance</TerminalLabel>
            <StatusPill tone={riskComplianceTone(riskCompliance.status)}>{riskCompliance.status.toUpperCase()}</StatusPill>
          </div>
          <div className="text-[9px]">
            <DataRow label="Daily Circuit Breaker" value={TIER_LABEL[riskCompliance.dailyCircuitBreakerTier]} valueClassName={tierTone(riskCompliance.dailyCircuitBreakerTier) === "red" ? "text-cmd-red" : undefined} />
            <DataRow label="Active Risk Warnings" value={riskCompliance.activeWarningCount} valueClassName={riskCompliance.activeWarningCount > 0 ? "text-cmd-amber" : "text-cmd-text"} />
            <DataRow label="Critical Warnings" value={riskCompliance.criticalWarningCount} valueClassName={riskCompliance.criticalWarningCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
            <DataRow label="Drawdown vs. Limit" value={`${riskCompliance.drawdownPct.toFixed(1)}% / ${riskCompliance.drawdownLimitPct.toFixed(0)}%`} valueClassName={riskCompliance.withinDrawdownLimit ? "text-cmd-text" : "text-cmd-red"} />
          </div>
        </Glass>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Glass className="p-3">
          <TerminalLabel>Drawdown</TerminalLabel>
          <div className="text-[9px]">
            <DataRow label="Current Drawdown" value={`${drawdown.currentDrawdownPct.toFixed(1)}%`} valueClassName={drawdown.withinLimit ? "text-cmd-text" : "text-cmd-red"} />
            <DataRow label="Configured Limit" value={`${drawdown.drawdownLimitPct.toFixed(0)}%`} />
            {drawdown.latestWindowMaxDrawdownPct !== null && (
              <DataRow label={`Worst Losing Trade (${drawdown.latestWindowPeriod})`} value={`${drawdown.latestWindowMaxDrawdownPct.toFixed(1)}%`} />
            )}
          </div>
        </Glass>

        <Glass className="p-3">
          <TerminalLabel>Strategy Expectancy — company-wide average across tested strategies</TerminalLabel>
          {expectancy.strategyCount === 0 ? (
            <EmptyState>No strategies with real simulation results yet.</EmptyState>
          ) : (
            <div className="text-[9px]">
              <DataRow
                label="Average Expectancy"
                value={expectancy.averageExpectancyPct !== null ? `${expectancy.averageExpectancyPct >= 0 ? "+" : ""}${expectancy.averageExpectancyPct.toFixed(2)}%` : "N/A"}
                valueClassName={expectancy.averageExpectancyPct !== null && expectancy.averageExpectancyPct >= 0 ? "text-cmd-green" : "text-cmd-red"}
              />
              <DataRow label="Strategies Tested" value={expectancy.strategyCount} />
              {expectancy.bestStrategyName !== null && <DataRow label="Best" value={`${expectancy.bestStrategyName} (${expectancy.bestExpectancyPct?.toFixed(2)}%)`} />}
              {expectancy.worstStrategyName !== null && <DataRow label="Weakest" value={`${expectancy.worstStrategyName} (${expectancy.worstExpectancyPct?.toFixed(2)}%)`} />}
            </div>
          )}
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Recent Strategy Performance — most recent real health assessment per strategy</TerminalLabel>
        {recentStrategyHealth.length === 0 ? (
          <EmptyState>No strategy health assessments yet.</EmptyState>
        ) : (
          <div className="space-y-1">
            {recentStrategyHealth.map((assessment) => (
              <div key={assessment.strategyId} className="flex items-center justify-between gap-2 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 px-2 py-1 text-[9px]">
                <span className="text-cmd-text">{assessment.strategyName}</span>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-cmd-textDim">
                    {assessment.recentWinRate.toFixed(0)}% win · {assessment.recentAvgReturnPct >= 0 ? "+" : ""}
                    {assessment.recentAvgReturnPct.toFixed(1)}%
                  </span>
                  <StatusPill tone={strategyHealthTone(assessment.status)}>{assessment.status.replace(/_/g, " ")}</StatusPill>
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
