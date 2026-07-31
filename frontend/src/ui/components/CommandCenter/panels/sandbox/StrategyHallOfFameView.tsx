import type { StrategyHallOfFameEntry } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * v0.7 Feature 52 (Part 2) — the Strategy Hall of Fame. Permanent, never
 * evicted — only ever filed for a strategy that cleared a real, strict
 * induction bar (≥30 aggregated trades, ≥55% win rate, ≥1.5 profit
 * factor, ≤20% average drawdown, and a real approved Founder Approval)
 * at the moment of its own real retirement. See
 * backend/app/strategy_lab.py's generate_strategy_retirement_outcome().
 */
export function StrategyHallOfFameView({ entries }: { entries: StrategyHallOfFameEntry[] }) {
  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Strategy Hall of Fame — permanent, only ever earned through real evidence</TerminalLabel>
        <p className="text-[9px] text-cmd-textDim">
          A real, strict bar checked only at the moment of a strategy's own retirement: ≥30 aggregated real trades, ≥55% win rate, ≥1.5 profit factor, ≤20% average drawdown, and a
          real approved Founder Approval on file.
        </p>
      </Glass>

      {entries.length === 0 ? (
        <Glass className="p-3">
          <EmptyState>No strategy has earned real induction yet.</EmptyState>
        </Glass>
      ) : (
        [...entries].reverse().map((e) => (
          <Glass key={e.id} className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>
                {e.strategyName} <span className="text-cmd-textDim">— by {AGENT_PROFILES[e.createdBy].name}</span>
              </TerminalLabel>
              <StatusPill tone="green">INDUCTED DAY {e.simDay}</StatusPill>
            </div>
            <p className="mb-2 text-[9px] text-cmd-text">{e.description}</p>
            <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
              <DataRow label="Real Days Active" value={e.simDaysActive} />
              <DataRow label="Real Trades Executed" value={e.tradesExecuted} />
              <DataRow label="Real Win Rate" value={`${e.winRate.toFixed(0)}%`} />
              <DataRow label="Real Profit Factor" value={e.profitFactor.toFixed(2)} />
              <DataRow label="Real Max Drawdown" value={`${e.maxDrawdownPct.toFixed(1)}%`} valueClassName="text-cmd-amber" />
              <DataRow
                label="Real Historical Return"
                value={`${e.historicalReturnPct >= 0 ? "+" : ""}${e.historicalReturnPct.toFixed(1)}%`}
                valueClassName={e.historicalReturnPct >= 0 ? "text-cmd-green" : "text-cmd-red"}
              />
            </div>
            <div className="mt-1.5 space-y-0.5 border-t border-cmd-border/50 pt-1.5">
              {e.legacyNotes.map((n, i) => (
                <div key={i} className="text-[9px] text-cmd-text">
                  · {n}
                </div>
              ))}
            </div>
            <DataRow label="Retirement Reason" value={e.retiredReason} />
          </Glass>
        ))
      )}
    </div>
  );
}
