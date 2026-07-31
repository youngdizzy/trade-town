import type { Strategy, StrategyHealthAssessment } from "@/types";
import { strategyHealthTone } from "../../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * v0.7 Feature 52 (Part 2) — "Live Performance Monitor," honestly
 * reframed. This codebase has no mechanism to attribute a live/paper
 * trade back to a specific Strategy object (see
 * backend/app/sandbox.py's module docstring) — there is no real live
 * P&L stream to monitor. What IS real: a recent-vs-lifetime trend read
 * over this strategy's own Market Simulation run history, re-computed
 * every time a new run completes (see
 * backend/app/strategy_lab.py's compute_strategy_health()). Shown here
 * as Strategy Health rather than under a name that implies live-trade
 * data this codebase doesn't have.
 */
export function StrategyHealthView({ selected, healthAssessments }: { selected: Strategy; healthAssessments: StrategyHealthAssessment[] }) {
  const own = healthAssessments.filter((h) => h.strategyId === selected.id);
  const latest = own[own.length - 1] ?? null;

  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Strategy Health — real simulation performance, not live P&L</TerminalLabel>
        <p className="text-[9px] text-cmd-textDim">
          This codebase's live/paper trading loop has no mechanism to attribute an executed trade back to a specific Strategy object — see the Pipeline tab's own note on Allocated
          Capital. What's shown here is real: this strategy's own recent Market Simulation runs compared against its full real lifetime history, re-read every time a new run
          completes.
        </p>
      </Glass>

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
