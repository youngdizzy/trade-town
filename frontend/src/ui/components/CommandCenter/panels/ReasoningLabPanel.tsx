import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { ReasoningChallenge, ReasoningChallengeCategory } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const REASONING_MAX_LEVEL = 3;

const CATEGORY_LABEL: Record<ReasoningChallengeCategory, string> = {
  finding_missing_information: "Finding Missing Information",
  identifying_weak_evidence: "Identifying Weak Evidence",
  recognizing_contradictory_data: "Recognizing Contradictory Data",
  separating_facts_from_assumptions: "Separating Facts from Assumptions",
  evaluating_multiple_hypotheses: "Evaluating Multiple Hypotheses",
  comparing_competing_explanations: "Comparing Competing Explanations",
  improving_communication: "Improving Communication",
};

const STANCE_TONE: Record<string, "cyan" | "amber" | "green"> = {
  opening: "cyan",
  challenge: "amber",
  support: "green",
};

/**
 * v0.7 Feature 29 — the Reasoning Lab. Every challenge here is filed
 * server-side from a real, already-existing AI Debate + its linked
 * TradeDecision (see backend/app/reasoning_lab.py's module docstring for
 * exactly which real signal backs each of the seven categories). No pnl
 * or trade outcome is ever read to produce a challenge or its category —
 * this practices the reasoning process itself, the same "process, not
 * outcome" guarantee the Discipline Chamber established.
 */
export function ReasoningLabPanel() {
  const { reasoningChallenges, reasoningLabState } = useGameStore();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<ReasoningChallengeCategory | null>(null);

  const recentChallenges = useMemo(
    () => [...reasoningChallenges].reverse().filter((c) => !categoryFilter || c.category === categoryFilter),
    [reasoningChallenges, categoryFilter],
  );

  const categoryCounts = useMemo(() => {
    const counts = new Map<ReasoningChallengeCategory, number>();
    for (const c of reasoningChallenges) counts.set(c.category, (counts.get(c.category) ?? 0) + 1);
    return counts;
  }, [reasoningChallenges]);

  return (
    <div className="grid grid-cols-1 gap-3">
      <Glass className="p-3">
        <TerminalLabel>Reasoning Lab</TerminalLabel>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-cmd-cyan">
            LEVEL {reasoningLabState.level} — {reasoningLabState.levelLabel.toUpperCase()}
          </span>
          <span className="text-[9px] text-cmd-textDim">{reasoningLabState.completedChallengeCount} challenge(s) completed</span>
        </div>
        <Meter value={(reasoningLabState.level / REASONING_MAX_LEVEL) * 100} tone="cyan" />
        <p className="mt-2 text-[9px] text-cmd-textDim">
          Higher levels unlock harder challenge categories from real AI Debates — never new pnl, only more of what the desk gets asked to reason through.
        </p>
      </Glass>

      <Glass className="max-h-[28rem] overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Reasoning History</TerminalLabel>
          <StatusPill tone="purple">
            {reasoningChallenges.length} challenge{reasoningChallenges.length === 1 ? "" : "s"}
          </StatusPill>
        </div>
        {reasoningChallenges.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            <button
              type="button"
              onClick={() => setCategoryFilter(null)}
              className={`rounded-sm border px-1.5 py-0.5 text-[8px] uppercase tracking-wider ${categoryFilter === null ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
            >
              All
            </button>
            {(Object.keys(CATEGORY_LABEL) as ReasoningChallengeCategory[]).map((category) => {
              const count = categoryCounts.get(category) ?? 0;
              if (count === 0) return null;
              return (
                <button
                  key={category}
                  type="button"
                  onClick={() => setCategoryFilter(categoryFilter === category ? null : category)}
                  className={`rounded-sm border px-1.5 py-0.5 text-[8px] uppercase tracking-wider ${categoryFilter === category ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
                >
                  {CATEGORY_LABEL[category]} ({count})
                </button>
              );
            })}
          </div>
        )}
        {recentChallenges.length === 0 ? (
          <EmptyState>No reasoning challenges filed yet — one is generated periodically from the company's most recent real AI Debate.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentChallenges.map((challenge) => (
              <ReasoningChallengeRow key={challenge.id} challenge={challenge} expanded={expandedId === challenge.id} onToggle={() => setExpandedId(expandedId === challenge.id ? null : challenge.id)} />
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function ReasoningChallengeRow({ challenge, expanded, onToggle }: { challenge: ReasoningChallenge; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5">
          <span className="text-cmd-purple">{CATEGORY_LABEL[challenge.category]}</span>
          <span className="text-cmd-textDim">{challenge.symbol}</span>
        </span>
        <StatusPill tone="cyan">Level {challenge.reasoningLevel}</StatusPill>
      </button>
      <div className="mt-1 text-cmd-textDim">{challenge.solution.whyReasonable}</div>
      {expanded && (
        <div className="mt-2 space-y-2 border-t border-cmd-border/50 pt-2">
          {challenge.contributions.length > 0 && (
            <div>
              <TerminalLabel>Collaborative Thinking</TerminalLabel>
              <div className="space-y-1">
                {challenge.contributions.map((c, i) => (
                  <div key={i} className="flex items-start gap-1.5">
                    <StatusPill tone={STANCE_TONE[c.stance] ?? "cyan"}>{c.stance}</StatusPill>
                    <span className="text-cmd-text">{AGENT_PROFILES[c.agentId].name}:</span>
                    <span className="text-cmd-textDim">{c.contribution}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div>
            <TerminalLabel>Explain Your Thinking</TerminalLabel>
            <SolutionList label="What we know" items={challenge.solution.whatWeKnow} />
            <SolutionList label="What we do not know" items={challenge.solution.whatWeDoNotKnow} />
            <SolutionList label="Assumptions" items={challenge.solution.assumptions} />
            <DataRow label="Why this is reasonable" value={challenge.solution.whyReasonable} />
            <DataRow label="Confidence" value={`${challenge.solution.confidence.toFixed(0)}/100`} />
            <DataRow label="What could change our conclusion" value={challenge.solution.whatCouldChangeOurConclusion} />
          </div>
        </div>
      )}
    </div>
  );
}

function SolutionList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mb-1">
      <span className="text-cmd-text">{label}:</span>
      <ul className="list-inside list-disc space-y-0.5 text-cmd-textDim">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
