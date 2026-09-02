import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { RiskContract, RiskDecision } from "@/types";
import { DataRow, Glass, StatusPill, TerminalLabel } from "../ui";

/**
 * CEO directive "TradeTown — Persisted Risk Contract + Dynamic Risk
 * Scaling." Shows the authoritative, versioned RiskContract that
 * currently governs trading (backend/app/risk_contract.py) — a real
 * snapshot of the CEO's own configured Risk Limits above, plus its
 * dynamic scaling ladders and the most recent real, per-decision
 * scaling reads that ladder produced (Scaling Transparency).
 *
 * Deliberately read-only for this pass — drafting/validating/activating
 * a revised contract is a real, separate write flow (see
 * app/routers/risk.py's risk_contracts_router) not yet exposed here;
 * every value below is the CEO's own already-configured limits/ladder,
 * never a second, independent risk config.
 */
export function RiskContractCard() {
  const [contract, setContract] = useState<RiskContract | null>(null);
  const [decisions, setDecisions] = useState<RiskDecision[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getActiveRiskContract()
      .then(setContract)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    api
      .getRiskDecisions(5)
      .then((res) => setDecisions(res.decisions))
      .catch(() => undefined);
  }, []);

  if (error) {
    return (
      <Glass className="p-3">
        <TerminalLabel>Risk Contract</TerminalLabel>
        <div className="mt-1 text-cmd-red">{error}</div>
      </Glass>
    );
  }
  if (!contract) return null;

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Risk Contract — v{contract.version}</TerminalLabel>
        <StatusPill tone="green">{contract.status.toUpperCase()}</StatusPill>
      </div>
      <div className="text-[9px] text-cmd-textDim">{contract.detail}</div>

      <div className="mt-2 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
        <DataRow label="Risk per trade ceiling" value={`${contract.limits.riskPerTradePct}%`} />
        <DataRow label="Max position ceiling" value={`${contract.limits.maxPositionPct}%`} />
        <DataRow label="Created by" value={contract.createdBy} />
        <DataRow label="Reason" value={contract.reason} />
      </div>

      <div className="mt-3 border-t border-cmd-border/50 pt-2">
        <TerminalLabel>Dynamic Scaling Ladders — downward-only, never increases size to recover losses</TerminalLabel>
        <div className="mt-1.5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Drawdown {contract.scalingPolicy.drawdownScalingEnabled ? "" : "(disabled)"}</div>
            {contract.scalingPolicy.drawdownBands.map((band) => (
              <div key={band.label} className="flex items-center justify-between text-[9px] text-cmd-text">
                <span>
                  ≥{band.threshold}% dd — {band.label.replaceAll("_", " ")}
                </span>
                <span className="font-cmdmono text-cmd-textDim">×{band.factor}</span>
              </div>
            ))}
          </div>
          <div>
            <div className="text-[9px] uppercase tracking-wide text-cmd-textDim">Losing Streak {contract.scalingPolicy.losingStreakScalingEnabled ? "" : "(disabled)"}</div>
            {contract.scalingPolicy.losingStreakBands.map((band) => (
              <div key={band.label} className="flex items-center justify-between text-[9px] text-cmd-text">
                <span>
                  ≥{band.threshold} losses — {band.label.replaceAll("_", " ")}
                </span>
                <span className="font-cmdmono text-cmd-textDim">×{band.factor}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {decisions.length > 0 && (
        <div className="mt-3 border-t border-cmd-border/50 pt-2">
          <TerminalLabel>Recent Risk Decisions (Scaling Transparency)</TerminalLabel>
          <div className="mt-1.5 space-y-1">
            {[...decisions].reverse().map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-2 border-b border-cmd-border/40 py-1 text-[9px] last:border-0">
                <span className="font-cmdmono text-cmd-text">{d.symbol}</span>
                <span className="flex-1 text-cmd-textDim">
                  {d.requestedQuantity.toFixed(4)} req → {d.approvedQuantity.toFixed(4)} approved (×{d.scaling.combinedFactor.toFixed(3)})
                </span>
                {d.rejected ? <span className="text-cmd-red">REJECTED</span> : <span className="text-cmd-green">FILLED</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Glass>
  );
}
