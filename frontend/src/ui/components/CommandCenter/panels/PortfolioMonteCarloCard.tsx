import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { PortfolioMonteCarloResult } from "@/types";
import { DataRow, EmptyState, Glass, Meter, TerminalLabel } from "../ui";

/**
 * CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
 * final follow-up — backend/app/portfolio_monte_carlo.py. A real
 * HISTORICAL bootstrap over this account's own closed trade history
 * (never the strategy-level bootstrap's synthetic win/loss model) — see
 * that module's own docstring. Read-only analysis, no automatic action.
 */
export function PortfolioMonteCarloCard() {
  const [result, setResult] = useState<PortfolioMonteCarloResult | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .getPortfolioMonteCarlo()
        .then((res) => {
          if (!cancelled) {
            setResult(res);
            setLoaded(true);
          }
        })
        .catch(() => undefined);
    load();
    const interval = setInterval(load, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!loaded) return null;

  const ruinTone = result && result.probabilityOfRuinPct >= 25 ? "red" : result && result.probabilityOfRuinPct >= 10 ? "amber" : "cyan";

  return (
    <Glass className="p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <TerminalLabel>Portfolio Monte Carlo — real historical bootstrap</TerminalLabel>
        {result && <span className="text-[8px] uppercase tracking-wide text-cmd-textDim">{result.sourceTradeCount} real trades sampled</span>}
      </div>

      {!result && (
        <EmptyState>Not enough real closed trades yet to bootstrap a portfolio-level Monte Carlo — this needs a real trading track record first.</EmptyState>
      )}

      {result && (
        <>
          <div className="text-[9px] text-cmd-textDim">
            Resamples this account&apos;s own real trade outcomes {result.pathsSimulated} times over {result.tradesPerPath}-trade paths — never a
            synthetic win/loss model.
          </div>

          <div className="mt-2">
            <div className="mb-0.5 flex items-center justify-between text-[9px] text-cmd-textDim">
              <span>Probability of Ruin (breaching your own {result.ruinThresholdPct.toFixed(0)}% drawdown limit)</span>
              <span className="tabular-nums text-cmd-text">{result.probabilityOfRuinPct.toFixed(1)}%</span>
            </div>
            <Meter value={result.probabilityOfRuinPct} tone={ruinTone} />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
            <DataRow label="Capital Survival" value={`${result.capitalSurvivalPct.toFixed(1)}%`} />
            <DataRow label="Probability of Profit" value={`${result.probabilityOfProfitPct.toFixed(1)}%`} />
            <DataRow label="Source Win Rate" value={`${result.sourceWinRatePct.toFixed(1)}%`} />
            <DataRow label="Starting Equity" value={`$${result.startingEquity.toLocaleString()}`} />
            <DataRow
              label="Median Return"
              value={`${result.medianReturnPct >= 0 ? "+" : ""}${result.medianReturnPct.toFixed(2)}%`}
              valueClassName={result.medianReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}
            />
            <DataRow label="Return Range (10th–90th)" value={`${result.returnRangeLowPct.toFixed(2)}% / ${result.returnRangeHighPct.toFixed(2)}%`} />
            <DataRow label="Median Max Drawdown" value={`${result.medianMaxDrawdownPct.toFixed(2)}%`} />
            <DataRow label="Worst-Case Drawdown (5th pct.)" value={`${result.worstCaseDrawdownPct.toFixed(2)}%`} />
            <DataRow label="Value at Risk (95%)" value={`${result.valueAtRisk95Pct.toFixed(2)}%`} />
            <DataRow label="Value at Risk (99%)" value={`${result.valueAtRisk99Pct.toFixed(2)}%`} />
            <DataRow label="Conditional VaR (95%)" value={`${result.conditionalValueAtRisk95Pct.toFixed(2)}%`} />
            <DataRow label="Conditional VaR (99%)" value={`${result.conditionalValueAtRisk99Pct.toFixed(2)}%`} />
          </div>
        </>
      )}
    </Glass>
  );
}
