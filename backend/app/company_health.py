"""CompanyHealth — v0.7 Feature 23, the Company Health & Stability System.

Ten sub-scores, each a small, named, documented formula (same
"transparency over automation" convention `app/company_score.py`
already established) rather than a single opaque number. Several
sub-scores necessarily reuse the exact same underlying real signal an
existing v0.5 CompanyScore metric already reads (agent mood, research
completion, portfolio P&L) — that's an intentional, documented overlap
(the two systems answer different questions: "is the company performing
well" vs. "is the company healthy to keep operating"), never two
independently-invented readings of the same thing.

Four of the ten map onto real state that has no prior aggregate reading
anywhere else in this codebase: Resource Usage (AgentEnergy's real
current/cap), Reputation (real HallOfFameEntry count), Technology Level
(the real SignalCalibrationState.unlockedLevel progression), and Market
Coverage (the real count of extra symbols added to the watchlist beyond
the eight SEED_SYMBOLS via the "watch_symbol" Agent Energy action — see
app/watchlist.py's EXTRA_SYMBOL_POOL; renamed from "Office Expansion"
under the CEO's Company/Executive Health directive — the formula was
always real watchlist growth, never a facility/office-capability
mechanic this codebase has never had). None of these are fabricated
company-management mechanics; every one is a real, already-tracked
number this module is the first to actually read.

v0.7 Feature 50 (Part 2/3) — the Company Health redesign adds a second,
Executive tier of ten more real, checkable dimensions
(`_EXECUTIVE_METRIC_LABELS` below), computed from data the Executive
Intelligence Network itself now produces (Decision Grade, the Executive
Meeting Log, Weekly Self-Evaluation) plus real existing systems this
module never previously read (Wisdom, Innovation Points, the Academy,
the Founder Council). This is additive, not a replacement: the original
eleven Operational dimensions above keep their exact original meaning
and formula — `overall`/`tier` are unchanged, so every existing
consumer (Company Priorities, the Founders' retirement trigger, the
COMPANY tab) keeps working identically. `executiveOverall`/
`executiveTier` are the new tier's own headline; `combinedOverall`/
`combinedTier` (an equal blend of the two) is the true redesigned
headline number.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.academy import is_mentor_level
from app.continuous_improvement import compute_remediation_effectiveness, compute_root_cause_recurrence
from app.control_effectiveness import compute_control_effectiveness
from app.discipline import GOOD_DISCIPLINE_TIERS, POOR_DISCIPLINE_TIERS
from app.education import all_lessons
from app.foundational_mentors import STUDENT_AGENT_IDS
from app.innovation import TIER_THRESHOLDS as INNOVATION_TIER_THRESHOLDS
from app.sandbox import STAGE_ORDER, stage_index
from app.schemas import (
    AgentEnergy,
    AgentId,
    AgentKnowledgeState,
    AgentState,
    ComplianceIncident,
    CompanyHealth,
    CompanyHealthComponentDelta,
    CompanyHealthDelta,
    CompanyHealthTier,
    CompanyHealthWeakArea,
    Debate,
    DepartmentSelfEvaluation,
    DisciplineReview,
    EducationProgress,
    ExecutiveMeetingLogEntry,
    FounderCouncilSession,
    FoundationalMentorState,
    GatekeeperRejection,
    HallOfFameEntry,
    InnovationState,
    PaperPortfolio,
    PaperTrade,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
    Strategy,
    StrategyHealthAssessment,
    TradeDecision,
    WatchlistEntry,
    WisdomState,
)
from app.signal_calibration import MAX_LEVEL as SIGNAL_MAX_LEVEL
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS

# v0.7 Feature 50 (Part 2/3) — how many recent decisions/meeting-log
# entries the new Executive-tier metrics look back over. Deliberately
# the same order of magnitude as MAX_DECISIONS' own recent-history
# reasoning elsewhere in this codebase — recent behavior, not the
# company's entire history.
EXECUTIVE_METRIC_WINDOW = 30
LEGENDARY_INNOVATOR_THRESHOLD = INNOVATION_TIER_THRESHOLDS[-1]

RESTFUL_LOCATIONS = {"lobby", "break-room"}

# Mirrors app/executive_intelligence.py::compute_executive_recommendation()'s
# own real "opposing" bucket exactly — genuine substantive opposition,
# distinct from the "waiting" bucket (request_more_research/
# recommend_waiting/recommend_position_change), which is a constructive
# epistemic stance, not disagreement. Reused rather than redefined so
# _department_consensus() below reads the same real taxonomy the rest of
# the Executive Intelligence Network already uses.
_OPPOSING_STANCES = frozenset({"disagree", "recommend_rejecting"})

_SEVERITY_PENALTY = {"critical": 15.0, "warning": 6.0, "info": 2.0}

_TIER_THRESHOLDS: list[tuple[float, CompanyHealthTier]] = [
    (85.0, "excellent"),
    (70.0, "good"),
    (50.0, "stable"),
    (30.0, "needs_attention"),
]

_METRIC_LABELS: dict[str, str] = {
    "operational_stability": "Operational Stability",
    "department_efficiency": "Department Efficiency",
    "employee_morale": "Employee Morale",
    "research_progress": "Research Progress",
    "capital_health": "Capital Health",
    "resource_usage": "Resource Usage",
    "reputation": "Reputation",
    "technology_level": "Technology Level",
    "market_coverage": "Market Coverage",
    "education_progress": "Education Progress",
    "team_chemistry": "Team Chemistry",
}

# v0.7 Feature 50 (Part 2/3) — the Company Health redesign. Ten new
# Executive-tier dimensions, real and checkable, computed from data the
# Executive Intelligence Network itself now produces (Decision Grade,
# the Executive Meeting Log, Weekly Self-Evaluation) plus real existing
# systems this file never previously read (Wisdom, Innovation Points,
# the Academy, the Founder Council). Additive alongside the eleven
# Operational dimensions above — never replacing them (see this
# module's own docstring for why).
_EXECUTIVE_METRIC_LABELS: dict[str, str] = {
    "decision_quality": "Decision Quality",
    "executive_alignment": "Executive Alignment",
    "risk_governance": "Risk Governance",
    "simulation_coverage": "Simulation Coverage",
    "department_consensus": "Department Consensus",
    "self_evaluation_health": "Self-Evaluation Health",
    "institutional_memory": "Institutional Memory",
    "innovation_velocity": "Innovation Velocity",
    "talent_development": "Talent Development",
    "founder_oversight": "Founder Oversight",
    "compliance_health": "Compliance Health",
}

# The window of most-recent debates a fresh Team Chemistry reading is
# computed over — recent behavior, not the company's entire history.
TEAM_CHEMISTRY_WINDOW = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier(overall: float, thresholds: list[tuple[float, CompanyHealthTier]] = _TIER_THRESHOLDS) -> CompanyHealthTier:
    for threshold, tier in thresholds:
        if overall >= threshold:
            return tier
    return "critical"


def _operational_stability(risk_warnings: list[RiskWarning]) -> float:
    penalty = sum(_SEVERITY_PENALTY.get(w.severity, 2.0) for w in risk_warnings)
    return max(0.0, 100.0 - penalty)


def _department_efficiency(agents: dict[AgentId, AgentState]) -> float:
    """CEO Company/Executive Health directive: investigated whether this
    could blend in a real "did they actually accomplish something"
    signal, not just presence. Direct trace of every other real
    per-agent signal in this codebase found none that would work: the
    free-text `current_task` schedule label and the structured `Task`
    system (`app/nexus.py`'s `_replace_working_task()`) both mark the
    prior task "completed" purely because the agent's schedule block
    changed — a real timer, not real evidence of accomplished work — so
    every agent reads as continuously "completing tasks" regardless of
    outcome, which would make a second component built on either of them
    tautological (always ~100%), not a genuine additional signal.

    Per explicit CEO direction, this stays presence-only — real (an
    agent genuinely is or isn't at a real work location, not
    fabricated), just intentionally narrow: it answers "is the
    department staffed and present," not "is real output being
    produced." `_research_progress()` and the Executive tier's
    `_decision_quality()`/`_simulation_coverage()` are this codebase's
    real output-quality signals; duplicating that coverage here under a
    different name was rejected as the fabrication this module's own
    conventions bar. A genuine second signal would need a real new
    mechanic (e.g. Task completion gated by real downstream evidence,
    not a schedule timer) — out of scope for this pass, documented here
    rather than left unexplained."""
    if not agents:
        return 50.0
    working = sum(1 for a in agents.values() if a.location not in RESTFUL_LOCATIONS)
    return working / len(agents) * 100.0


def _employee_morale(agents: dict[AgentId, AgentState]) -> float:
    if not agents:
        return 50.0
    return sum(a.mood for a in agents.values()) / len(agents)


def _research_progress(research: list[ResearchItem]) -> float:
    if not research:
        return 50.0
    completed = sum(1 for r in research if r.status == "completed")
    return completed / len(research) * 100.0


def _capital_health(portfolio: PaperPortfolio) -> float:
    return max(0.0, min(100.0, 50.0 + portfolio.total_pnl_pct * 1.5))


def _resource_usage(agent_energy: AgentEnergy) -> float:
    if agent_energy.cap <= 0:
        return 50.0
    return max(0.0, min(100.0, agent_energy.current / agent_energy.cap * 100.0))


def _reputation(hall_of_fame: list[HallOfFameEntry]) -> float:
    return min(100.0, len(hall_of_fame) * 4.0)


def _technology_level(signal_calibration: SignalCalibrationState) -> float:
    if SIGNAL_MAX_LEVEL <= 1:
        return 100.0
    return (signal_calibration.unlocked_level - 1) / (SIGNAL_MAX_LEVEL - 1) * 100.0


def _market_coverage(watchlist: list[WatchlistEntry]) -> float:
    """CEO Company/Executive Health directive: renamed from
    `_office_expansion()` — the formula (real extra symbols added to the
    watchlist beyond the 8 SEED_SYMBOLS, relative to the real
    EXTRA_SYMBOL_POOL) never changed and never measured any facility/
    office-capability mechanic; this codebase has no such mechanic (see
    app/save_modules.py's own "No Buildings module" note). Same real
    formula, honest name."""
    if not EXTRA_SYMBOL_POOL:
        return 100.0
    added = max(0, len(watchlist) - len(SEED_SYMBOLS))
    return min(100.0, added / len(EXTRA_SYMBOL_POOL) * 100.0)


def _education_progress(education: EducationProgress) -> float:
    """CEO Company/Executive Health directive: the original formula
    (`completed_lesson_ids / total lessons`) is real and honest — every
    entry in `completed_lesson_ids` requires a real correct quiz answer
    (`app/education.py`'s `grade_quiz()` never marks a lesson complete on
    a wrong answer) — but it is legitimately slow (a small, fixed
    curriculum with no further growth once finished) and, on its own,
    credits only the *outcome* of the final correct attempt, never
    whether that understanding was solid or a lucky late guess after
    several wrong ones.

    Blended equally with a second real, already-tracked signal:
    `correct_quiz_attempts / quiz_attempts` (`EducationProgress`'s own
    two real counters, incremented by `grade_quiz()` on every real quiz
    submission, right or wrong — never fabricated, never reset by a
    retry). A player who answers correctly on the first real try scores
    higher than one who needed several guesses to land on the same
    completed lesson, even though both end up with an identical
    `completed_lesson_ids` set — genuine understanding, not just
    eventual completion. Neutral 50.0 for the accuracy half until at
    least one real quiz has actually been attempted."""
    total = len(all_lessons())
    completion = len(education.completed_lesson_ids) / total * 100.0 if total else 50.0
    accuracy = education.correct_quiz_attempts / education.quiz_attempts * 100.0 if education.quiz_attempts else 50.0
    return (completion + accuracy) / 2.0


def _debate_collaboration_quality(debates: list[Debate]) -> float:
    """v0.7 Feature 43, corrected under the CEO's Company/Executive
    Health directive — a real, checkable reading of whether analysts
    tend to back the desk's real final call or genuinely push back
    against it, over the most recent TEAM_CHEMISTRY_WINDOW debates.

    Reads app/debate.py's real per-analyst stance, which that module now
    assigns by comparing each analyst's own vote to the desk's actual
    overall_recommendation (not "does disagreement exist anywhere on the
    desk" — see that module's own docstring for the bug this replaced,
    which made nearly every debate read as 100% conflict). A 4-2 split
    now yields 4 support turns and 2 real challenge turns, so this
    signal genuinely rewards GOOD DISAGREEMENT (a real minority dissent,
    preserved and visible) alongside real majority alignment, rather
    than collapsing every non-unanimous debate to zero. 50.0 (neutral)
    until the company has held at least one real debate."""
    recent = debates[-TEAM_CHEMISTRY_WINDOW:]
    turns = [t for d in recent for t in d.turns if t.stance != "opening"]
    if not turns:
        return 50.0
    supportive = sum(1 for t in turns if t.stance == "support")
    return supportive / len(turns) * 100.0


def _cross_agent_research_handoffs(research: list[ResearchItem]) -> float:
    """The CEO's Company Health directive asked Team Chemistry to
    reflect real collaboration, not just debate tone — this is the
    second real, non-fabricated signal: whether completed research
    within the same real category actually gets picked up and built on
    by a *different* agent, versus one agent working a subject in
    isolation. Same real category-and-recency grouping
    app/knowledge_graph.py's own _builds_on_chain() already uses to draw
    "builds on" edges between research items — this reads the identical
    real ResearchItem.assignedAgent/category/updatedAt fields, just
    checking whether the agent changed across each real consecutive
    pair instead of drawing a graph edge from it. 50.0 (neutral) until
    the company has at least one same-category pair to check — a
    single completed research item, or research items that never share
    a category, has no real handoff to measure yet."""
    completed = [r for r in research if r.status == "completed"]
    by_category: dict[str, list[ResearchItem]] = {}
    for item in completed:
        by_category.setdefault(item.category, []).append(item)

    total_pairs = 0
    handoffs = 0
    for items in by_category.values():
        ordered = sorted(items, key=lambda r: r.updated_at)
        for earlier, later in zip(ordered, ordered[1:]):
            total_pairs += 1
            if later.assigned_agent != earlier.assigned_agent:
                handoffs += 1

    if total_pairs == 0:
        return 50.0
    return handoffs / total_pairs * 100.0


def _team_chemistry(debates: list[Debate], research: list[ResearchItem]) -> float:
    """v0.7 Feature 43, extended under the CEO's Company/Executive
    Health directive: an equal, unweighted mean of two independent real
    collaboration signals — see _debate_collaboration_quality() (how the
    desk behaves toward its own real final calls) and
    _cross_agent_research_handoffs() (whether research knowledge
    actually crosses between agents) above. Same "plain mean, no hidden
    weighting" convention this module already uses throughout. Mentorship/
    knowledge-sharing (already read by app/wisdom.py's own
    share_knowledge factor, which feeds Institutional Memory) is
    deliberately not re-read a second time here — see this module's own
    "no duplicate systems" convention — a genuinely new, checkable
    collaboration signal (e.g. real CEO-assigned cross-agent review
    pairings) is documented as future work rather than duplicated."""
    return (_debate_collaboration_quality(debates) + _cross_agent_research_handoffs(research)) / 2.0


def _decision_quality(decisions: list[TradeDecision], discipline_reviews: list[DisciplineReview]) -> float:
    """v0.7 Feature 50 Part 2/3, extended under the CEO's Company/
    Executive Health directive.

    `decision_grade_score` was already real and already outcome-decoupled
    — `compute_decision_grade()` (app/executive.py) blends the real
    Decision Confidence Engine score, real analyst agreement, and real
    Trade Gatekeeper approval, computed the moment the CEO decides,
    before any trade outcome exists. Averaging it (kept below as `base`)
    already satisfies the CEO's core instruction — "do not judge
    decisions solely by whether they made money" — since it never reads
    pnl at all. The real gap: nothing ever checked whether that initial
    grade was *calibrated* — whether it agreed with a second, genuinely
    independent real assessment of the same decision.

    `app/discipline.py`'s own Discipline Score is exactly that: computed
    separately, later (at trade close, once a real hold duration is
    known), from a different weighted blend of real factors (research
    depth, viewpoint diversity, cross-examination, assumptions
    challenged, position sizing, patience) — and, per that module's own
    docstring, it "never reads `decision`'s outcome or any trade pnl"
    either. Comparing the two real, independently-computed, equally
    outcome-decoupled scores for the same real decision (linked by
    `DisciplineReview.decision_id`) is a genuine calibration check —
    "did the process look as good in hindsight as it did at the moment
    of decision" — without ever touching money either way. A close
    real agreement between the two earns high `calibration`; a wide gap
    (the initial grade and the independent later review disagreed about
    how sound the process really was) earns low `calibration`,
    regardless of whether the trade itself won or lost.

    `_decision_quality()` is now an equal blend of `base` and
    `calibration`. Neutral 50.0 for `calibration` when no real graded
    decision yet has a matching real closed-trade Discipline Review to
    check against — an honest "not yet calibratable" state, not a
    fabricated pass."""
    graded = [d for d in decisions if d.decision_grade_score is not None][-EXECUTIVE_METRIC_WINDOW:]
    if not graded:
        return 50.0
    base = sum(d.decision_grade_score for d in graded if d.decision_grade_score is not None) / len(graded)

    review_by_decision_id = {r.decision_id: r for r in discipline_reviews}
    agreements = [
        100.0 - abs(d.decision_grade_score - review_by_decision_id[d.id].score)
        for d in graded
        if d.decision_grade_score is not None and d.id in review_by_decision_id
    ]
    calibration = sum(agreements) / len(agreements) if agreements else 50.0

    return (base + calibration) / 2.0


def _executive_alignment(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    if not recent:
        return 50.0
    agreed = sum(1 for e in recent if e.network_agreed)
    return agreed / len(recent) * 100.0


def _risk_governance(trade_history: list[PaperTrade], gatekeeper_rejections: list[GatekeeperRejection]) -> float:
    total = len(trade_history) + len(gatekeeper_rejections)
    if total == 0:
        return 50.0
    return len(trade_history) / total * 100.0


def _simulation_coverage(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    if not recent:
        return 0.0
    covered = sum(1 for e in recent for op in e.opinions if op.role == "simulation" and op.stance != "request_more_research")
    return covered / len(recent) * 100.0


def _department_consensus(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    """v0.7 Feature 50 Part 2/3, corrected under the CEO's Company/
    Executive Health directive.

    The original formula counted only `stance == "agree"` as a positive
    signal, which is exactly the anti-pattern the CEO's directive named:
    it measured "did everybody vote yes," not "can the organization
    reach a coherent, evidence-supported decision." Direct trace of
    every real opinion generator (app/executive_intelligence.py) found
    `ExecutiveStance` already has six real values, not two — and
    `compute_executive_recommendation()` in that same module already
    treats `request_more_research`/`recommend_waiting`/
    `recommend_position_change` as a distinct real "waiting" bucket,
    genuinely different from real opposition
    (`disagree`/`recommend_rejecting`). Reused here rather than
    reinvented: a "waiting" stance is a legitimate, constructive
    epistemic position — asking for more evidence is not disagreement —
    so it counts as coherent alongside real agreement, never penalized.

    Only real, substantive opposition can drag this score down, and even
    then only when it's unsubstantiated: every opposing `DepartmentOpinion`
    already carries a real `concerns` list (Design Bible Chapter 70 Part 2,
    the Executive Consensus Meter) populated from that department's own
    real computed data (a risk vote's reasoning, a Devil's Advocate
    report's real hidden risks/weak assumptions, a Coach report's real
    common mistakes). An opposing opinion WITH real concerns on record is
    exactly the CEO's own "GOOD DISAGREEMENT + EVIDENCE" case — coherent,
    not penalized. Only a real opposing opinion with an empty `concerns`
    list (a bare, unsubstantiated block — confirmed by direct trace to be
    reachable today only via `_devils_advocate_opinion()`'s `major`
    severity path when it's driven by missing evidence or analyst dissent
    alone, with no specific hidden risk or weak assumption named) counts
    against the score. This module makes no attempt to model real
    escalation or resolution workflows beyond what's already tracked —
    see this function's Design Bible section for the honest remaining
    gap."""
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    opinions = [op for e in recent for op in e.opinions]
    if not opinions:
        return 50.0
    coherent = sum(1 for op in opinions if op.stance not in _OPPOSING_STANCES or op.concerns)
    return coherent / len(opinions) * 100.0


def _misalignment_rate(reviews: list[DisciplineReview]) -> float | None:
    """Real PREDICTION vs OUTCOME mismatch rate — a review is
    "misaligned" when its real process tier and its real trade outcome
    point opposite directions (a good-tier process that still lost, or
    a poor-tier process that happened to win — see
    app/discipline.py's own GOOD_DISCIPLINE_TIERS/POOR_DISCIPLINE_TIERS,
    reused here rather than reinvented). An "adequate"-tier review
    counts toward neither, the same real middle-tier convention
    discipline.py already established. None if there is no real
    checkable population yet."""
    aligned = sum(1 for r in reviews if (r.tier in GOOD_DISCIPLINE_TIERS and r.outcome == "win") or (r.tier in POOR_DISCIPLINE_TIERS and r.outcome == "loss"))
    misaligned = sum(1 for r in reviews if (r.tier in GOOD_DISCIPLINE_TIERS and r.outcome == "loss") or (r.tier in POOR_DISCIPLINE_TIERS and r.outcome == "win"))
    checkable = aligned + misaligned
    if checkable == 0:
        return None
    return misaligned / checkable


def _self_evaluation_health(self_evaluations: list[DepartmentSelfEvaluation], discipline_reviews: list[DisciplineReview]) -> float:
    """v0.7 Feature 50 Part 2/3, extended under the CEO's Company/
    Executive Health directive: PREDICTION -> OUTCOME -> ERROR ANALYSIS
    -> CORRECTION -> FUTURE IMPROVEMENT, not confidence alone.

    The original formula read only each department's average opinion
    confidence that week — a real signal that departments are actively
    engaging with real decisions, kept below as `engagement`, but never
    a prediction-vs-outcome comparison at all. The CEO's directive asked
    "Are predictions compared against outcomes?" and explicitly warned:
    "Do not reward agents merely for reporting that they made a
    mistake. Reward actual learning and reduced recurrence."

    The new `calibration_trend` component answers exactly that, reusing
    real data this codebase already computes for a different reason
    (app/discipline.py's own good/poor tier definitions) rather than
    inventing a new statistic: it compares the real misalignment rate
    (see `_misalignment_rate()` above) across the earlier half of real
    Discipline Reviews on record versus the later half — the same
    "earlier vs later real average" trend convention app/wisdom.py's
    own `_learn_from_experience()` already established, applied to a
    different real signal (misalignment rate, not raw score). A real
    DECREASE in misalignment over time — the organization's own
    predictions getting more accurate — earns credit; a flat or
    worsening rate does not, regardless of how many mistakes were
    merely logged. Neutral 50.0 with fewer than 4 real reviews on
    record — not enough real history to say anything honest about a
    trend yet."""
    if not self_evaluations and len(discipline_reviews) < 4:
        return 50.0
    engagement = 50.0
    if self_evaluations:
        latest_by_role: dict[str, float] = {}
        for entry in self_evaluations:
            latest_by_role[entry.role] = entry.score
        engagement = sum(latest_by_role.values()) / len(latest_by_role)

    calibration_trend = 50.0
    if len(discipline_reviews) >= 4:
        midpoint = len(discipline_reviews) // 2
        earlier_rate = _misalignment_rate(discipline_reviews[:midpoint])
        later_rate = _misalignment_rate(discipline_reviews[midpoint:])
        if earlier_rate is not None and later_rate is not None:
            calibration_trend = max(0.0, min(100.0, 50.0 + (earlier_rate - later_rate) * 100.0))

    return (engagement + calibration_trend) / 2.0


def _knowledge_retention(agent_knowledge: dict[AgentId, AgentKnowledgeState]) -> float:
    """CEO Company/Executive Health directive: Institutional Memory
    should reuse and strengthen real existing knowledge systems, not
    duplicate one under a new name. WisdomState.score (blended in below)
    already IS a real, comprehensive institutional-memory reading — an
    unweighted mean of eight real factors (learning from experience,
    documenting lessons, avoiding repeated mistakes, and more; see
    app/wisdom.py's own module docstring). What it does not read is
    whether that reflection has actually become durable in individual
    agents. app/academy.py's real seven-level per-agent KnowledgeLevel
    ladder (`is_mentor_level()` marking its real top tier, reached only
    by real cumulative points from completed research/Academy projects/
    meeting attendance — never fabricated) is a genuinely distinct real
    signal: Wisdom's own `share_knowledge` factor only tallies a raw
    MemoryRecord mentorship-session count, never actual depth of mastery
    reached. 0.0 with no agents — an honest floor, not a neutral guess,
    since a fresh company has genuinely retained nothing yet."""
    if not agent_knowledge:
        return 0.0
    mentors = sum(1 for state in agent_knowledge.values() if is_mentor_level(state))
    return mentors / len(agent_knowledge) * 100.0


def _institutional_memory(wisdom_state: WisdomState, agent_knowledge: dict[AgentId, AgentKnowledgeState]) -> float:
    """Equal blend of WisdomState.score (the company's own real weekly/
    monthly reflection score) and _knowledge_retention() above (whether
    that reflection has actually taken root in individual agents) — see
    _knowledge_retention()'s own docstring for why these are two
    genuinely distinct real signals, not one system read twice."""
    return (wisdom_state.score + _knowledge_retention(agent_knowledge)) / 2.0


def _validation_rigor(innovation_state: dict[AgentId, InnovationState]) -> float:
    """The original, unchanged Innovation Velocity formula: real average
    Devil's Advocate points (app/innovation.py) relative to the real
    Legendary Innovator threshold — the desk's demonstrated ability to
    find genuine weaknesses before capital is committed. Kept as one
    real ingredient below rather than replaced, since it already is a
    real, non-fabricated signal — just not the whole real pipeline the
    CEO's directive named."""
    if not innovation_state:
        return 0.0
    avg_points = sum(s.points for s in innovation_state.values()) / len(innovation_state)
    return min(100.0, avg_points / LEGENDARY_INNOVATOR_THRESHOLD * 100.0)


def _pipeline_progress(strategies: list[Strategy]) -> float:
    """CEO Company/Executive Health directive: Innovation Velocity was
    named for a pipeline ("USEFUL IDEA -> TESTABLE HYPOTHESIS -> EVIDENCE
    -> VALIDATION -> DEPLOYMENT -> MEASURED IMPROVEMENT") but the
    original formula (see _validation_rigor() above) read only one stage
    of it — Devil's Advocate critique quality — and nothing about
    whether ideas actually move. app/sandbox.py's own real, gated
    STAGE_ORDER (idea -> research -> historical_backtest ->
    market_simulation -> paper_trading -> limited_live_capital ->
    company_review -> approved -> retired) is a stage-for-stage match to
    that exact pipeline and is already tracked per real Strategy. A true
    time-to-deployment velocity would need a fabricated "ideal days per
    stage" constant this codebase has no real data to support (the CEO's
    directive explicitly forbids inventing such thresholds), so this
    reads real pipeline DEPTH instead — how far, on average, the
    company's real strategies have actually traveled down the real
    gated sequence, an honest, non-fabricated stand-in for velocity."""
    if not strategies:
        return 0.0
    max_index = len(STAGE_ORDER) - 1
    return sum(stage_index(s.stage) for s in strategies) / len(strategies) / max_index * 100.0


def _measured_improvement(strategies: list[Strategy], strategy_health_assessments: list[StrategyHealthAssessment]) -> float:
    """The pipeline's final real step: DEPLOYMENT -> MEASURED
    IMPROVEMENT. app/strategy_lab.py's compute_strategy_health() already
    produces a real, non-fabricated StrategyHealthAssessment.trend
    ("improving"/"stable"/"declining") per strategy, comparing that
    strategy's own recent real SimulationResults against its own
    lifetime average — never profit alone, the same "recent vs. own
    history" convention this module already uses elsewhere (e.g.
    _self_evaluation_health()'s calibration_trend). Only strategies that
    have actually reached real deployment (stage index >= "approved")
    count — an idea still in backtesting has nothing to measure
    improvement against yet. Neutral 50.0 when nothing has reached
    deployment yet, or a deployed strategy has no health read on record
    yet — an honest "not yet measurable" state, not a penalty."""
    deployed = [s for s in strategies if stage_index(s.stage) >= stage_index("approved")]
    if not deployed:
        return 50.0
    latest_by_strategy: dict[str, StrategyHealthAssessment] = {}
    for assessment in strategy_health_assessments:
        latest_by_strategy[assessment.strategy_id] = assessment
    trend_credit = {"improving": 100.0, "stable": 50.0, "declining": 0.0}
    scores = [trend_credit[latest_by_strategy[s.id].trend] for s in deployed if s.id in latest_by_strategy]
    if not scores:
        return 50.0
    return sum(scores) / len(scores)


def _innovation_velocity(innovation_state: dict[AgentId, InnovationState], strategies: list[Strategy], strategy_health_assessments: list[StrategyHealthAssessment]) -> float:
    """Equal blend of the three real pipeline ingredients above:
    _validation_rigor() (VALIDATION — catching weaknesses before capital
    is committed), _pipeline_progress() (IDEA -> HYPOTHESIS -> EVIDENCE
    -> DEPLOYMENT — real movement down the real Strategy Lab pipeline),
    and _measured_improvement() (DEPLOYMENT -> MEASURED IMPROVEMENT —
    whether deployed strategies actually hold up). 0.0 only when the
    company has neither ever filed a Devil's Advocate challenge nor has
    any strategies on record at all — an honest floor for a company that
    genuinely has not started yet, not a fabricated penalty."""
    if not innovation_state and not strategies:
        return 0.0
    return (_validation_rigor(innovation_state) + _pipeline_progress(strategies) + _measured_improvement(strategies, strategy_health_assessments)) / 3.0


def _talent_development(foundational_mentor_state: FoundationalMentorState, discipline_reviews: list[DisciplineReview]) -> float:
    """v0.7 Feature 50 Part 2/3, extended under the CEO's Company/
    Executive Health directive: TRAINING -> KNOWLEDGE -> APPLICATION ->
    PERFORMANCE -> REVIEW -> IMPROVEMENT, not mere XP.

    `graduation_status == "graduated"` was already real, not XP —
    reaching it requires completing every real lesson in a mentor's
    track (`_is_graduated_progress()`), each lesson auto-quizzed against
    that employee's own real aptitude (`_agent_aptitude()`, itself an
    average of real `DisciplineReview` scores the employee has
    attended), and then an explicit CEO approval
    (`approve_graduation()`) before it counts. That's the real TRAINING
    -> KNOWLEDGE half of the chain. What was missing, per the CEO's
    explicit instruction not to award credit "merely because a training
    event occurred," is the APPLICATION -> PERFORMANCE half: does a
    graduate's real on-the-job behavior actually hold up afterward?

    Each graduated (agent, mentor) pair now contributes a blend of two
    real signals: 100.0 for the real completed training (unchanged
    structural credit), and a real "post-graduation performance" reading
    — the average score of that same agent's real `DisciplineReview`s
    filed strictly after `graduated_sim_day` (the exact real day the CEO
    approved this graduation). A freshly-graduated agent with no
    post-graduation reviews yet reads a neutral 50.0 for that half — an
    honest "trained, application not yet demonstrable" state, not a
    fabricated pass or a punitive zero. A graduate who goes on to post
    genuinely strong real Discipline Scores earns close to full credit
    for the pair; one whose real post-graduation scores are weak earns
    less, even though they hold the same "graduated" badge — exactly the
    CEO's "reward actual learning, not the training event" instruction.
    A non-graduated real slot still contributes 0, unchanged."""
    active_mentors = [m for m in foundational_mentor_state.mentors if m.status == "active"]
    if not active_mentors:
        return 0.0
    total_slots = len(STUDENT_AGENT_IDS) * len(active_mentors)
    total_credit = 0.0
    for agent_id in STUDENT_AGENT_IDS:
        by_mentor = foundational_mentor_state.progress.get(agent_id, {})
        for mentor in active_mentors:
            progress = by_mentor.get(mentor.id)
            if progress is None or progress.graduation_status != "graduated":
                continue
            post_graduation_scores = [
                r.score for r in discipline_reviews if agent_id in r.attendees and progress.graduated_sim_day is not None and r.sim_day > progress.graduated_sim_day
            ]
            application_score = sum(post_graduation_scores) / len(post_graduation_scores) if post_graduation_scores else 50.0
            total_credit += (100.0 + application_score) / 2.0
    return total_credit / total_slots if total_slots else 0.0


def _founder_oversight(council_sessions: list[FounderCouncilSession]) -> float:
    """v0.7 Feature 39, extended under the CEO's Company/Executive
    Health directive: HIGH VISIBILITY + HIGH LEVERAGE + LOW
    MICROMANAGEMENT, not "how many sessions have ever occurred."

    The original formula (`min(100, count * 20)`) counted lifetime
    Founder Council sessions only — a company that held 5 sessions with
    nothing real to discuss in any of them scored identically to one
    whose every session surfaced a real major decision, a real risk, or
    a real dissenting analysis. The CEO's directive asked whether the
    CEO actually "receives meaningful decision summaries" and can
    "understand why important decisions were made" — occurrence alone
    can't answer that.

    Now an equal blend of two real signals: the original occurrence
    reading (still real — regular oversight cadence matters, per "HIGH
    LEVERAGE," not a one-off), and a new real substance reading — the
    average, across all real sessions on record, of how many of each
    session's three real notes (`coach_highlight_is_real`,
    `keystone_note_is_real`, `compass_note_is_real` — see
    app/founders.py's `generate_council_session()`) actually referenced
    real company content that period, versus its own honest "nothing to
    review yet" fallback. 0.0 (unchanged) until the company has held at
    least one real session — no oversight has ever happened yet."""
    if not council_sessions:
        return 0.0
    occurrence = min(100.0, len(council_sessions) * 20.0)
    substance = sum(
        (int(s.coach_highlight_is_real) + int(s.keystone_note_is_real) + int(s.compass_note_is_real)) / 3.0 * 100.0 for s in council_sessions
    ) / len(council_sessions)
    return (occurrence + substance) / 2.0


# CEO directive "Features 31-35," Feature 35 — Continuous Compliance
# Improvement, connected into Company Health through this EXISTING
# architecture (a new, additive Executive-tier dimension, the same "new
# dimension, never a rewrite" pattern every sibling above already
# follows) rather than a second, parallel scoring system. Deliberately
# NOT `app/audit_log.py::compute_compliance_score()` — that formula
# stays untouched; see this function's own return-path comments and the
# Design Bible/Architecture.md for the documented limitation and
# proposed (not yet CEO-authorized) change to that separate formula.
def _compliance_health(
    compliance_incidents: list[ComplianceIncident],
    decisions: list[TradeDecision],
    gatekeeper_rejections: list[GatekeeperRejection],
    current_sim_day: int,
) -> float:
    """A real, disclosed blend of three genuinely different real
    evidence sources — incident resolution, remediation effectiveness
    (Feature 35), and control effectiveness (Feature 34) — never a
    single opaque number. Each component defaults to the neutral 50.0
    this file's own `_risk_governance()` already established for "no
    real evidence yet" (never a fabricated 0 or 100), and a real,
    disclosed penalty subtracts for any confirmed RECURRING FAILURE
    (the same root cause repeatedly producing incidents)."""
    if not compliance_incidents:
        resolution_component = 50.0
    else:
        resolved_count = sum(1 for i in compliance_incidents if i.status == "resolved")
        resolution_component = resolved_count / len(compliance_incidents) * 100.0

    remediations = compute_remediation_effectiveness(compliance_incidents, current_sim_day=current_sim_day)
    scored_remediations = [r for r in remediations if r.effectiveness_state != "not_enough_evidence"]
    if not scored_remediations:
        remediation_component = 50.0
    else:
        effective = sum(1 for r in scored_remediations if r.effectiveness_state == "effective")
        partially_effective = sum(1 for r in scored_remediations if r.effectiveness_state == "partially_effective")
        remediation_component = (effective + 0.5 * partially_effective) / len(scored_remediations) * 100.0

    control_summary = compute_control_effectiveness(decisions, gatekeeper_rejections)
    scored_controls = [c for c in control_summary.controls if c.effectiveness_state not in ("not_yet_tested", "insufficient_data")]
    if not scored_controls:
        control_component = 50.0
    else:
        effective_controls = sum(1 for c in scored_controls if c.effectiveness_state == "effective")
        mixed_controls = sum(1 for c in scored_controls if c.effectiveness_state == "mixed")
        control_component = (effective_controls + 0.5 * mixed_controls) / len(scored_controls) * 100.0

    recurrences = compute_root_cause_recurrence(compliance_incidents)
    recurring_failure_count = sum(1 for r in recurrences if r.recurring_failure)
    # Disclosed, capped penalty — same "conservative but arbitrary, no
    # real regulatory requirement behind it" honesty note the Compliance
    # Score formula itself already carries (app/audit_log.py).
    recurrence_penalty = min(30.0, recurring_failure_count * 10.0)

    blended = (resolution_component + remediation_component + control_component) / 3.0
    return round(max(0.0, blended - recurrence_penalty), 1)


# CEO directive "Command Center + Professional Quant Trading Firm
# Upgrade" — the Executive View's Problem/Cause/Severity/Action
# breakdown. Every branch below restates the SAME real inputs
# compute_company_health() already reads for that metric's own score
# (calling the same standalone _debate_collaboration_quality()/
# _cross_agent_research_handoffs()/_knowledge_retention()/
# _validation_rigor()/_pipeline_progress()/_measured_improvement()
# helpers directly where one already exists, so the cited evidence can
# never drift from the real formula) — never a second, independently
# invented reading. Where a metric is a blend with no standalone
# sub-function to call without duplicating fragile inline logic (decision
# quality's calibration check, self-evaluation's trend), the cause names
# the real blend honestly rather than fabricating false precision about
# which half is weaker. `action` says "No direct lever" wherever true —
# several of these metrics are genuinely observational (agent mood,
# presence, real trading P&L), not something a CEO click can move, and
# pretending otherwise would be exactly the invented-actionability this
# codebase's conventions bar.
def _diagnose(
    key: str,
    *,
    risk_warnings: list[RiskWarning],
    agents: dict[AgentId, AgentState],
    research: list[ResearchItem],
    portfolio: PaperPortfolio,
    agent_energy: AgentEnergy,
    hall_of_fame: list[HallOfFameEntry],
    signal_calibration: SignalCalibrationState,
    watchlist: list[WatchlistEntry],
    education: EducationProgress,
    debates: list[Debate],
    decisions: list[TradeDecision],
    meeting_log: list[ExecutiveMeetingLogEntry],
    wisdom_state: WisdomState,
    innovation_state: dict[AgentId, InnovationState],
    founder_council_sessions: list[FounderCouncilSession],
    gatekeeper_rejections: list[GatekeeperRejection],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    strategies: list[Strategy],
    strategy_health_assessments: list[StrategyHealthAssessment],
    compliance_incidents: list[ComplianceIncident],
) -> tuple[str, str]:
    if key == "operational_stability":
        if not risk_warnings:
            return "No active real risk warnings — this reflects the full 100-point baseline.", "No action needed."
        penalty = sum(_SEVERITY_PENALTY.get(w.severity, 2.0) for w in risk_warnings)
        critical = sum(1 for w in risk_warnings if w.severity == "critical")
        return (
            f"{len(risk_warnings)} real risk warning(s) on record ({critical} critical), a combined {penalty:.0f}-point penalty.",
            "Resolve the real risk warnings driving the penalty — critical ones cost the most (15 pts each).",
        )
    if key == "department_efficiency":
        working = sum(1 for a in agents.values() if a.location not in RESTFUL_LOCATIONS)
        return (
            f"Only {working} of {len(agents)} agents are at a real work location (not lobby/break-room) this tick.",
            "No direct lever — reflects agents' real current schedule locations and recovers as their day progresses.",
        )
    if key == "employee_morale":
        avg_mood = sum(a.mood for a in agents.values()) / len(agents) if agents else 0.0
        return (
            f"Average real agent mood is {avg_mood:.0f}/100 across {len(agents)} agents.",
            "No direct lever — mood already responds to real rest, breaks, and meetings agents take autonomously.",
        )
    if key == "research_progress":
        completed = sum(1 for r in research if r.status == "completed")
        return (
            f"{completed} of {len(research)} real research items on record are completed.",
            "Assign or prioritize research for idle agents — completion pace is otherwise agent-driven.",
        )
    if key == "capital_health":
        return (
            f"Real portfolio P&L is {portfolio.total_pnl_pct:+.1f}% right now.",
            "No company-management lever — tracks the trading desk's own real performance directly.",
        )
    if key == "resource_usage":
        return (
            f"Agent energy is at {agent_energy.current:.0f} of a real {agent_energy.cap:.0f} cap.",
            "No direct lever — energy recovers as agents rest at real lobby/break-room locations.",
        )
    if key == "reputation":
        return (
            f"{len(hall_of_fame)} real Hall of Fame entries on record.",
            "No shortcut — earned only by real Hall-of-Fame-worthy trades or achievements.",
        )
    if key == "technology_level":
        return (
            f"Signal Calibration is at real level {signal_calibration.unlocked_level} of {SIGNAL_MAX_LEVEL}.",
            "Progress by unlocking further real Signal Calibration levels through continued use.",
        )
    if key == "market_coverage":
        added = max(0, len(watchlist) - len(SEED_SYMBOLS))
        return (
            f"{added} of {len(EXTRA_SYMBOL_POOL)} real extra symbols added to the watchlist beyond the 8 seed symbols.",
            "Add more real symbols to the watchlist to raise this score.",
        )
    if key == "education_progress":
        total = len(all_lessons())
        return (
            f"{len(education.completed_lesson_ids)} of {total} real Academy lessons completed; {education.correct_quiz_attempts} of {education.quiz_attempts} real quiz attempts correct.",
            "Complete more real Academy lessons and answer their quizzes correctly.",
        )
    if key == "team_chemistry":
        collab = _debate_collaboration_quality(debates)
        handoffs = _cross_agent_research_handoffs(research)
        if collab <= handoffs:
            return (
                f"Debate collaboration quality is {collab:.0f}/100 — recent real AI Debates skew toward challenge over support.",
                "No direct lever — reflects real debate tone as agents actually argue recent trade ideas.",
            )
        return (
            f"Cross-agent research handoffs are {handoffs:.0f}/100 — completed research isn't crossing between different agents.",
            "No direct lever — reflects whether agents are actually building on each other's real completed research.",
        )
    if key == "decision_quality":
        return (
            "Recent real Decision Grades are low, and/or diverge from the independent real Discipline Review filed for the same decision.",
            "No direct lever — reflects the real Decision Confidence Engine, analyst agreement, and Gatekeeper approval at each decision's own moment.",
        )
    if key == "executive_alignment":
        recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
        agreed = sum(1 for e in recent if e.network_agreed)
        return (
            f"The Executive Intelligence Network agreed on {agreed} of {len(recent)} recent real meetings.",
            "No direct lever — reflects real, substantive disagreement across recent Executive Meetings.",
        )
    if key == "risk_governance":
        return (
            f"{len(gatekeeper_rejections)} real proposals were rejected by the Gatekeeper against {len(portfolio.trade_history)} that actually closed.",
            "Review why proposals are failing real Gatekeeper checks — a high rejection share usually means weak setups are reaching the desk.",
        )
    if key == "simulation_coverage":
        return (
            "The Simulation Lab department hasn't offered a confident real opinion (vs. requesting more research) in recent Executive Meetings.",
            "Run more real Simulation Lab sessions so it has fresh evidence to weigh in with.",
        )
    if key == "department_consensus":
        return (
            "Recent real opposing votes in Executive Meetings lack a substantiating `concerns` entry.",
            "Ensure dissenting departments back their opposition with real, specific concerns rather than a bare no.",
        )
    if key == "self_evaluation_health":
        return (
            "Real weekly self-evaluation engagement is low, and/or the gap between initial Decision Grade and eventual trade outcome isn't narrowing over time.",
            "No direct lever — reflects real weekly self-evaluation participation and the organization's own prediction-calibration trend.",
        )
    if key == "institutional_memory":
        retention = _knowledge_retention(agent_knowledge)
        if wisdom_state.score <= retention:
            return (
                f"Real Wisdom score is {wisdom_state.score:.0f}/100 — the company's own weekly/monthly reflection factors are weak.",
                "No direct lever — reflects real reflection factors (learning from experience, documenting lessons, avoiding repeats).",
            )
        return (
            f"Only {retention:.0f}% of agents have reached the real top Mentor knowledge level.",
            "No direct lever — grows as agents accumulate real research/Academy/meeting points toward Mentor level.",
        )
    if key == "innovation_velocity":
        if not innovation_state and not strategies:
            return "No real Devil's Advocate challenges or Strategy Lab strategies exist yet.", "No action needed yet — becomes measurable once strategy work begins."
        parts = {
            "Devil's Advocate validation rigor": _validation_rigor(innovation_state),
            "Strategy Lab pipeline progress": _pipeline_progress(strategies),
            "deployed-strategy health trend": _measured_improvement(strategies, strategy_health_assessments),
        }
        weakest_label, weakest_value = min(parts.items(), key=lambda kv: kv[1])
        return (
            f"The weakest of three real pipeline signals is {weakest_label} at {weakest_value:.0f}/100.",
            "No direct lever — reflects real Devil's Advocate critique quality, how far strategies have advanced down the Strategy Lab pipeline, and deployed strategies' own health trend.",
        )
    if key == "talent_development":
        return (
            "Few agents have graduated real mentorship, and/or graduates' real post-graduation Discipline Scores are weak.",
            "Approve real mentorship graduations once earned, and review post-graduation Discipline Reviews trending weak.",
        )
    if key == "founder_oversight":
        return (
            f"{len(founder_council_sessions)} real Founder Council sessions on record, and/or recent ones fell back to \"nothing to review\" more often than not.",
            "Hold real Founder Council sessions regularly so they have current company activity to surface.",
        )
    if key == "compliance_health":
        return (
            f"{len(compliance_incidents)} real compliance incidents on record; resolution, remediation, and control-effectiveness evidence are currently weak.",
            "Resolve open real compliance incidents and address any confirmed recurring root causes.",
        )
    return "No specific real cause available for this metric.", "No specific action available."


def compute_company_health(
    *,
    agents: dict[AgentId, AgentState],
    research: list[ResearchItem],
    portfolio: PaperPortfolio,
    risk_warnings: list[RiskWarning],
    agent_energy: AgentEnergy,
    hall_of_fame: list[HallOfFameEntry],
    signal_calibration: SignalCalibrationState,
    watchlist: list[WatchlistEntry],
    education: EducationProgress,
    debates: list[Debate],
    decisions: list[TradeDecision],
    meeting_log: list[ExecutiveMeetingLogEntry],
    self_evaluations: list[DepartmentSelfEvaluation],
    wisdom_state: WisdomState,
    innovation_state: dict[AgentId, InnovationState],
    foundational_mentor_state: FoundationalMentorState,
    founder_council_sessions: list[FounderCouncilSession],
    gatekeeper_rejections: list[GatekeeperRejection],
    discipline_reviews: list[DisciplineReview],
    # CEO Company/Executive Health directive — Institutional Memory's
    # real knowledge-retention signal (see _knowledge_retention()).
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    # CEO Company/Executive Health directive — Innovation Velocity's real
    # pipeline-progress and measured-improvement signals (see
    # _pipeline_progress() / _measured_improvement()).
    strategies: list[Strategy],
    strategy_health_assessments: list[StrategyHealthAssessment],
    # CEO directive "Features 31-35," Feature 35 — Compliance Health's
    # real incident/remediation/control evidence (see
    # `_compliance_health()`). `current_sim_day` is the same real value
    # every other sim-day-aware consumer in this codebase already has in
    # scope (e.g. `is_overdue()`), needed so a fresh remediation isn't
    # judged before its real observation window has elapsed.
    compliance_incidents: list[ComplianceIncident],
    current_sim_day: int,
    # v0.7 Design Bible Chapter 63 — CEO-configurable tier thresholds
    # (RiskLimits.companyHealth*Threshold), defaulting to the exact
    # module constants above so existing behavior is unchanged until the
    # CEO adjusts them. Always passed together (see app/state.py's
    # update_risk_limits for the descending-order validation).
    excellent_threshold: float = 85.0,
    good_threshold: float = 70.0,
    stable_threshold: float = 50.0,
    needs_attention_threshold: float = 30.0,
) -> CompanyHealth:
    tier_thresholds: list[tuple[float, CompanyHealthTier]] = [
        (excellent_threshold, "excellent"),
        (good_threshold, "good"),
        (stable_threshold, "stable"),
        (needs_attention_threshold, "needs_attention"),
    ]
    metrics = {
        "operational_stability": _operational_stability(risk_warnings),
        "department_efficiency": _department_efficiency(agents),
        "employee_morale": _employee_morale(agents),
        "research_progress": _research_progress(research),
        "capital_health": _capital_health(portfolio),
        "resource_usage": _resource_usage(agent_energy),
        "reputation": _reputation(hall_of_fame),
        "technology_level": _technology_level(signal_calibration),
        "market_coverage": _market_coverage(watchlist),
        "education_progress": _education_progress(education),
        "team_chemistry": _team_chemistry(debates, research),
    }
    overall = sum(metrics.values()) / len(metrics)

    executive_metrics = {
        "decision_quality": _decision_quality(decisions, discipline_reviews),
        "executive_alignment": _executive_alignment(meeting_log),
        "risk_governance": _risk_governance(portfolio.trade_history, gatekeeper_rejections),
        "simulation_coverage": _simulation_coverage(meeting_log),
        "department_consensus": _department_consensus(meeting_log),
        "self_evaluation_health": _self_evaluation_health(self_evaluations, discipline_reviews),
        "institutional_memory": _institutional_memory(wisdom_state, agent_knowledge),
        "innovation_velocity": _innovation_velocity(innovation_state, strategies, strategy_health_assessments),
        "talent_development": _talent_development(foundational_mentor_state, discipline_reviews),
        "founder_oversight": _founder_oversight(founder_council_sessions),
        "compliance_health": _compliance_health(compliance_incidents, decisions, gatekeeper_rejections, current_sim_day),
    }
    executive_overall = sum(executive_metrics.values()) / len(executive_metrics)
    combined_overall = (overall + executive_overall) / 2.0

    # The two (or more, on a tie) weakest real sub-scores from EACH tier,
    # named in plain language — never generic filler. A company already
    # at 100 everywhere gets no recommendations at all, honestly.
    weakest_operational = sorted(metrics.items(), key=lambda kv: kv[1])[:2]
    weakest_executive = sorted(executive_metrics.items(), key=lambda kv: kv[1])[:2]
    recommendations = [f"{_METRIC_LABELS[name]} is low ({score:.0f}/100) — worth attention." for name, score in weakest_operational if score < 70.0]
    recommendations += [f"{_EXECUTIVE_METRIC_LABELS[name]} is low ({score:.0f}/100) — worth attention." for name, score in weakest_executive if score < 70.0]

    def _diagnose_one(name: str, score: float, label: str, group: Literal["operational", "executive"]) -> CompanyHealthWeakArea:
        cause, action = _diagnose(
            name,
            risk_warnings=risk_warnings,
            agents=agents,
            research=research,
            portfolio=portfolio,
            agent_energy=agent_energy,
            hall_of_fame=hall_of_fame,
            signal_calibration=signal_calibration,
            watchlist=watchlist,
            education=education,
            debates=debates,
            decisions=decisions,
            meeting_log=meeting_log,
            wisdom_state=wisdom_state,
            innovation_state=innovation_state,
            founder_council_sessions=founder_council_sessions,
            gatekeeper_rejections=gatekeeper_rejections,
            agent_knowledge=agent_knowledge,
            strategies=strategies,
            strategy_health_assessments=strategy_health_assessments,
            compliance_incidents=compliance_incidents,
        )
        return CompanyHealthWeakArea(
            metric=name,
            label=label,
            group=group,
            score=round(score, 1),
            severity=_tier(score, tier_thresholds),
            problem=f"{label} is low ({score:.0f}/100).",
            cause=cause,
            action=action,
        )

    weak_areas: list[CompanyHealthWeakArea] = [
        _diagnose_one(name, score, _METRIC_LABELS[name], "operational") for name, score in weakest_operational if score < 70.0
    ] + [_diagnose_one(name, score, _EXECUTIVE_METRIC_LABELS[name], "executive") for name, score in weakest_executive if score < 70.0]

    return CompanyHealth(
        overall=round(overall, 1),
        tier=_tier(overall, tier_thresholds),
        operationalStability=round(metrics["operational_stability"], 1),
        departmentEfficiency=round(metrics["department_efficiency"], 1),
        employeeMorale=round(metrics["employee_morale"], 1),
        researchProgress=round(metrics["research_progress"], 1),
        capitalHealth=round(metrics["capital_health"], 1),
        resourceUsage=round(metrics["resource_usage"], 1),
        reputation=round(metrics["reputation"], 1),
        technologyLevel=round(metrics["technology_level"], 1),
        marketCoverage=round(metrics["market_coverage"], 1),
        educationProgress=round(metrics["education_progress"], 1),
        teamChemistry=round(metrics["team_chemistry"], 1),
        recommendations=recommendations,
        weakAreas=weak_areas,
        updatedAt=_now_iso(),
        decisionQuality=round(executive_metrics["decision_quality"], 1),
        executiveAlignment=round(executive_metrics["executive_alignment"], 1),
        riskGovernance=round(executive_metrics["risk_governance"], 1),
        simulationCoverage=round(executive_metrics["simulation_coverage"], 1),
        departmentConsensus=round(executive_metrics["department_consensus"], 1),
        selfEvaluationHealth=round(executive_metrics["self_evaluation_health"], 1),
        institutionalMemory=round(executive_metrics["institutional_memory"], 1),
        innovationVelocity=round(executive_metrics["innovation_velocity"], 1),
        talentDevelopment=round(executive_metrics["talent_development"], 1),
        founderOversight=round(executive_metrics["founder_oversight"], 1),
        complianceHealth=round(executive_metrics["compliance_health"], 1),
        executiveOverall=round(executive_overall, 1),
        executiveTier=_tier(executive_overall, tier_thresholds),
        combinedOverall=round(combined_overall, 1),
        combinedTier=_tier(combined_overall, tier_thresholds),
    )


# CEO Company Health + Live Market Realism directive, Section 6 — the
# explicit before/after delta breakdown the CEO asked to see (e.g. "+2.4
# Decision Quality, -0.8 Efficiency..."), computed as a pure diff between
# two already-real CompanyHealth readings this module already produces —
# no new telemetry, no invented "reason"/"evidence" text (the only honest
# source for either would be re-deriving which of the many real inputs
# changed, which this function doesn't attempt; see CompanyHealthDelta's
# own schema docstring). Only components whose score actually moved make
# it into the list, sorted by magnitude (largest real movement first) so
# a tick where nothing changed reports an empty list rather than
# twenty-one honest zeroes.
def diff_company_health(previous: CompanyHealth | None, current: CompanyHealth) -> CompanyHealthDelta | None:
    if previous is None:
        return None

    components: list[CompanyHealthComponentDelta] = []
    for key, label in _METRIC_LABELS.items():
        prev_value = getattr(previous, key)
        curr_value = getattr(current, key)
        delta = round(curr_value - prev_value, 1)
        if delta != 0.0:
            components.append(
                CompanyHealthComponentDelta(key=key, label=label, group="operational", previous=prev_value, current=curr_value, delta=delta)
            )
    for key, label in _EXECUTIVE_METRIC_LABELS.items():
        prev_value = getattr(previous, key)
        curr_value = getattr(current, key)
        delta = round(curr_value - prev_value, 1)
        if delta != 0.0:
            components.append(
                CompanyHealthComponentDelta(key=key, label=label, group="executive", previous=prev_value, current=curr_value, delta=delta)
            )
    components.sort(key=lambda c: abs(c.delta), reverse=True)

    return CompanyHealthDelta(
        previousUpdatedAt=previous.updated_at,
        currentUpdatedAt=current.updated_at,
        overallDelta=round(current.overall - previous.overall, 1),
        executiveOverallDelta=round(current.executive_overall - previous.executive_overall, 1),
        combinedOverallDelta=round(current.combined_overall - previous.combined_overall, 1),
        tierChanged=current.tier != previous.tier,
        executiveTierChanged=current.executive_tier != previous.executive_tier,
        combinedTierChanged=current.combined_tier != previous.combined_tier,
        components=components,
    )
