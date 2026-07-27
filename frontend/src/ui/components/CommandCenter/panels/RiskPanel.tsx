import { useGameStore } from "@/ui/hooks/useGameStore";
import { RISK_LEVEL_LABEL, formatPct, riskLevel, riskTextClass } from "../lib/derive";
import { DataRow, EmptyState, Glass, RiskDot, TerminalLabel } from "../ui";

const RISK_BANNER = {
  green: "border-cmd-green/50 bg-cmd-green/5",
  yellow: "border-cmd-amber/50 bg-cmd-amber/5",
  red: "border-cmd-red/50 bg-cmd-red/5",
};

/**
 * Sentinel (position/drawdown limits) and Guardian (per-symbol
 * concentration) are the only two sources of RiskWarning in TradeTown's
 * backend — see risk_engine.py. A `warning`/`critical` severity from
 * either becomes a hard-reject vote that unconditionally blocks a trade
 * (decision.py's HARD_REJECT_CHOICES), so "RED" here always means the
 * system really is refusing new trades right now, not just a cosmetic
 * label.
 */
export function RiskPanel() {
  const { riskWarnings, riskLimits, paperPortfolio, companyScore } = useGameStore();
  const level = riskLevel(riskWarnings);

  const equity = paperPortfolio.cashBalance + paperPortfolio.positions.reduce((s, p) => s + p.quantity * p.currentPrice, 0);
  const largestPosition = [...paperPortfolio.positions].sort((a, b) => b.quantity * b.currentPrice - a.quantity * a.currentPrice)[0] ?? null;
  const largestPositionPct = largestPosition && equity ? ((largestPosition.quantity * largestPosition.currentPrice) / equity) * 100 : 0;

  return (
    <div className="space-y-3">
      <Glass className={`border p-4 ${RISK_BANNER[level]}`}>
        <div className="flex items-center gap-2">
          <RiskDot level={level} className="h-3 w-3" />
          <span className={`font-cmdmono text-xl tracking-wider ${riskTextClass(level)}`}>{RISK_LEVEL_LABEL[level]}</span>
        </div>
        <div className="mt-1 text-cmd-textDim">
          {level === "red" && "A hard-reject condition is active — new trade candidates are being blocked (see decision.py's veto rule)."}
          {level === "yellow" && "Elevated risk — one or more warnings are active, but nothing is currently blocking new trades."}
          {level === "green" && "No active risk warnings. Sentinel and Guardian have no open concerns."}
        </div>
      </Glass>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Glass className="p-3">
          <TerminalLabel>Open Positions</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">
            {paperPortfolio.positions.length} / {riskLimits.maxOpenPositions}
          </div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Largest Position</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{largestPosition ? `${largestPosition.symbol} — ${largestPositionPct.toFixed(1)}%` : "None"}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Limit {riskLimits.maxPositionPct}% per position</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Total P&amp;L</TerminalLabel>
          <div className={`font-cmdmono ${paperPortfolio.totalPnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>{formatPct(paperPortfolio.totalPnlPct)}</div>
          <div className="mt-0.5 text-[9px] text-cmd-textDim">Limit −{riskLimits.maxDrawdownPct}% max drawdown</div>
        </Glass>
        <Glass className="p-3">
          <TerminalLabel>Risk Management Score</TerminalLabel>
          <div className="font-cmdmono text-cmd-text">{Math.round(companyScore.riskManagement)}/100</div>
        </Glass>
      </div>

      <Glass className="p-3">
        <TerminalLabel>Configured Risk Limits</TerminalLabel>
        <DataRow label="Max position size" value={`${riskLimits.maxPositionPct}%`} />
        <DataRow label="Risk per trade" value={`${riskLimits.riskPerTradePct}%`} />
        <DataRow label="Max daily loss" value={`${riskLimits.maxDailyLossPct}%`} />
        <DataRow label="Max drawdown" value={`${riskLimits.maxDrawdownPct}%`} />
        <DataRow label="Max open positions" value={riskLimits.maxOpenPositions} />
        <DataRow label="Max per-symbol concentration" value={`${riskLimits.maxSectorConcentrationPct}%`} />
        <div className="mt-1.5 text-[9px] text-cmd-textDim">
          Concentration is measured per-symbol, not per real market sector — TradeTown doesn&apos;t track a sector taxonomy (see risk_engine.py).
        </div>
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Active Warnings ({riskWarnings.length})</TerminalLabel>
        {riskWarnings.length === 0 ? (
          <EmptyState>No active risk warnings.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {riskWarnings.map((w) => (
              <div key={w.id} className={`flex items-center justify-between gap-2 border-b border-cmd-border/60 py-1 last:border-0 ${w.severity === "critical" ? "text-cmd-red" : "text-cmd-amber"}`}>
                <span className="font-cmdmono">{w.symbol}</span>
                <span className="flex-1 text-left">{w.message}</span>
                <span className="text-[9px] uppercase">{w.severity}</span>
              </div>
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}
