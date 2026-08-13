import { useEffect, useState } from "react";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { api } from "@/net/api";
import type { EvaluationPolicyComparisonReport, Strategy, StrategyCertification, StrategyDossier } from "@/types";
import { executiveStanceTone, experimentTierTone, strategyExecutiveActionTone, strategyLiquidityVerdictTone, strategyRegimeVerdictTone, strategyRiskRatingTone } from "../../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * v0.7 Feature 52 (Part 1) — "Certification": the brief's Monte Carlo
 * Testing / Market Regime Testing / Liquidity Validation / 9-department
 * Executive Review / Founder Approval / Confidence Score, assembled into
 * one real Strategy Dossier (GET /api/sandbox/dossier), computed fresh
 * every open — never a second source of truth. See
 * backend/app/strategy_lab.py's module docstring for the full honesty
 * boundary each artifact below observes. v0.7 Feature 53 adds the real
 * 15-point Company Certification checklist (GET /api/sandbox/certification)
 * at the top — `certified` is always a fresh read of current real state,
 * so a real Strategy Health decline automatically revokes it, visible
 * the next time this tab is opened.
 */
export function StrategyCertificationView({ selected }: { selected: Strategy }) {
  const [dossier, setDossier] = useState<StrategyDossier | null>(null);
  const [certification, setCertification] = useState<StrategyCertification | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Prop-Firm Risk Intelligence Addendum, Piece 10 — a real, on-demand
  // Monte Carlo evaluation-policy comparison. Fetched separately (not
  // part of Promise.all above) since it's slower and genuinely optional
  // — null both while loading and when the strategy has no completed
  // simulation runs to bootstrap from.
  const [evaluationPolicies, setEvaluationPolicies] = useState<EvaluationPolicyComparisonReport | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([api.getSandboxDossier(selected.id), api.getSandboxCertification(selected.id)])
      .then(([dossierRes, certificationRes]) => {
        if (!cancelled) {
          setDossier(dossierRes);
          setCertification(certificationRes);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected.id]);

  useEffect(() => {
    let cancelled = false;
    setEvaluationPolicies(null);
    api
      .getEvaluationPolicyComparison(selected.id)
      .then((res) => {
        if (!cancelled) setEvaluationPolicies(res);
      })
      .catch(() => {
        if (!cancelled) setEvaluationPolicies(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selected.id]);

  if (loading && !dossier) {
    return (
      <Glass className="p-3">
        <EmptyState>Assembling this strategy's real validation dossier…</EmptyState>
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
  if (!dossier) return null;

  const { monteCarlo, regimeTest, liquidityValidation, executiveReview, founderApproval, confidence, experimentTier, experimentTierRationale } = dossier;
  const hasAnyEvidence = monteCarlo || regimeTest || liquidityValidation || executiveReview || founderApproval || confidence;

  return (
    <div className="space-y-3">
      {certification && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Company Certification — 15 real requirements, always a live read of current state</TerminalLabel>
            <StatusPill tone={certification.certified ? "green" : "red"}>{certification.certified ? "CERTIFIED" : "NOT CERTIFIED"}</StatusPill>
          </div>
          <p className="mb-2 text-[9px] text-cmd-textDim">
            Only Certified strategies may deploy real company capital. Recomputed fresh every time this opens — a real decline in this strategy's own Health can revoke Certification
            automatically, with no separate action needed.
          </p>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {certification.requirements.map((r) => (
              <div key={r.id} className="flex items-start gap-1.5 text-[9px]">
                <StatusPill tone={r.met ? "green" : "red"}>{r.met ? "✓" : "✗"}</StatusPill>
                <div className="flex-1">
                  <div className="text-cmd-text">{r.label}</div>
                  <div className="text-cmd-textDim">{r.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </Glass>
      )}

      {!hasAnyEvidence && (
        <Glass className="p-3">
          <EmptyState>No real validation evidence on file yet — run Market Simulations and request a Company Review from the Pipeline tab first.</EmptyState>
        </Glass>
      )}

      {confidence && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Confidence Score — a real composite, never independently estimated</TerminalLabel>
            <StatusPill tone={strategyRiskRatingTone(confidence.riskRating)}>{confidence.overallConfidencePct.toFixed(0)}/100 · {confidence.riskRating.toUpperCase()} RISK</StatusPill>
          </div>
          <DataRow label="Recommended Position Size" value={`${confidence.recommendedPositionSizePct.toFixed(1)}%`} />
          {confidence.recommendedMarketConditions.length > 0 && <DataRow label="Recommended Conditions" value={confidence.recommendedMarketConditions.join(", ")} />}
          <div className="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-green">Known Strengths</div>
              {confidence.knownStrengths.map((s, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  · {s}
                </div>
              ))}
            </div>
            <div>
              <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-amber">Known Weaknesses</div>
              {confidence.knownWeaknesses.map((s, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  · {s}
                </div>
              ))}
            </div>
          </div>
        </Glass>
      )}

      {monteCarlo && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Monte Carlo Testing — {monteCarlo.pathsSimulated} simulated trade sequences, real generating statistics</TerminalLabel>
            {experimentTier && <StatusPill tone={experimentTierTone(experimentTier)}>{experimentTier.toUpperCase()} EXPERIMENT</StatusPill>}
          </div>
          {experimentTierRationale && <p className="mb-1.5 text-[8px] italic text-cmd-textDim">{experimentTierRationale}</p>}
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
            <DataRow label="Median Return" value={`${monteCarlo.medianReturnPct >= 0 ? "+" : ""}${monteCarlo.medianReturnPct.toFixed(1)}%`} valueClassName={monteCarlo.medianReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"} />
            <DataRow label="Return Range (10th–90th)" value={`${monteCarlo.returnRangeLowPct.toFixed(1)}% – ${monteCarlo.returnRangeHighPct.toFixed(1)}%`} />
            <DataRow label="Probability Of Profit" value={`${monteCarlo.probabilityOfProfitPct.toFixed(0)}%`} />
            <DataRow label="Median Max Drawdown" value={`${monteCarlo.medianMaxDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
            <DataRow label="Worst-Case Drawdown (5th pct.)" value={`${monteCarlo.worstCaseDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
            <DataRow
              label="Probability Of Ruin"
              value={`${monteCarlo.probabilityOfRuinPct.toFixed(1)}%`}
              valueClassName={monteCarlo.probabilityOfRuinPct > 10 ? "text-cmd-red" : "text-cmd-text"}
            />
            <DataRow label="VaR (95th / 99th pct.)" value={`${monteCarlo.valueAtRisk95Pct.toFixed(1)}% / ${monteCarlo.valueAtRisk99Pct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
            <DataRow label="CVaR (95th / 99th pct.)" value={`${monteCarlo.conditionalValueAtRisk95Pct.toFixed(1)}% / ${monteCarlo.conditionalValueAtRisk99Pct.toFixed(1)}%`} valueClassName="text-cmd-red" />
          </div>
          <p className="mt-1.5 text-[8px] italic text-cmd-textDim">
            A real share of these {monteCarlo.pathsSimulated} simulated paths that breached a named drawdown bar — not a true infinite-sample probability of ruin. Drawn from this
            strategy's own real {monteCarlo.sourceWinRate.toFixed(0)}% win rate / {monteCarlo.sourceAvgWinPct.toFixed(1)}% avg win / {monteCarlo.sourceAvgLossPct.toFixed(1)}% avg loss.
          </p>
          <p className="mt-1 text-[8px] italic text-cmd-textDim">
            VaR/CVaR are real percentile and tail-mean reads off this same bootstrap's own sorted final-return array — no new simulation. VaR is the return level such that only
            5%/1% of paths did worse; CVaR is the mean return among exactly that worst 5%/1% of paths — what to expect given you're already in the tail.
          </p>
        </Glass>
      )}

      {evaluationPolicies && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Evaluation-Level Risk-Policy Comparison — {evaluationPolicies.policies[0]?.pathsSimulated ?? 0} paths/policy, real Monte Carlo race</TerminalLabel>
          </div>
          <p className="mb-2 text-[8px] italic text-cmd-textDim">{evaluationPolicies.researchQuestion}</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] border-collapse text-left text-[9px]">
              <thead>
                <tr className="border-b border-cmd-border/50 text-cmd-textDim">
                  <th className="py-1 pr-2 font-normal">Policy</th>
                  <th className="py-1 pr-2 font-normal">Risk/Trade</th>
                  <th className="py-1 pr-2 font-normal">P(Pass)</th>
                  <th className="py-1 pr-2 font-normal">P(Fail DD)</th>
                  <th className="py-1 pr-2 font-normal">P(Fail Time)</th>
                  <th className="py-1 pr-2 font-normal">Days to Pass</th>
                  <th className="py-1 pr-2 font-normal">Median DD</th>
                  <th className="py-1 pr-2 font-normal">Worst-Case DD</th>
                  <th className="py-1 pr-2 font-normal">P(Loss Streak)</th>
                </tr>
              </thead>
              <tbody>
                {evaluationPolicies.policies.map((p) => (
                  <tr key={p.policyId} className="border-b border-cmd-border/20">
                    <td className="py-1 pr-2 text-cmd-text">{p.label}</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-text">{p.riskPerTradePct.toFixed(2)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-green">{p.probabilityOfPassingPct.toFixed(1)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-red">{p.probabilityOfFailingDrawdownPct.toFixed(1)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-amber">{p.probabilityOfFailingTimeExpiryPct.toFixed(1)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-text">{p.expectedTradingDaysToPass !== null ? p.expectedTradingDaysToPass.toFixed(0) : "—"}</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-amber">{p.medianMaxDrawdownPct.toFixed(1)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-red">{p.worstCaseMaxDrawdownPct.toFixed(1)}%</td>
                    <td className="py-1 pr-2 tabular-nums text-cmd-text">
                      {p.probabilityOfConsecutiveLossStreakPct.toFixed(1)}% (≥{p.consecutiveLossStreakThreshold})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[8px] italic text-cmd-amber">{evaluationPolicies.conclusion}</p>
          <details className="mt-1.5">
            <summary className="cursor-pointer text-[8px] text-cmd-textDim">Assumptions &amp; limitations ({evaluationPolicies.assumptions.length + evaluationPolicies.limitations.length})</summary>
            <div className="mt-1 space-y-0.5">
              {evaluationPolicies.assumptions.map((a, i) => (
                <div key={`a-${i}`} className="text-[8px] italic text-cmd-textDim/80">
                  · {a}
                </div>
              ))}
              {evaluationPolicies.limitations.map((l, i) => (
                <div key={`l-${i}`} className="text-[8px] italic text-cmd-textDim/80">
                  · {l}
                </div>
              ))}
            </div>
          </details>
        </Glass>
      )}

      {regimeTest && (
        <Glass className="p-3">
          <TerminalLabel>Market Regime Testing — real performance bucketed by Testing Environment</TerminalLabel>
          <div className="space-y-1">
            {regimeTest.buckets.map((b) => (
              <div key={b.scenario} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                <div>
                  <span className="text-cmd-cyan">{b.scenario.replace(/_/g, " ")}</span>
                  <span className="ml-1.5 text-cmd-textDim">({b.regimes.join(", ")})</span>
                </div>
                {b.tested ? (
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums text-cmd-textDim">
                      {b.avgReturnPct >= 0 ? "+" : ""}
                      {b.avgReturnPct.toFixed(1)}% · {b.avgWinRate.toFixed(0)}% WR · {b.runCount} run{b.runCount === 1 ? "" : "s"}
                    </span>
                    <StatusPill tone={strategyRegimeVerdictTone(b.verdict)}>{b.verdict}</StatusPill>
                  </div>
                ) : (
                  <StatusPill tone="neutral">untested</StatusPill>
                )}
              </div>
            ))}
          </div>
        </Glass>
      )}

      {liquidityValidation && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Liquidity Validation — real conditions against this strategy's own watched symbols</TerminalLabel>
            <StatusPill tone={strategyLiquidityVerdictTone(liquidityValidation.verdict)}>{liquidityValidation.verdict}</StatusPill>
          </div>
          <p className="text-[9px] text-cmd-text">{liquidityValidation.detail}</p>
          <DataRow label="Symbols Checked" value={liquidityValidation.symbolsChecked.join(", ")} />
          <DataRow label="Real Sweep Rate" value={`${liquidityValidation.realSweepRatePct.toFixed(0)}%`} />
        </Glass>
      )}

      {executiveReview && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Executive Review — 9 real departments</TerminalLabel>
            <StatusPill tone={strategyExecutiveActionTone(executiveReview.recommendation)}>
              {executiveReview.recommendation.replace(/_/g, " ")} · {executiveReview.overallConfidencePct.toFixed(0)}/100
            </StatusPill>
          </div>
          <p className="mb-2 text-[9px] text-cmd-text">{executiveReview.reason}</p>
          <div className="space-y-1.5">
            {executiveReview.opinions.map((o) => (
              <div key={o.role} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <div className="flex items-center justify-between">
                  <span className="text-cmd-cyan">
                    {o.departmentLabel}
                    {o.agentId && <span className="ml-1 text-cmd-textDim">({AGENT_PROFILES[o.agentId].name})</span>}
                  </span>
                  <StatusPill tone={executiveStanceTone(o.stance)}>{o.stance.replace(/_/g, " ")}</StatusPill>
                </div>
                {o.evidence.map((e, i) => (
                  <div key={i} className="mt-0.5 text-cmd-text">
                    · {e}
                  </div>
                ))}
                {o.concerns.map((c, i) => (
                  <div key={i} className="mt-0.5 text-cmd-amber">
                    ⚠ {c}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </Glass>
      )}

      {founderApproval && (
        <Glass className="p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <TerminalLabel>Founder Approval</TerminalLabel>
            <StatusPill tone={founderApproval.verdict === "approved" ? "green" : "red"}>{founderApproval.verdict}</StatusPill>
          </div>
          <p className="text-[9px] text-cmd-text">{founderApproval.verdictReason}</p>
          <DataRow label="Confidence At Decision" value={`${founderApproval.confidencePct.toFixed(0)}/100`} />
        </Glass>
      )}
    </div>
  );
}
