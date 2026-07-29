import { useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { CaseStudy, CaseStudyCategory, DisciplineReview, DisciplineTier } from "@/types";
import { SUCCESS_CASE_STUDY_CATEGORIES } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

const TIER_TONE: Record<DisciplineTier, "green" | "cyan" | "amber" | "red"> = {
  exemplary: "green",
  sound: "cyan",
  adequate: "amber",
  weak: "amber",
  reckless: "red",
};

const CATEGORY_LABEL: Record<CaseStudyCategory, string> = {
  overconfidence: "The Cost of Overconfidence",
  incomplete_research: "Incomplete Research",
  unchallenged_assumptions: "Failure to Challenge Assumptions",
  acted_too_quickly: "Acting Too Quickly",
  ignored_dissent: "Poor Communication",
  confirmation_bias: "Confirmation Bias",
  // v0.7 Feature 42 — the Library of Successes half of the same case
  // study log (see backend/app/successes.py).
  disciplined_process: "A Well-Disciplined Process",
  rigorous_cross_examination: "Rigorous Cross-Examination",
  patient_execution: "Patient Execution",
};

/**
 * v0.7 Features 26/27 — the Discipline Chamber and the Library of
 * Mistakes. Every number and category here is real, computed server-side
 * from an actual closed trade's real process trail (see
 * backend/app/discipline.py / backend/app/mistakes.py's module
 * docstrings for exactly which real signal backs each factor/category).
 * `score`/`factors` never depend on the trade's pnl — the "good process,
 * bad outcome" and "weak process, lucky win" counts below exist
 * specifically to make that distinction visible to the player, the whole
 * pedagogical point of Feature 26.
 */
export function DisciplinePanel() {
  const { disciplineReviews, caseStudies } = useGameStore();
  const [expandedReviewId, setExpandedReviewId] = useState<string | null>(null);
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<CaseStudyCategory | null>(null);

  const recentReviews = useMemo(() => [...disciplineReviews].reverse(), [disciplineReviews]);
  const recentCaseStudies = useMemo(() => [...caseStudies].reverse().filter((c) => !categoryFilter || c.category === categoryFilter), [caseStudies, categoryFilter]);

  const stats = useMemo(() => {
    if (disciplineReviews.length === 0) return null;
    const avgScore = disciplineReviews.reduce((sum, r) => sum + r.score, 0) / disciplineReviews.length;
    const goodProcessBadOutcome = disciplineReviews.filter((r) => r.score >= 70 && r.outcome === "loss").length;
    const weakProcessGoodOutcome = disciplineReviews.filter((r) => r.score < 55 && r.outcome === "win").length;
    return { avgScore, goodProcessBadOutcome, weakProcessGoodOutcome };
  }, [disciplineReviews]);

  const categoryCounts = useMemo(() => {
    const counts = new Map<CaseStudyCategory, number>();
    for (const c of caseStudies) counts.set(c.category, (counts.get(c.category) ?? 0) + 1);
    return counts;
  }, [caseStudies]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Glass className="p-3 lg:col-span-2">
        <TerminalLabel>Discipline Chamber</TerminalLabel>
        {!stats ? (
          <EmptyState>No trades have closed yet — a Discipline Review is filed for every one, scoring the decision process, never the outcome.</EmptyState>
        ) : (
          <>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-cmd-cyan">{stats.avgScore.toFixed(0)}/100 average discipline score</span>
              <span className="text-[9px] text-cmd-textDim">{disciplineReviews.length} review(s) on record</span>
            </div>
            <Meter value={stats.avgScore} tone={stats.avgScore >= 70 ? "green" : stats.avgScore >= 55 ? "cyan" : "amber"} />
            <div className="mt-2 grid grid-cols-2 gap-2 text-[9px]">
              <div className="rounded-sm border border-cmd-green/40 bg-cmd-bg/40 p-1.5">
                <span className="text-cmd-green">{stats.goodProcessBadOutcome}</span> good-process trade(s) that still lost — bad luck, not a bad decision.
              </div>
              <div className="rounded-sm border border-cmd-amber/40 bg-cmd-bg/40 p-1.5">
                <span className="text-cmd-amber">{stats.weakProcessGoodOutcome}</span> weak-process trade(s) that happened to win — a warning, not a validation.
              </div>
            </div>
          </>
        )}
      </Glass>

      <Glass className="max-h-96 overflow-y-auto p-3">
        <TerminalLabel>Discipline Reviews</TerminalLabel>
        {recentReviews.length === 0 ? (
          <EmptyState>Nothing reviewed yet.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentReviews.map((review) => (
              <DisciplineReviewRow key={review.id} review={review} expanded={expandedReviewId === review.id} onToggle={() => setExpandedReviewId(expandedReviewId === review.id ? null : review.id)} />
            ))}
          </div>
        )}
      </Glass>

      <Glass className="max-h-96 overflow-y-auto p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Library of Mistakes &amp; Successes</TerminalLabel>
          <StatusPill tone="purple">{caseStudies.length} case stud{caseStudies.length === 1 ? "y" : "ies"}</StatusPill>
        </div>
        <div className="mb-2 flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setCategoryFilter(null)}
            className={`rounded-sm border px-1.5 py-0.5 text-[8px] uppercase tracking-wider ${categoryFilter === null ? "border-cmd-cyan/50 text-cmd-cyan" : "border-cmd-border text-cmd-textDim"}`}
          >
            All
          </button>
          {(Object.keys(CATEGORY_LABEL) as CaseStudyCategory[]).map((category) => {
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
        {recentCaseStudies.length === 0 ? (
          <EmptyState>No case studies filed yet — one is only ever filed for a real, specific process gap behind a loss, or a real process strength behind a win.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {recentCaseStudies.map((study) => (
              <CaseStudyRow key={study.id} study={study} expanded={expandedCaseId === study.id} onToggle={() => setExpandedCaseId(expandedCaseId === study.id ? null : study.id)} />
            ))}
          </div>
        )}
      </Glass>
    </div>
  );
}

function DisciplineReviewRow({ review, expanded, onToggle }: { review: DisciplineReview; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5">
          <span className="text-cmd-cyan">{review.symbol}</span>
          <StatusPill tone={TIER_TONE[review.tier]}>{review.tier}</StatusPill>
          <StatusPill tone={review.outcome === "win" ? "green" : "red"}>{review.outcome === "win" ? "WON" : "LOST"}</StatusPill>
        </span>
        <span className="tabular-nums text-cmd-textDim">{review.score.toFixed(0)}/100</span>
      </button>
      <div className="mt-1 text-cmd-textDim">{review.summary}</div>
      {expanded && (
        <div className="mt-2 space-y-2 border-t border-cmd-border/50 pt-2">
          <div>
            <TerminalLabel>Factors</TerminalLabel>
            <div className="space-y-1">
              {review.factors.map((factor) => (
                <div key={factor.id}>
                  <div className="flex items-center justify-between">
                    <span className="text-cmd-text">{factor.name}</span>
                    <span className="tabular-nums text-cmd-textDim">{factor.score.toFixed(0)}</span>
                  </div>
                  <Meter value={factor.score} tone={factor.score >= 70 ? "green" : factor.score >= 40 ? "amber" : "red"} />
                </div>
              ))}
            </div>
          </div>
          <PostDecisionList label="What we did well" items={review.postDecisionReview.whatWeDidWell} />
          <PostDecisionList label="Mistakes made" items={review.postDecisionReview.mistakesMade} />
          <PostDecisionList label="Assumptions that proved incorrect" items={review.postDecisionReview.assumptionsIncorrect} />
          <PostDecisionList label="How to improve" items={review.postDecisionReview.howToImprove} />
          {review.attendees.length > 0 && (
            <div className="text-[9px] text-cmd-textDim">Attending: {review.attendees.map((a) => AGENT_PROFILES[a].name).join(", ")}</div>
          )}
        </div>
      )}
    </div>
  );
}

function PostDecisionList({ label, items }: { label: string; items: string[] }) {
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

function CaseStudyRow({ study, expanded, onToggle }: { study: CaseStudy; expanded: boolean; onToggle: () => void }) {
  const isSuccess = SUCCESS_CASE_STUDY_CATEGORIES.has(study.category);
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5">
          <span className={isSuccess ? "text-cmd-green" : "text-cmd-purple"}>{study.title}</span>
          <span className="text-cmd-textDim">{study.symbol}</span>
        </span>
        <span className={`tabular-nums ${isSuccess ? "text-cmd-green" : "text-cmd-red"}`}>{study.tradePnlPct >= 0 ? "+" : ""}{study.tradePnlPct.toFixed(1)}%</span>
      </button>
      <div className="mt-1 text-cmd-textDim">{study.missedInformation}</div>
      {expanded && (
        <div className="mt-2 space-y-2 border-t border-cmd-border/50 pt-2">
          <div>
            <TerminalLabel>Timeline</TerminalLabel>
            {study.timeline.map((entry, i) => (
              <DataRow key={i} label={entry.label} value={new Date(entry.timestamp).toLocaleString()} />
            ))}
          </div>
          <div>
            <TerminalLabel>Background</TerminalLabel>
            <p className="text-cmd-textDim">{study.background}</p>
          </div>
          <div>
            <TerminalLabel>Decision Process</TerminalLabel>
            <p className="text-cmd-textDim">{study.decisionProcess}</p>
          </div>
          <div>
            <TerminalLabel>Department Opinions</TerminalLabel>
            <ul className="list-inside list-disc space-y-0.5 text-cmd-textDim">
              {study.departmentOpinions.map((opinion, i) => (
                <li key={i}>{opinion}</li>
              ))}
            </ul>
          </div>
          <div>
            <TerminalLabel>Lessons Learned</TerminalLabel>
            <p className="text-cmd-textDim">{study.lessonsLearned}</p>
          </div>
          <div>
            <TerminalLabel>Recommended Improvements</TerminalLabel>
            <p className="text-cmd-textDim">{study.recommendedImprovements}</p>
          </div>
          <div>
            <TerminalLabel>Related Company Principles</TerminalLabel>
            <ul className="list-inside list-disc space-y-0.5 text-cmd-textDim">
              {study.relatedPrinciples.map((principle, i) => (
                <li key={i}>{principle}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
