import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { Strategy, StrategyMatch } from "@/types";
import { Glass, StatusPill, TerminalLabel } from "../../ui";

const RISK_TONE: Record<StrategyMatch["recommendedRiskLevel"], "green" | "cyan" | "amber" | "red"> = {
  minimal: "green",
  reduced: "amber",
  normal: "cyan",
  elevated: "red",
};

function strategyLabel(id: string, strategies: Strategy[]): string {
  return strategies.find((s) => s.id === id)?.name ?? id;
}

/**
 * CEO directive "Strategy Intelligence + Live Strategy Attribution,"
 * Phase 11 — "TODAY: strategies currently eligible / strategies
 * currently blocked." Reuses the exact same real
 * `compute_strategy_match()` read `MarketIntelPanel.tsx`'s Evidence
 * Confluence card already shows — but that one reads the once-daily
 * `MarketIntelligenceReport`'s own copy, which that schema's own
 * docstring discloses "can be up to a day stale." This fetches the
 * SAME real computation fresh, on demand, against the always-current
 * live regime — never a fabricated second reading.
 */
export function LiveStrategyEligibilityCard({ strategies }: { strategies: Strategy[] }) {
  const [match, setMatch] = useState<StrategyMatch | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getLiveStrategyEligibility()
      .then((result) => {
        if (!cancelled) setMatch(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return null;
  if (!match) return null;

  return (
    <Glass className="p-3">
      <div className="mb-1 flex items-center justify-between">
        <TerminalLabel>Today — Strategy Eligibility, Right Now</TerminalLabel>
        <StatusPill tone={RISK_TONE[match.recommendedRiskLevel]}>{match.recommendedRiskLevel} risk</StatusPill>
      </div>
      <p className="text-[9px] text-cmd-textDim">{match.detail}</p>
      {match.recommendedStrategyIds.length > 0 && (
        <div className="mt-1 text-[9px] text-cmd-green">Eligible: {match.recommendedStrategyIds.map((id) => strategyLabel(id, strategies)).join(", ")}</div>
      )}
      {match.avoidedStrategyIds.length > 0 && (
        <div className="mt-0.5 text-[9px] text-cmd-red">Blocked: {match.avoidedStrategyIds.map((id) => strategyLabel(id, strategies)).join(", ")}</div>
      )}
    </Glass>
  );
}
