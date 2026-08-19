import { useEffect, useMemo, useState } from "react";
import { useGameStore } from "@/ui/hooks/useGameStore";
import { api } from "@/net/api";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { CaseStudy, CaseStudyCategory, DisciplineReview, DisciplineTier, ExitEfficiencyState, ExitEfficiencySummary, FailureClassification, FailureReason, TradeExitEfficiency } from "@/types";
import { SUCCESS_CASE_STUDY_CATEGORIES } from "@/types";
import { DataRow, EmptyState, Glass, Meter, StatusPill, TerminalLabel } from "../ui";

function exitEfficiencyTone(state: ExitEfficiencyState): "green" | "red" | "amber" | "cyan" {
  switch (state) {
    case "efficient_exit":
      return "green";
    case "poor_exit":
      return "red";
    case "average_exit":
      return "amber";
    case "not_enough_data":
      return "cyan";
  }
}

const EXIT_EFFICIENCY_LABEL: Record<ExitEfficiencyState, string> = {
  efficient_exit: "Efficient Exit",
  average_exit: "Average Exit",
  poor_exit: "Poor Exit",
  not_enough_data: "Not Enough Data",
};

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

// CEO directive "Features 26-30," Feature 30 — the Failure Review
// Board (backend/app/failure_review.py). A genuinely different
// question than CATEGORY_LABEL above: that taxonomy names the
// behavioral/process mistake; this one names why the THESIS actually
// failed. "external_shock" was researched and explicitly cut backend-
// side (no per-trade-linkable Black Swan record exists) so it never
// appears here either.
const FAILURE_REASON_LABEL: Record<FailureReason, string> = {
  bad_thesis: "Bad Thesis",
  poor_execution: "Poor Execution",
  risk_management_failure: "Risk Management Failure",
  market_regime_misread: "Market Regime Misread",
  information_gap: "Information Gap",
  process_violation: "Process Violation",
  unknown: "Unknown",
};

const FAILURE_REASON_TONE: Record<FailureReason, "green" | "cyan" | "amber" | "red" | "purple"> = {
  bad_thesis: "purple",
  poor_execution: "amber",
  risk_management_failure: "red",
  market_regime_misread: "cyan",
  information_gap: "amber",
  process_violation: "red",
  unknown: "cyan",
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
  const { disciplineReviews, caseStudies, failureClassifications } = useGameStore();
  const [expandedReviewId, setExpandedReviewId] = useState<string | null>(null);
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<CaseStudyCategory | null>(null);
  const [expandedFailureId, setExpandedFailureId] = useState<string | null>(null);

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

  const recentFailures = useMemo(() => [...failureClassifications].reverse(), [failureClassifications]);
  const failureReasonCounts = useMemo(() => {
    const counts = new Map<FailureReason, number>();
    for (const f of failureClassifications) counts.set(f.reason, (counts.get(f.reason) ?? 0) + 1);
    return counts;
  }, [failureClassifications]);

  // CEO directive "Professional Trading Firm Transformation" — real,
  // on-demand Exit Efficiency (backend/app/exit_efficiency.py), no WS-
  // broadcast field backs it, the same on-demand pattern this Command
  // Center already uses elsewhere.
  const [exitEfficiency, setExitEfficiency] = useState<ExitEfficiencySummary | null>(null);
  useEffect(() => {
    api.getExitEfficiency().then(setExitEfficiency).catch(() => undefined);
  }, []);
  const recentExitReads = useMemo(() => (exitEfficiency ? [...exitEfficiency.reads].reverse() : []), [exitEfficiency]);

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

      <Glass className="max-h-96 overflow-y-auto p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Failure Review Board</TerminalLabel>
          <StatusPill tone="purple">{failureClassifications.length} classification{failureClassifications.length === 1 ? "" : "s"}</StatusPill>
        </div>
        {failureClassifications.length === 0 ? (
          <EmptyState>No losing trade has closed yet — the Failure Review Board files one real, evidence-backed classification of WHY the thesis failed for every real closed loss (distinct from the behavioral mistakes above).</EmptyState>
        ) : (
          <>
            <div className="mb-2 flex flex-wrap gap-1">
              {(Object.keys(FAILURE_REASON_LABEL) as FailureReason[]).map((reason) => {
                const count = failureReasonCounts.get(reason) ?? 0;
                if (count === 0) return null;
                return (
                  <span key={reason} className="rounded-sm border border-cmd-border/60 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-cmd-textDim">
                    {FAILURE_REASON_LABEL[reason]} ({count})
                  </span>
                );
              })}
            </div>
            <div className="space-y-1.5">
              {recentFailures.map((classification) => (
                <FailureClassificationRow key={classification.id} classification={classification} expanded={expandedFailureId === classification.id} onToggle={() => setExpandedFailureId(expandedFailureId === classification.id ? null : classification.id)} />
              ))}
            </div>
          </>
        )}
      </Glass>

      <Glass className="max-h-96 overflow-y-auto p-3 lg:col-span-2">
        <div className="mb-1.5 flex items-center justify-between">
          <TerminalLabel>Exit Efficiency</TerminalLabel>
          <span className="text-[9px] text-cmd-textDim">
            Where a trade closed within its own real observed range — never how the decision was made, never why the thesis failed
          </span>
        </div>
        {exitEfficiency === null ? (
          <EmptyState>Loading…</EmptyState>
        ) : exitEfficiency.reads.length === 0 ? (
          <EmptyState>No trade has closed yet.</EmptyState>
        ) : (
          <>
            <div className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-2 sm:grid-cols-5">
              <DataRow
                label="Avg Capture"
                value={exitEfficiency.avgCapturePct === null ? "NOT ENOUGH DATA" : `${exitEfficiency.avgCapturePct.toFixed(0)}%`}
                valueClassName={exitEfficiency.avgCapturePct === null ? "text-cmd-textDim" : "text-cmd-text"}
              />
              <DataRow label="Efficient" value={exitEfficiency.efficientExitCount} valueClassName="text-cmd-green" />
              <DataRow label="Average" value={exitEfficiency.averageExitCount} />
              <DataRow label="Poor" value={exitEfficiency.poorExitCount} valueClassName={exitEfficiency.poorExitCount > 0 ? "text-cmd-red" : "text-cmd-text"} />
              <DataRow label="Not Enough Data" value={exitEfficiency.notEnoughDataCount} />
            </div>
            <div className="space-y-1">
              {recentExitReads.map((read) => (
                <ExitEfficiencyRow key={read.tradeId} read={read} />
              ))}
            </div>
          </>
        )}
      </Glass>
    </div>
  );
}

