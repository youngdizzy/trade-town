"""app/failure_review.py — CEO directive "Features 26-30: Agent
Intelligence, Learning & Institutional Memory System," Feature 30 (Agent
Debate + Failure Review Board), the final stage of the
26->27->28->29->30 learning loop. Per the directive's own staging rule,
this does not begin until Feature 29 is tested and integrated.

RESEARCH FINDING (recorded here per the directive's "document what was
found before coding" rule): the CEO's brief asked this piece to reuse
app/debate.py / app/devils_advocate.py / app/discipline.py's existing
machinery rather than invent a new debate engine or failure taxonomy
from scratch. Direct inspection confirmed:

  app/debate.py           — generate_debate() is pre-decision
                             deliberation only. Already reused (never
                             regenerated) by app/discipline.py's
                             compute_discipline_score() and this
                             module — see classify_failure() below,
                             which reads the same real DisciplineReview
                             a closed trade already produced, never a
                             second debate-derived computation.
  app/devils_advocate.py  — generate_challenge_report() targets a
                             pending, not-yet-decided proposal. No
                             post-hoc failure-reason concept exists
                             here; genuinely out of scope for a
                             post-close classification.
  app/discipline.py       — the real machinery this module leans on
                             hardest: DisciplineReview.factors (the
                             seven real, already-scored process
                             factors) and DisciplineReview.
                             post_decision_review (the seven real
                             post-decision-question lists) are both
                             reused verbatim below, never recomputed a
                             second, possibly-drifting way.

A second real taxonomy already exists in this codebase —
CaseStudyCategory (app/mistakes.py's six loss categories:
overconfidence, incomplete_research, unchallenged_assumptions,
acted_too_quickly, ignored_dissent, confirmation_bias). It answers a
different question than this module: CaseStudyCategory asks "what
BEHAVIORAL/PROCESS mistake occurred," this module asks "why did the
THESIS actually FAIL." A trade can be process-perfect and still rest on
a wrong thesis (a well-run debate can still misjudge the market), or
have a flawless thesis undone by a real process lapse — so this is a
genuinely separate axis, not a duplicate. Where the two do correlate
(e.g. "incomplete_research" case study <-> "information_gap" failure
reason), this module REUSES the already-detected CaseStudyCategory as
real evidence rather than re-deriving the same signal a second way —
see classify_failure()'s precedence order below.

FailureReason (app/schemas.py) has seven real, evidence-backed values.
An eighth, "external_shock" (a Black Swan event), was researched and
explicitly cut: app/schemas.py's CrisisBriefing is "Never persisted as
its own list" and carries no black_swan_event_id link to any
PaperTrade/TradeDecision, so there is no honest per-trade evidence to
classify against. Disclosed here as a real scope cut, not shipped as a
permanently-dead enum value no code path could ever produce.

GOVERNANCE BOUNDARY (matches Feature 29's own precedent exactly): this
module is purely retrospective and promotion-only. It runs only after a
trade has already closed, reads real evidence gatekeeper.py/
risk_engine.py already computed, and touches none of it — no changes to
gatekeeper.py, risk_engine.py, Circuit Breakers, or the Model Validator.
Nothing here can block or alter a future trade.

Precedence order (classify_failure() below), most objectively-verifiable
real signal first, so a trade matching more than one real cause still
gets exactly one honest classification:

  1. process_violation         <- app/process_adherence.py's own
                                   _trading_mode_check() reused verbatim
                                   (a real, checkable rule violation).
  2. risk_management_failure   <- DisciplineReview's own
                                   position_sizing_discipline factor,
                                   using the same "< 55 = weak" bar
                                   discipline.py's own
                                   _post_decision_review() already uses.
  3. information_gap           <- this trade's own "incomplete_research"
                                   CaseStudy, if one was filed.
  4. market_regime_misread     <- the Market Intelligence Learning
                                   Loop's own regime_consistent read
                                   (app/market_intelligence.py),
                                   cross-referenced by real sim day
                                   against the trade's own real hold
                                   window. Day-level, not per-trade —
                                   disclosed in the evidence string.
  5. poor_execution            <- this trade's own "acted_too_quickly"
                                   or "ignored_dissent" CaseStudy.
  6. bad_thesis                <- this trade's own "unchallenged_
                                   assumptions", "overconfidence", or
                                   "confirmation_bias" CaseStudy.
  7. unknown                   <- no real signal above fired; an honest
                                   "not enough evidence to name a cause"
                                   result, never a guess.
"""
from __future__ import annotations

from app.process_adherence import _trading_mode_check
from app.schemas import (
    AgentId,
    CaseStudy,
    CaseStudyCategory,
    DisciplineReview,
    FailureClassification,
    FailureReason,
    MarketIntelligenceLearningEntry,
    PaperTrade,
    TradeDecision,
)

MAX_FAILURE_CLASSIFICATIONS = 60

# The same real "weak" bar discipline.py's own _post_decision_review()
# already uses to decide which factors land in mistakesMade/
# whatToNeverRepeat — reused, not reinvented.
WEAK_FACTOR_THRESHOLD = 55.0

_INFORMATION_GAP_CATEGORIES: frozenset[CaseStudyCategory] = frozenset({"incomplete_research"})
_POOR_EXECUTION_CATEGORIES: tuple[CaseStudyCategory, ...] = ("acted_too_quickly", "ignored_dissent")
_BAD_THESIS_CATEGORIES: tuple[CaseStudyCategory, ...] = ("unchallenged_assumptions", "overconfidence", "confirmation_bias")


