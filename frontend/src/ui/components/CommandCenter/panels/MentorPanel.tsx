import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import { NexusManager } from "@/game/systems/NexusManager";
import { api } from "@/net/api";
import type { QuestionCategory, ThinkingProfile } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const CATEGORY_LABELS: Record<QuestionCategory, string> = {
  critical_thinking: "Critical Thinking",
  decision_making: "Decision Making",
  communication: "Communication",
  leadership: "Leadership",
  psychology: "Psychology",
  risk_awareness: "Risk Awareness",
  research: "Research",
  reflection: "Reflection",
  logic: "Logic",
  teamwork: "Teamwork",
};

/**
 * v0.7 Feature 32 — Sage, the Socratic Mentor. Every number here is real:
 * QuestionOfTheDay rotates deterministically through a small hand-authored
 * library (see backend/app/mentor.py's module docstring for why — no
 * free-form question generation exists in this codebase), the player's
 * response is stored verbatim and never graded, and ThinkingProfile traits
 * are purely computed from signals this codebase already tracks elsewhere
 * (Discipline Reviews, Reasoning Lab contributions, Reflection Chamber
 * insights, Academy points). No dedicated physical "Mentor Chamber" room
 * was built for this feature (see docs/Architecture.md's scope-cut note,
 * matching Academy/Discipline Chamber/Reasoning Lab/Reflection Chamber) —
 * this panel is the Mentor Chamber, and Sage's home location reuses the
 * Brain Room.
 */
export function MentorPanel() {
  const { questionArchive, thinkingProfiles, mentorState } = useGameStore();
  const [responseDraft, setResponseDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const today = questionArchive[questionArchive.length - 1];
  const archive = useMemo(() => [...questionArchive].reverse(), [questionArchive]);
  const profiles = useMemo(() => Object.values(thinkingProfiles) as ThinkingProfile[], [thinkingProfiles]);

  const submitResponse = async () => {
    if (!today || !responseDraft.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitQotdResponse(today.id, responseDraft.trim());
      NexusManager.setQuestionOfTheDayResponse(res.question);
      setResponseDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <Glass className="p-3 lg:col-span-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Question of the Day</TerminalLabel>
          <StatusPill tone="purple">{mentorState.tierLabel.toUpperCase()}</StatusPill>
        </div>
        {!today ? (
          <EmptyState>Sage publishes a new question every in-game morning at 8:00.</EmptyState>
        ) : (
          <>
            <div className="mb-1 flex items-center gap-2 text-[9px] text-cmd-textDim">
              <StatusPill tone="cyan">{CATEGORY_LABELS[today.category]}</StatusPill>
              <span>Day {today.simDay}</span>
            </div>
            <div className="mb-2 text-cmd-cyan">“{today.question}”</div>
            {today.relatedReference && <div className="mb-2 text-[9px] italic text-cmd-textDim">{today.relatedReference}</div>}
            {today.playerResponse ? (
              <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
                <TerminalLabel>Your Answer</TerminalLabel>
                <div className="text-cmd-text">{today.playerResponse}</div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <textarea
                  value={responseDraft}
                  onChange={(e) => setResponseDraft(e.target.value)}
                  placeholder="What do you think?"
                  rows={2}
                  className="w-full resize-none rounded-sm border border-cmd-border bg-cmd-bg/60 p-1.5 text-[9px] text-cmd-text placeholder:text-cmd-textDim focus:border-cmd-cyan/50 focus:outline-none"
                />
                <div className="flex items-center justify-between">
                  <span className="text-[9px] text-cmd-textDim">Never graded — Sage only ever asks.</span>
                  <button
                    type="button"
                    onClick={() => void submitResponse()}
                    disabled={!responseDraft.trim() || submitting}
                    className="flex-none rounded-sm border border-cmd-cyan/50 px-3 py-1 text-[10px] uppercase tracking-wider text-cmd-cyan shadow-cmd-cyan transition-colors hover:bg-cmd-cyan/10 disabled:opacity-40"
                  >
                    {submitting ? "Submitting…" : "Answer"}
                  </button>
                </div>
                {error && <div className="text-[9px] text-cmd-red">{error}</div>}
              </div>
            )}
          </>
        )}
        <p className="mt-2 border-t border-cmd-border/50 pt-2 text-[9px] text-cmd-textDim">
          {mentorState.questionsAsked} question{mentorState.questionsAsked === 1 ? "" : "s"} asked so far — {mentorState.tierLabel.toLowerCase()}.
        </p>
      </Glass>

      <Glass className="max-h-[28rem] overflow-y-auto p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Question Archive</TerminalLabel>
          <StatusPill tone="cyan">{questionArchive.length}</StatusPill>
        </div>
        {archive.length === 0 ? (
          <EmptyState>No questions archived yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {archive.map((question) => (
              <div key={question.id} className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
                <button type="button" onClick={() => setExpandedId(expandedId === question.id ? null : question.id)} className="flex w-full items-center justify-between gap-2 text-left">
                  <span className="flex items-center gap-1.5">
                    <StatusPill tone="cyan">{CATEGORY_LABELS[question.category]}</StatusPill>
                    <span className="text-cmd-textDim">Day {question.simDay}</span>
                  </span>
                  <span className="tabular-nums text-cmd-textDim">{question.playerResponse ? "answered" : ""}</span>
                </button>
                {expandedId === question.id && (
                  <div className="mt-1.5 space-y-1 border-t border-cmd-border/50 pt-1.5">
                    <div className="text-cmd-text">“{question.question}”</div>
                    {question.relatedReference && <div className="italic text-cmd-textDim">{question.relatedReference}</div>}
                    {question.playerResponse && <DataRow label="Your Answer" value={question.playerResponse} />}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Glass>

      <Glass className="p-3">
        <TerminalLabel>Question Library</TerminalLabel>
        <p className="text-[9px] text-cmd-textDim">
          Sage draws from a curated bank of questions spanning {Object.keys(CATEGORY_LABELS).length} categories — Critical Thinking, Decision Making, Communication, Leadership, Psychology, Risk Awareness, Research, Reflection, Logic, and Teamwork.
        </p>
      </Glass>

      <Glass className="p-3 lg:col-span-3">
        <TerminalLabel>Thinking Profiles</TerminalLabel>
        {profiles.length === 0 ? (
          <EmptyState>No profiles computed yet.</EmptyState>
        ) : (
          <div className="mt-1.5 grid grid-cols-1 gap-2 md:grid-cols-2">
            {profiles.map((profile) => (
              <ThinkingProfileCard key={profile.agentId} profile={profile} />
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function ThinkingProfileCard({ profile }: { profile: ThinkingProfile }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 text-[9px]">
      <div className="mb-1.5 text-cmd-cyan">{AGENT_PROFILES[profile.agentId].name}</div>
      <div className="space-y-1">
        {profile.traits.map((trait) => (
          <div key={trait.id}>
            <div className="flex items-center justify-between">
              <span className="text-cmd-text">{trait.name}</span>
              <span className="tabular-nums text-cmd-textDim">{trait.score.toFixed(0)}</span>
            </div>
            <Meter value={trait.score} tone={trait.score >= 70 ? "green" : trait.score >= 40 ? "amber" : "red"} />
          </div>
        ))}
      </div>
    </div>
  );
}