function ExitEfficiencyRow({ read }: { read: TradeExitEfficiency }) {
  return (
    <div className="flex items-center gap-2 rounded-sm border border-cmd-border/40 bg-cmd-bg/30 px-2 py-1 text-[9px]">
      <StatusPill tone={exitEfficiencyTone(read.evidenceState)}>{EXIT_EFFICIENCY_LABEL[read.evidenceState]}</StatusPill>
      <span className="font-cmdmono text-cmd-cyan">{read.symbol}</span>
      <span className="text-cmd-textDim">Day {read.simDay}</span>
      <span className={read.pnlPct >= 0 ? "text-cmd-green" : "text-cmd-red"}>
        {read.pnlPct >= 0 ? "+" : ""}
        {read.pnlPct.toFixed(2)}%
      </span>
      <span className="ml-auto text-cmd-textDim">
        range {read.maePct.toFixed(1)}% → {read.mfePct.toFixed(1)}%{read.capturePct !== null && ` — ${read.capturePct.toFixed(0)}% captured`}
      </span>
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

function FailureClassificationRow({ classification, expanded, onToggle }: { classification: FailureClassification; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-[9px]">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-2 text-left">
        <span className="flex items-center gap-1.5">
          <span className="text-cmd-cyan">{classification.symbol}</span>
          <StatusPill tone={FAILURE_REASON_TONE[classification.reason]}>{FAILURE_REASON_LABEL[classification.reason]}</StatusPill>
        </span>
        <span className="tabular-nums text-cmd-red">{classification.tradePnlPct.toFixed(1)}%</span>
      </button>
      <div className="mt-1 text-cmd-textDim">{classification.evidence}</div>
      {expanded && classification.attributedAgents.length > 0 && (
        <div className="mt-2 border-t border-cmd-border/50 pt-2 text-[9px] text-cmd-textDim">
          Attributed: {classification.attributedAgents.map((a) => AGENT_PROFILES[a].name).join(", ")}
        </div>
      )}
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
