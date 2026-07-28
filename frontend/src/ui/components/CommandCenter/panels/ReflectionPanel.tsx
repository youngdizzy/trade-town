import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { ReflectionCadence, ReflectionSession, WisdomTier } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const TIER_TONE: Record<WisdomTier, "amber" | "cyan" | "green" | "purple"> = {
  young_company: "amber",
  developing_judgment: "cyan",
  institutional_memory: "cyan",
  seasoned_wisdom: "green",
  enduring_wisdom: "purple",
};

const TIER_MAX_SCORE = 100;

const CADENCE_TONE: Record<ReflectionCadence, "cyan" | "purple"> = {
  weekly: "cyan",
  monthly: "purple",
};

/**
 * v0.7 Feature 30 — the Reflection Chamber. Every number here is real:
 * wisdomState is recomputed only when a ReflectionSession is generated
 * (weekly/monthly — see backend/app/wisdom.py's module docstring for
 * why that's deliberate, not a shortcut), and never reads a trade's
 * pnl — Company Wisdom measures process, not profit. No new physical
 * room was built for this feature (see docs/Architecture.md's scope-cut
 * note) — this panel is the Reflection Chamber.
 */
export function ReflectionPanel() {
  const { reflectionSessions, wisdomState } = useGameStore();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const recentSessions = useMemo(() => [...reflectionSessions].reverse(), [reflectionSessions]);

  return (
    <div className="grid grid-cols-1 gap-3">
      <Glass className="p-3">
        <TerminalLabel>Company Wisdom</TerminalLabel>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-cmd-cyan">
            {wisdomState.score.toFixed(0)}/100 — {wisdomState.tierLabel.toUpperCase()}
          </span>
          <StatusPill tone={TIER_TONE[wisdomState.tier]}>{wisdomState.tier.replace(/_/g, " ")}</StatusPill>
        </div>
        <Meter value={(wisdomState.score / TIER_MAX_SCORE) * 100} tone={wisdomState.score >= 70 ? "green" : wisdomState.score >= 50 ? "cyan" : "amber"} />
        <p className="mt-2 text-[9px] text-cmd-textDim">
          Never a measure of profit — this score tracks whether the company learns from experience, shares knowledge, follows its own principles, and avoids repeating real mistakes. Deliberately one of the hardest scores in TradeTown to max.
        </p>
        {wisdomState.factors.length > 0 && (
          <div className="mt-3 space-y-1.5 border-t border-cmd-border/50 pt-2">
            {wisdomState.factors.map((factor) => (
              <div key={factor.id}>
                <div className="flex items-center justify-between">
                  <span className="text-cmd-text">{factor.name}</span>
                  <span className="tabular-nums text-cmd-textDim">{factor.score.toFixed(0)}</span>
                </div>
                <Meter value={factor.score} tone={factor.score >= 70 ? "green" : factor.score >= 40 ? "amber" : "red"} />
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-[32rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Reflection Journal</TerminalLabel>
          <StatusPill tone="purple">
            {reflectionSessions.length} session{reflectionSessions.length === 1 ? "" : "s"}
          </StatusPill>
        </div>
        {recentSessions.length === 0 ? (
          <EmptyState>No Reflection Session yet — the company holds one automatically every in-game week and month.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentSessions.map((session) => (
              <ReflectionSessionRow key={session.id} session={session} expanded={expandedId === session.id} onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)} />
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function ReflectionSessionRow({ session, expanded, onToggle }: { session: ReflectionSession; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5">
          <StatusPill tone={CADENCE_TONE[session.cadence]}>{session.cadence}</StatusPill>
          <span className="text-cmd-textDim">Day {session.simDay}</span>
        </span>
        <span className="tabular-nums text-cmd-cyan">Wisdom {session.wisdomScore.toFixed(0)}/100</span>
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 border-t border-cmd-border/50 pt-2">
          <div>
            <TerminalLabel>Questions Discussed</TerminalLabel>
            <div className="space-y-1.5">
              {session.questions.map((q, i) => (
                <div key={i}>
                  <div className="text-cmd-text">{q.question}</div>
                  <div className="text-cmd-textDim">{q.answer}</div>
                </div>
              ))}
            </div>
          </div>
          {session.insights.length > 0 && (
            <div>
              <TerminalLabel>Department Insights</TerminalLabel>
              <ul className="list-inside list-disc space-y-0.5 text-cmd-textDim">
                {session.insights.map((insight, i) => (
                  <li key={i}>
                    <span className="text-cmd-text">{AGENT_PROFILES[insight.agentId].name}:</span> {insight.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <TextList label="Key Discoveries" items={session.keyDiscoveries} />
          <TextList label="Lessons Learned" items={session.lessonsLearned} />
          <TextList label="Important Questions" items={session.importantQuestions} />
          <TextList label="Recommended Future Projects" items={session.recommendedFutureProjects} />
          <DataRow label="Attendees" value={`${session.attendees.length} department(s)`} />
        </div>
      )}
    </div>
  );
}

function TextList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <TerminalLabel>{label}</TerminalLabel>
      <ul className="list-inside list-disc space-y-0.5 text-cmd-textDim">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
