import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { StrategyExecutiveDashboard, StrategyExecutiveDashboardEntry } from "@/types";
import { useMonteCarloReliability } from "../../lib/useMonteCarloReliability";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const RELIABILITY_TONE: Record<string, "green" | "amber" | "red"> = {
  reliable: "green",
  marginal: "amber",
  unreliable: "red",
};

/**
 * Quantitative Research & Intelligence System, Piece 7 — Forge, the
 * Quant Developer. A real, standing engineering fact about the Monte
 * Carlo bootstrap pipeline itself (not a per-strategy finding — see
 * backend/app/quant_developer.py's module docstring), so it lives on
 * this company-wide dashboard rather than the per-strategy
 * Certification view.
 */
function MonteCarloReliabilityCard() {
  const { assessment, loading, error } = useMonteCarloReliability(true);

  if (loading && !assessment) {
    return (
      <Glass className="p-3">
        <EmptyState>Forge is auditing the Monte Carlo pipeline…</EmptyState>
      </Glass>
    );
  }
  if (error) {
    return (
      <Glass className="p-3">
        <div className="text-[9px] text-cmd-red">{error}</div>
      </Glass>
    );
  }
  if (!assessment) return null;

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Monte Carlo Reliability — Forge, Quant Developer</TerminalLabel>
        {!assessment.observedPathCountsConsistent && <StatusPill tone="red">PATH COUNT DRIFT</StatusPill>}
      </div>
      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
        <DataRow label="Paths Simulated" value={assessment.pathsSimulated} />
        <DataRow label="5% Tail Samples" value={assessment.tailSampleCount95Pct} />
        <DataRow label="1% Tail Samples" value={assessment.tailSampleCount99Pct} />
        <DataRow label="Real Results Audited" value={assessment.realResultsAudited} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <StatusPill tone={RELIABILITY_TONE[assessment.verdict95Pct]}>VaR95/CVaR95: {assessment.verdict95Pct.toUpperCase()}</StatusPill>
        <StatusPill tone={RELIABILITY_TONE[assessment.verdict99Pct]}>VaR99/CVaR99: {assessment.verdict99Pct.toUpperCase()}</StatusPill>
      </div>
      <p className="mt-1.5 text-[8px] italic text-cmd-textDim">{assessment.reasoning}</p>
      <p className="mt-1 text-[8px] italic text-cmd-textDim">{assessment.thresholdSource}</p>
    </Glass>
  );
}

function Slot({ label, entry, tone }: { label: string; entry: StrategyExecutiveDashboardEntry | null; tone: "green" | "red" | "cyan" | "amber" | "purple" }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
      <div className="mb-1 uppercase tracking-wide text-cmd-textDim">{label}</div>
      {entry ? (
        <>
          <div className="text-cmd-cyan">{entry.strategyName}</div>
          <StatusPill tone={tone}>
            {entry.metricLabel}
            {entry.metricLabel !== "Most recently created" ? `: ${entry.metricValue.toFixed(1)}` : ""}
          </StatusPill>
        </>
      ) : (
        <span className="text-cmd-textDim">Not enough real evidence yet</span>
      )}
    </div>
  );
}

/**
 * v0.7 Feature 52 (Part 2) — the Executive Dashboard. Read-only,
 * computed fresh every open (GET /api/sandbox/dashboard) — every count
 * and named slot reads already-real Strategy/SimulationResult/review
 * history, never a second source of truth. See
 * backend/app/strategy_lab.py's compute_strategy_executive_dashboard().
 */
export function StrategyExecutiveDashboardView() {
  const [dashboard, setDashboard] = useState<StrategyExecutiveDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    setError(null);
    api
      .getSandboxDashboard()
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  if (loading && !dashboard) {
    return (
      <Glass className="p-3">
        <EmptyState>Assembling the real company-wide strategy aggregate…</EmptyState>
      </Glass>
    );
  }
  if (error) {
    return (
      <Glass className="p-3">
        <div className="text-[9px] text-cmd-red">{error}</div>
      </Glass>
    );
  }
  if (!dashboard) return null;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Portfolio Overview — real stage counts</TerminalLabel>
          <button type="button" onClick={refresh} className="rounded-sm border border-cmd-border px-2 py-0.5 text-[9px] uppercase text-cmd-textDim hover:border-cmd-cyan/50 hover:text-cmd-cyan">
            Refresh
          </button>
        </div>
        <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
          <DataRow label="Active" value={dashboard.activeCount} />
          <DataRow label="In Development" value={dashboard.inDevelopmentCount} />
          <DataRow label="In Validation" value={dashboard.inValidationCount} />
          <DataRow label="Paper Trading" value={dashboard.paperTradingCount} />
          <DataRow label="Approved" value={dashboard.approvedCount} />
          <DataRow label="Retired" value={dashboard.retiredCount} />
          <DataRow label="Hall Of Fame" value={dashboard.hallOfFameCount} valueClassName="text-cmd-green" />
          <DataRow label="Failed Archive" value={dashboard.failedArchiveCount} valueClassName="text-cmd-amber" />
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Named Slots — each citing the real metric that earned it</TerminalLabel>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <Slot label="Best Strategy" entry={dashboard.bestStrategy} tone="green" />
          <Slot label="Weakest Strategy" entry={dashboard.weakestStrategy} tone="red" />
          <Slot label="Most Improved" entry={dashboard.mostImprovedStrategy} tone="cyan" />
          <Slot label="Newest" entry={dashboard.newestStrategy} tone="purple" />
          <Slot label="Highest Confidence" entry={dashboard.highestConfidenceStrategy} tone="cyan" />
        </div>
      </Glass>

      <MonteCarloReliabilityCard />
    </div>
  );
}
