import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { RecoveryFactorRead } from "@/types";
import { formatMoney } from "../lib/derive";
import { DataRow, Glass, TerminalLabel } from "../ui";

/**
 * CEO directive "Professional Quant Trading Core," Phase B P2 item —
 * the Live Recovery Factor (backend/app/analytics.py::
 * compute_recovery_factor()). A real, standard quant ratio (net profit
 * / worst real peak-to-trough drawdown, both measured against today's
 * real live equity) — never a fabricated composite score.
 */
export function RecoveryFactorCard() {
  const [read, setRead] = useState<RecoveryFactorRead | null>(null);

  useEffect(() => {
    api.getRecoveryFactor().then(setRead).catch(() => undefined);
  }, []);

  if (!read) return null;

  return (
    <Glass className="p-3">
      <TerminalLabel>Live Recovery Factor — real net profit / real worst drawdown</TerminalLabel>
      <div className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
        <DataRow
          label="Net Profit"
          value={`${read.netProfitUsd >= 0 ? "+" : ""}${formatMoney(read.netProfitUsd)}`}
          valueClassName={read.netProfitUsd >= 0 ? "text-cmd-green" : "text-cmd-red"}
        />
        <DataRow label="Worst Real Drawdown" value={`${formatMoney(read.maxDrawdownUsd)} (${read.maxDrawdownPct.toFixed(1)}%)`} />
        <DataRow
          label="Recovery Factor"
          value={read.recoveryFactor === null ? "undefined" : `${read.recoveryFactor.toFixed(2)}x`}
          valueClassName={read.recoveryFactor === null ? undefined : read.recoveryFactor >= 2 ? "text-cmd-green" : read.recoveryFactor >= 0 ? "text-cmd-amber" : "text-cmd-red"}
        />
        <DataRow label="Live Equity" value={formatMoney(read.currentEquity)} />
      </div>
      <div className="mt-2 text-[9px] text-cmd-textDim">{read.summary}</div>
    </Glass>
  );
}