def _case_study_for(
    case_studies: list[CaseStudy], categories: tuple[CaseStudyCategory, ...] | frozenset[CaseStudyCategory]
) -> CaseStudy | None:
    """Returns this trade's own CaseStudy matching the highest-priority
    category in `categories` (iteration order = priority for a tuple; a
    frozenset has exactly one member so order is moot)."""
    by_category = {cs.category: cs for cs in case_studies}
    for wanted in categories:
        match = by_category.get(wanted)
        if match is not None:
            return match
    return None


def _process_violation(trade: PaperTrade) -> str | None:
    check = _trading_mode_check(trade)
    if check.status == "failed":
        return check.detail
    return None


def _risk_management_failure(discipline_review: DisciplineReview) -> str | None:
    factor = next((f for f in discipline_review.factors if f.id == "position_sizing_discipline"), None)
    if factor is not None and factor.score < WEAK_FACTOR_THRESHOLD:
        return f"Position Sizing Discipline factor scored {factor.score:.0f}/100 in the Discipline Chamber review — {factor.detail}"
    return None


def _market_regime_misread(
    trade: PaperTrade, market_intelligence_learning: list[MarketIntelligenceLearningEntry]
) -> str | None:
    if trade.closed_sim_minutes <= 0:
        return None
    open_day = trade.opened_sim_minutes // 1440
    close_day = trade.closed_sim_minutes // 1440
    misreads = [
        e
        for e in market_intelligence_learning
        if open_day <= e.for_sim_day <= close_day and e.regime_consistent is False
    ]
    if not misreads:
        return None
    entry = misreads[0]
    return (
        f"The Market Intelligence Learning Loop found sim day {entry.for_sim_day}'s real market environment "
        f"({entry.actual_environment_regime}) inconsistent with the predicted regime ({entry.predicted_regime}) — "
        f"{entry.lesson} This is a company-wide, day-level read (no per-trade regime-call mechanism exists), "
        "cross-referenced here only by real sim-day overlap with this trade's own hold window."
    )


def classify_failure(
    decision: TradeDecision,
    trade: PaperTrade,
    discipline_review: DisciplineReview,
    case_studies: list[CaseStudy],
    market_intelligence_learning: list[MarketIntelligenceLearningEntry],
    *,
    classification_id: str,
    sim_day: int,
    created_at: str,
) -> FailureClassification:
    """Only ever called for a real closed, losing trade (see nexus.py's
    wiring — the same `trade.pnl <= 0` branch that already files this
    trade's CaseStudy(s)). `case_studies` is this trade's own filed
    studies (may be empty — a well-disciplined loss to real market
    variance triggers none), never the capped company-wide list, so
    every category check below is complete for this trade regardless of
    MAX_CASE_STUDIES eviction elsewhere."""
    reason: FailureReason
    evidence: str | None

    evidence = _process_violation(trade)
    if evidence is not None:
        reason = "process_violation"
    else:
        evidence = _risk_management_failure(discipline_review)
        if evidence is not None:
            reason = "risk_management_failure"
        else:
            info_gap_study = _case_study_for(case_studies, _INFORMATION_GAP_CATEGORIES)
            if info_gap_study is not None:
                reason = "information_gap"
                evidence = info_gap_study.missed_information
            else:
                evidence = _market_regime_misread(trade, market_intelligence_learning)
                if evidence is not None:
                    reason = "market_regime_misread"
                else:
                    execution_study = _case_study_for(case_studies, _POOR_EXECUTION_CATEGORIES)
                    if execution_study is not None:
                        reason = "poor_execution"
                        evidence = execution_study.missed_information
                    else:
                        thesis_study = _case_study_for(case_studies, _BAD_THESIS_CATEGORIES)
                        if thesis_study is not None:
                            reason = "bad_thesis"
                            evidence = thesis_study.missed_information
                        else:
                            reason = "unknown"
                            evidence = (
                                f"No specific real failure signal (Trading Mode Compliance, Risk Management, "
                                f"Case Study categories, or the Market Intelligence regime check) fired for this "
                                f"trade — the Discipline Chamber scored the process {discipline_review.tier} "
                                f"({discipline_review.score:.0f}/100). Filed as Unknown rather than guessing a cause."
                            )

    attributed: list[AgentId] = list(decision.supporting_agents)

    return FailureClassification(
        id=classification_id,
        tradeId=trade.id,
        decisionId=decision.id,
        symbol=decision.symbol,
        reason=reason,
        evidence=evidence,
        attributedAgents=attributed,
        tradePnlPct=round(trade.pnl_pct, 2),
        simDay=sim_day,
        createdAt=created_at,
    )


def record_failure_classification(
    classifications: list[FailureClassification],
    classification: FailureClassification,
    *,
    max_records: int = MAX_FAILURE_CLASSIFICATIONS,
) -> list[FailureClassification]:
    updated = [*classifications, classification]
    if len(updated) > max_records:
        del updated[: len(updated) - max_records]
    return updated


def should_promote_failure_classification(classification: FailureClassification) -> bool:
    """"unknown" carries no real actionable lesson to file — every other
    reason reused a real, checkable signal and is worth promoting."""
    return classification.reason != "unknown"
