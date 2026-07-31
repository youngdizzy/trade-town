import type { FailedStrategyArchiveEntry } from "@/types";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { STAGE_LABELS } from "../../lib/derive";
import { DataRow, EmptyState, Glass, StatusPill, TerminalLabel } from "../../ui";

/**
 * v0.7 Feature 52 (Part 2) — the Failed Strategy Archive. Every real
 * retirement that didn't clear the Hall of Fame bar — never deleted,
 * always kept as a real, citable lesson. "What failed" and "lessons
 * learned" are pulled from that strategy's own real StrategyReview
 * verdicts and StrategyExecutiveReview concerns, never invented after
 * the fact — see backend/app/strategy_lab.py's
 * generate_strategy_retirement_outcome().
 */
export function StrategyFailedArchiveView({ entries }: { entries: FailedStrategyArchiveEntry[] }) {
  return (
    <div className="space-y-3">
      <Glass className="p-3">
        <TerminalLabel>Failed Strategy Archive — every real lesson, permanently kept</TerminalLabel>
        <p className="text-[9px] text-cmd-textDim">
          Every retirement that didn't clear the Hall of Fame's real bar. "What failed" and "lessons learned" are pulled from this strategy's own real reviewer verdicts and
          department concerns — never invented after the fact.
        </p>
      </Glass>

      {entries.length === 0 ? (
        <Glass className="p-3">
          <EmptyState>No strategy has been retired without earning Hall of Fame induction yet.</EmptyState>
        </Glass>
      ) : (
        [...entries].reverse().map((e) => (
          <Glass key={e.id} className="p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <TerminalLabel>
                {e.strategyName} <span className="text-cmd-textDim">— by {AGENT_PROFILES[e.createdBy].name}</span>
              </TerminalLabel>
              <StatusPill tone="amber">RETIRED DAY {e.simDay}</StatusPill>
            </div>
            <DataRow label="Failed At Stage" value={STAGE_LABELS[e.failedAtStage]} />
            <DataRow label="Retirement Reason" value={e.retiredReason} />
            <div className="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-amber">What Failed</div>
                {e.whatFailed.map((w, i) => (
                  <div key={i} className="text-[9px] text-cmd-text">
                    · {w}
                  </div>
                ))}
              </div>
              <div>
                <div className="mb-1 text-[9px] uppercase tracking-wide text-cmd-cyan">Lessons Learned</div>
                {e.lessonsLearned.map((l, i) => (
                  <div key={i} className="text-[9px] text-cmd-text">
                    · {l}
                  </div>
                ))}
              </div>
            </div>
          </Glass>
        ))
      )}
    </div>
  );
}
