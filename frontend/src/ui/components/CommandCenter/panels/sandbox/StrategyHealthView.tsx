import { useEffect, useState } from "react";
import { api } from "@/net/api";
import type { Strategy, StrategyHealthAssessment, StrategyLiveVsBacktestRead } from "@/types";
import { strategyHealthTone } from "../../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

const LIVE_VS_BACKTEST_TONE: Record<StrategyLiveVsBacktestRead["verdict"], "green" | "amber" | "cyan"> = {
  consistent_with_backtest: "green",
  diverging_from_backtest: "amber",
  not_enough_live_data: "cyan",
  no_backtest_health_on_record: "cyan",
};

/**
 * v0.7 Feature 52 (Part 2) — "Live Performance Monitor," honestly
 * reframed. What IS real: a recent-vs-lifetime trend read over this
 * strategy's own Market Simulation run history, re-computed every time
 * a new run completes (see backend/app/strategy_lab.py's
 * compute_strategy_health()). Shown here as Strategy Health rather than
 * under a name that implies a live-trade-only stream.
 *
 * CEO directive "Live Trade → Strategy Provenance," Phase 5 — a real
 * live-vs-backtest comparison now sits alongside it: this docstring
 * used to say the codebase "has no mechanism to attribute an executed
 * trade back to a specific Strategy object" — true when Feature 52
 * shipped, false since that directive's Phase 2. The comparison below
 * is fetched fresh (never persisted, same CAGS convention as
 * everything else in this panel) and only ever compares winRatePct —
 * both real 0-100% scales; live avgPnlPct and backtest expectancyR are
 * deliberately never forced onto one number (different units).
 */
export function StrategyHealthView({ selected, healthAssessments }: { selected: Strategy; healthAssessments: StrategyHealthAssessment[] }) {
  const own = healthAssessments.filter((h) => h.strategyId === selected.id);
  const latest = own[own.length - 1] ?? null;

  const [liveVsBacktest, setLiveVsBacktest] = useState<StrategyLiveVsBacktestRead | null | undefined>(undefined);
  useEffect(() => {
    let cancelled = false;
    setLiveVsBacktest(undefined);
    api
      .getStrategyLiveVsBacktest()
      .then((summary) => {
        if (!cancelled) setLiveVsBacktest(summary.reads.find((r) => r.strategyId === selected.id) ?? null);
      })
      .catch(() => {
        if (!cancelled) setLiveVsBacktest(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selected.id]);

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Strategy Health — real simulation performance, not live P&L</TerminalLabel>
        <p className="text-[9px] text-cmd-textDim">
          This strategy&apos;s own recent Market Simulation runs compared against its full real lifetime history, re-read every time a new run completes.
        </p>
      </Glass>

      {liveVsBacktest && (
        <Glass className="p-3">
          <div className="mb-1 flex items-center justify-between">
            <TerminalLabel>Live vs. Backtest — does this strategy trade the way it tested?</TerminalLabel>
            <StatusPill tone={LIVE_VS_BACKTEST_TONE[liveVsBacktest.verdict]}>{liveVsBacktest.verdict.replace(/_/g, " ")}</StatusPill>
          </div>
          <div className="grid grid-cols-2 gap-x-4">
            <DataRow label={`Live Win Rate (${liveVsBacktest.liveTradeCount} real trade${liveVsBacktest.liveTradeCount === 1 ? "" : "s"})`} value={`${liveVsBacktest.liveWinRatePct.toFixed(0)}%`} />
            <DataRow
              label={liveVsBacktest.backtestRecentWinRatePct === null ? "Backtest Recent Win Rate" : `Backtest Recent Win Rate (${liveVsBacktest.backtestRecentSampleSize} runs)`}
              value={liveVsBacktest.backtestRecentWinRatePct === null ? "—" : `${liveVsBacktest.backtestRecentWinRatePct.toFixed(0)}%`}
            />
          </div>
          <p className="mt-1.5 text-[9px] text-cmd-textDim">{liveVsBacktest.detail}</p>
        </Glass>
      )}

      {!latest ? (
        <Glass className="p-3">
          <EmptyState>No completed Market Simulation runs yet — nothing real to read a trend from.</EmptyState>
        </Glass>
      ) : (
        <>
          <Glass className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>Current Read</TerminalLabel>
              <StatusPill tone={strategyHealthTone(latest.status)}>
                {latest.status.replace(/_/g, " ")} · {latest.trend}
              </StatusPill>
            </div>
            <div className="grid grid-cols-2 gap-x-4">
              <DataRow label={`Recent Win Rate (last ${latest.recentSampleSize})`} value={`${latest.recentWinRate.toFixed(0)}%`} />
              <DataRow label={`Lifetime Win Rate (${latest.lifetimeSampleSize} runs)`} value={`${latest.lifetimeWinRate.toFixed(0)}%`} />
              <DataRow
                label="Recent Avg Return"
                value={`${latest.recentAvgReturnPct >= 0 ? "+" : ""}${latest.recentAvgReturnPct.toFixed(1)}%`}
                valueClassName={latest.recentAvgReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}
              />
              <DataRow
                label="Lifetime Avg Return"
                value={`${latest.lifetimeAvgReturnPct >= 0 ? "+" : ""}${latest.lifetimeAvgReturnPct.toFixed(1)}%`}
                valueClassName={latest.lifetimeAvgReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}
              />
              <DataRow label="Recent Avg Drawdown" value={`${latest.recentAvgDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
              <DataRow label="Lifetime Avg Drawdown" value={`${latest.lifetimeAvgDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
            </div>
            <div className="mt-1.5 space-y-0.5 border-t border-cmd-border/50 pt-1.5">
              {latest.reasoning.map((r, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  · {r}
                </div>
              ))}
            </div>
          </Glass>

          {own.length > 1 && (
            <Glass className="p-3">
              <TerminalLabel>Health History — real assessment on every completed run</TerminalLabel>
              <div className="max-h-56 overflow-y-auto">
                <table className="w-full text-[9px]">
                  <thead>
                    <tr className="border-b border-cmd-border text-cmd-textDim">
                      <th className="px-1 py-1 text-left">Day</th>
                      <th className="px-1 py-1 text-left">Status</th>
                      <th className="px-1 py-1 text-left">Trend</th>
                      <th className="px-1 py-1 text-left">Recent Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...own].reverse().map((h, i) => (
                      // A strategy can complete more than one real
                      // Market Simulation run on the same sim day, and
                      // this assessment's own real id is only unique per
                      // (strategy, day) — not per completed run — so the
                      // array position disambiguates real same-day
                      // re-assessments rather than colliding React keys.
                      <tr key={`${h.id}-${i}`} className="border-b border-cmd-border/40">
                        <td className="px-1 py-1 tabular-nums text-cmd-cyan">{h.simDay}</td>
                        <td className="px-1 py-1">
                          <StatusPill tone={strategyHealthTone(h.status)}>{h.status.replace(/_/g, " ")}</StatusPill>
                        </td>
                        <td className="px-1 py-1 text-cmd-textDim">{h.trend}</td>
                        <td className={`px-1 py-1 tabular-nums ${h.recentAvgReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}`}>
                          {h.recentAvgReturnPct >= 0 ? "+" : ""}
                          {h.recentAvgReturnPct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Glass>
          )}
        </>
      )}
    </div>
  );
}
