import type { FailedStrategyArchiveEntry, Strategy, StrategyHallOfFameEntry } from "@/types";
import { STAGE_LABELS } from "../../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * v0.7 Feature 52 (Part 2) — "Strategy Evolution," honestly reframed.
 * This codebase has no strategy revision/versioning mechanism (no
 * v1.0→v1.1→v2.0 parent/child links, no re-run-the-whole-pipeline-on-
 * change) — see docs/Architecture.md's Part 2 section for why that's a
 * real structural addition deferred to a follow-up pass, not built here
 * to avoid faking a "v2.3 vs v2.4" comparison this codebase can't back.
 * What IS real and shown here: this strategy's own real stage_history —
 * every stage it has actually earned, in order, each backed by a real
 * signal — and, for a retired strategy, its one real permanent outcome.
 */
export function StrategyEvolutionView({
  selected,
  hallOfFameEntry,
  failedArchiveEntry,
}: {
  selected: Strategy;
  hallOfFameEntry: StrategyHallOfFameEntry | null;
  failedArchiveEntry: FailedStrategyArchiveEntry | null;
}) {
  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Real Journey — every stage this strategy has actually earned</TerminalLabel>
        <p className="mb-2 text-[9px] text-cmd-textDim">
          No fabricated version history: this codebase has no strategy revision mechanism (see docs/Architecture.md). What's real is this strategy's own stage-by-stage transition
          log, each one backed by a real signal.
        </p>
        {selected.stageHistory.length === 0 ? (
          <EmptyState>No real stage transitions on file yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {selected.stageHistory.map((event, i) => (
              <div key={event.id} className="flex gap-2 border-b border-cmd-border/40 pb-1.5 text-[9px] last:border-0">
                <span className="text-cmd-cyan">{i + 1}.</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <StatusPill tone={event.stage === "retired" ? "neutral" : event.stage === "approved" ? "green" : "cyan"}>{STAGE_LABELS[event.stage]}</StatusPill>
                    <span className="text-cmd-textDim">Day {event.simDay}</span>
                  </div>
                  <div className="mt-0.5 text-cmd-text">{event.detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Glass>

      {selected.stage === "retired" && (
        <Glass className="p-3">
          <TerminalLabel>Real Retirement Outcome</TerminalLabel>
          {hallOfFameEntry && (
            <div>
              <StatusPill tone="green">INDUCTED — STRATEGY HALL OF FAME</StatusPill>
              <div className="mt-1.5 space-y-1">
                <DataRow label="Real Trades Executed" value={hallOfFameEntry.tradesExecuted} />
                <DataRow label="Real Win Rate" value={`${hallOfFameEntry.winRate.toFixed(0)}%`} />
                <DataRow label="Real Historical Return" value={`${hallOfFameEntry.historicalReturnPct >= 0 ? "+" : ""}${hallOfFameEntry.historicalReturnPct.toFixed(1)}%`} />
                {hallOfFameEntry.legacyNotes.map((n, i) => (
                  <div key={i} className="text-[9px] text-cmd-text">
                    · {n}
                  </div>
                ))}
              </div>
            </div>
          )}
          {failedArchiveEntry && (
            <div>
              <StatusPill tone="amber">FILED — FAILED STRATEGY ARCHIVE</StatusPill>
              <div className="mt-1.5 space-y-1">
                <DataRow label="Failed At Stage" value={STAGE_LABELS[failedArchiveEntry.failedAtStage]} />
                <div className="mt-1 text-[9px] uppercase tracking-wide text-cmd-amber">What Failed</div>
                {failedArchiveEntry.whatFailed.map((w, i) => (
                  <div key={i} className="text-[9px] text-cmd-text">
                    · {w}
                  </div>
                ))}
                <div className="mt-1 text-[9px] uppercase tracking-wide text-cmd-amber">Lessons Learned</div>
                {failedArchiveEntry.lessonsLearned.map((l, i) => (
                  <div key={i} className="text-[9px] text-cmd-text">
                    · {l}
                  </div>
                ))}
              </div>
            </div>
          )}
          {!hallOfFameEntry && !failedArchiveEntry && <EmptyState>Retirement outcome not yet loaded — reopen this strategy from the Pipeline tab.</EmptyState>}
        </Glass>
      )}
    </div>
  );
}
