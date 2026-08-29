import { useEffect, useState } from "react";
import { api } from "@/net/api";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { AgentBrierCalibration, BrierCalibrationSummary } from "@/types";
import { EmptyState, Glass, Meter, TerminalLabel } from "../ui";

function brierMeterTone(brierScore: number | null) {
  return brierScore === null ? "cyan" : brierScore <= 0.15 ? "green" : brierScore <= 0.25 ? "amber" : "red";
}

/**
 * CEO directive "Professional Quant Trading Core," Phase B P2 item —
 * a real Brier-score calibration read over the Prediction Ledger
 * (backend/app/prediction_tracking.py::compute_brier_calibration()).
 * A standard proper scoring rule — never a fabricated "AI IQ" number —
 * plus the standard reliability-diagram bucket breakdown. Extended per
 * CEO directive "Professional Quant Portfolio Intelligence + Alpha
 * Research Engine," Phase 7 (Agent Calibration) with the same real
 * methodology broken out per real named agent, so an agent that states
 * high confidence but is repeatedly wrong is visible on its own row —
 * see backend/app/prediction_tracking.py::compute_agent_brier_calibration().
 */
export function BrierCalibrationCard() {
  const [summary, setSummary] = useState<BrierCalibrationSummary | null>(null);
  const [agentCalibrations, setAgentCalibrations] = useState<AgentBrierCalibration[] | null>(null);

  useEffect(() => {
    api.getBrierCalibration().then(setSummary).catch(() => undefined);
    api.getAgentBrierCalibration().then(setAgentCalibrations).catch(() => undefined);
  }, []);

  if (!summary) return null;

  const meterTone = brierMeterTone(summary.brierScore);
  const evaluableAgents = (agentCalibrations ?? []).filter((a) => a.calibration.evidenceState === "sufficient_evidence");

  return (
    <Glass className="p-3">
      <TerminalLabel>Brier-Score Calibration — real proper scoring rule</TerminalLabel>
      <div className="mb-1.5 mt-1 text-[9px] text-cmd-textDim">
        0.0 = perfect calibration, ~0.25 = a coin-flip forecaster, 1.0 = worst possible. Measures whether stated confidence tracks real outcomes.
      </div>

      {summary.evidenceState === "not_enough_data" ? (
        <EmptyState>{summary.summary}</EmptyState>
      ) : (
        <>
          <div className="mb-1 flex items-center justify-between text-[9px] text-cmd-textDim">
            <span>Brier Score ({summary.resolvedPredictionCount} real resolved predictions)</span>
            <span className="tabular-nums text-cmd-text">{summary.brierScore?.toFixed(3)}</span>
          </div>
          <Meter value={(1 - (summary.brierScore ?? 0)) * 100} tone={meterTone} />
          <div className="mt-2 text-[9px] text-cmd-textDim">{summary.summary}</div>

          {summary.buckets.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Reliability by Confidence Bucket</div>
              {summary.buckets.map((b) => (
                <div key={`${b.rangeLowPct}-${b.rangeHighPct}`} className="flex items-center justify-between gap-2 border-t border-cmd-border/40 pt-1 text-[9px]">
                  <span className="text-cmd-textDim">
                    {b.rangeLowPct.toFixed(0)}–{b.rangeHighPct.toFixed(0)}% stated ({b.predictedCount})
                  </span>
                  <span className="text-cmd-text">{b.realAccuracyPct === null ? "not enough data" : `${b.realAccuracyPct.toFixed(0)}% real accuracy`}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {evaluableAgents.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-cmd-border/40 pt-2">
          <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-textDim">Per-Agent Calibration</div>
          {evaluableAgents
            .slice()
            .sort((a, b) => (a.calibration.brierScore ?? 0) - (b.calibration.brierScore ?? 0))
            .map((a) => (
              <div key={a.agentId} className="text-[9px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-cmd-textDim">
                    {AGENT_PROFILES[a.agentId].name} ({a.calibration.resolvedPredictionCount})
                  </span>
                  <span className="tabular-nums text-cmd-text">{a.calibration.brierScore?.toFixed(3)}</span>
                </div>
                <Meter value={(1 - (a.calibration.brierScore ?? 0)) * 100} tone={brierMeterTone(a.calibration.brierScore)} />
              </div>
            ))}
        </div>
      )}
    </Glass>
  );
}
