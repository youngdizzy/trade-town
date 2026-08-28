import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { BrierCalibrationSummary } from "@/types";
import { EmptyState, Glass, Meter, TerminalLabel } from "../ui";

/**
 * CEO directive "Professional Quant Trading Core," Phase B P2 item —
 * a real Brier-score calibration read over the Prediction Ledger
 * (backend/app/prediction_tracking.py::compute_brier_calibration()).
 * A standard proper scoring rule — never a fabricated "AI IQ" number —
 * plus the standard reliability-diagram bucket breakdown.
 */
export function BrierCalibrationCard() {
  const [summary, setSummary] = useState<BrierCalibrationSummary | null>(null);

  useEffect(() => {
    api.getBrierCalibration().then(setSummary).catch(() => undefined);
  }, []);

  if (!summary) return null;

  const meterTone = summary.brierScore === null ? "cyan" : summary.brierScore <= 0.15 ? "green" : summary.brierScore <= 0.25 ? "amber" : "red";

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
    </Glass>
  );
}
