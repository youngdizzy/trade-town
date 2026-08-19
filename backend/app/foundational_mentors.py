"""The Foundational Mentor Program / Professional Academy (v0.7 Feature
49, Phase 3, revised) — an expandable, CEO-facing library of named
"tracks", each modeled on a real, respected trading educator's real,
publicly-known area of expertise, worked through as a sequential
lesson-and-quiz curriculum.

EMPLOYEES ARE THE STUDENTS. This module was originally built with the
CEO as the one taking lessons and quizzes; that was inverted per an
explicit CEO revision request. TradeTown is a company management sim —
the player is the CEO, the employees are the staff — so requiring the
CEO to personally click through lessons/quizzes to make company
progress happen was the wrong model. Now: `STUDENT_AGENT_IDS` (the real
employee roster below) auto-progress through the company's one
currently-active mentor track every real tick (`tick_employee_progress`),
the same honest "progress climbs each tick, no LLM content generation"
convention `app/academy_research.py`'s AcademyProject already
established. The CEO manages (reviews progress, approves graduations,
pauses/resumes/skips/repeats company-wide training) rather than
performs the work. `ceo_progress` on `FoundationalMentorState` is an
entirely separate, always-optional bucket for a CEO who personally
wants to take the same lessons (`Settings.ceoAcademyLearningMode`,
default off) — this never gates or is required for real company
progress; see `mark_ceo_lesson_viewed`/`grade_ceo_lesson_quiz` below.

STUDENT ROSTER: `STUDENT_AGENT_IDS` = scout, atlas, echo, nova, scribe,
sentinel, pulse, guardian — the same 8-of-9 roster
`app/academy_research.py`'s `ACADEMY_RESEARCHER_IDS` already uses for
its own company-wide Academy project rotation, minus Coach. Coach is
explicitly the teacher/monitor in this revision's own brief ("The Coach
automatically monitors every employee"), not a trainee, so unlike
academy_research.py's rotation (which predates this feature and still
includes Coach for its own unrelated purpose) Coach is excluded here.
CIO (oversees rather than trades — the same reasoning
academy_research.py already applies to excluding the CIO from its own
researcher rotation) and Quant (a senior reviewer role — the brief's own
"Quant Approval" and "Legendary Quant [becomes] a Foundational Mentor"
language casts Quant as a reviewer/future-teacher, not a trainee) are
excluded for the same kind of reason. Sage (an existing mentor/advisor
role) and Keystone/Compass (retired Founders — see app/founders.py) are
excluded as already-established non-trainee roles.

CONTENT ATTRIBUTION BOUNDARY (unchanged from the original build, read
this before adding or editing a lesson): this codebase has no HTTP
client, no PDF/video parser, and no LLM call anywhere (confirmed by grep
across the whole backend, consistent with the precedent already
established in app/education.py and Feature 40's own module docstring)
— so TradeTown has no mechanism to actually watch, read, or otherwise
ingest any real person's real video, book, or article content. A real
educator's name is used ONLY as a CEO-assigned track label naming the
real subject area their track covers. Every lesson's actual teaching
content below is 100% original TradeTown-authored material on that same
subject, never a transcription, summary, paraphrase, or quote of that
person's actual published work. `_CONTENT_DISCLAIMER` states this
explicitly on every mentor profile.

WHAT'S REAL VS. ROADMAP: five of the seven roadmap tracks ship real
lesson content — "tjr" (8 original lessons, `_TJR_LESSONS`, expanded
from the original 6 to match this revision's wider TJR focus-area
list), "market_intelligence" (23 lessons, `_MARKET_INTELLIGENCE_LESSONS`
— the original 8 from v0.7 Feature 51, 7 more from the CEO directive
"Session Trading Education & Agent Training" (orders 9-15), and 8 more
from the CEO directive "Market-Analysis Knowledge + Session Intelligence
Expansion" (orders 16-23) — not credited to any real external educator),
"al_brooks" (8 lessons, `_AL_BROOKS_LESSONS`, added by that same
"Market-Analysis Knowledge + Session Intelligence Expansion" directive,
Phases 1-2 — the track's first real content since the original build),
and — Trading Psychology & Discipline, Piece F — "mark_douglas" and
"linda_raschke" (2 lessons each, `_MARK_DOUGLAS_LESSONS`/
`_LINDA_RASCHKE_LESSONS`, deliberately a small honest start rather than
backfilling to match TJR's 8). The remaining two named tracks
(tom_hougaard, mike_bellafiore) are seeded as real, ordered, named
roadmap entries — real display name, real track label, real focus-area
topics — but deliberately ship with zero lessons and `status: "planned"`
rather than fabricated placeholder shells. `_LESSON_SPECS_BY_MENTOR` is
exactly where a future track's real content gets added.

AUTO-GRADED QUIZZES — the honest signal behind them. An employee's real
`quiz_options`/`correct_index` content still exists (and is still used
for the CEO's own optional personal quiz-taking, graded exactly as
before). For an employee's own automatic pass/fail, there is no picked
option to grade — inventing a fabricated "the employee selected option
C" would be dishonest. Instead each employee's real pass probability is
tied to `_agent_aptitude()`: their own real average `DisciplineReview`
score across every review they attended (the same real per-agent signal
`app/mentor.py`'s ThinkingProfile already treats as a legitimate
aptitude proxy), clamped to a floor/ceiling so no employee is
deterministically guaranteed or barred. This is honestly a real,
per-agent-varying pass chance grounded in the agent's own trade-decision
history — not a fabricated understanding score.

GRADUATION QUEUE — the real "Approve Graduation" gate. When an employee
completes every lesson (all correctly quizzed), their
`graduation_status` becomes `"pending_approval"`, not immediately
`"graduated"` — matching the brief's own "CEO Responsibilities: Approve
Graduation" and "Graduation Queue" dashboard section. Only
`approve_graduation()` (a real CEO action) advances it to `"graduated"`.
Once every student in `STUDENT_AGENT_IDS` has an approved graduation on
the currently-active mentor, the company as a whole graduates that
track (`company_graduated_sim_day`) and the next roadmap entry unlocks
— "mastery before progression," per the brief.

CERTIFICATION MANAGEMENT — a quality-of-life fix over the original
"Approve Graduation only" gate: once a certification appears in Current
Certifications, the CEO can View it, Revoke it (with a required reason,
returning the employee to the track — see `revoke_certification`),
Downgrade/Promote its standing (Active <-> Suspended — a real,
reversible demotion short of full revocation, since no tiered
Bronze/Silver/Gold concept exists anywhere in this codebase to
"downgrade"/"promote" a performance level against), Reset Progress
(only on an already-revoked certification, wiping any renewed re-
training headway), and View its full permanent History. See the
"Certification Management" section below (`CertificationRecord` in
schemas.py is the new, independent, permanent registry this all reads
and writes — never derived from `FoundationalMentorProgress`, which a
revoke genuinely resets).

MENTOR LAB REVISION — real, in-product mentor/lesson authoring is now
built (`add_custom_mentor`, `add_custom_lesson`, `set_active_mentor`),
no longer a code-only scope cut. `FoundationalMentorId` changed from a
fixed `Literal` to a plain `str` and the sequential roadmap order moved
from a module constant (`_ROADMAP_ORDER`) to real persisted state
(`FoundationalMentorState.roadmap_order`) specifically so a CEO-added
mentor really does come up for company-wide study in its turn, the same
as the original 6. `set_active_mentor` additionally lets the CEO jump
straight to any mentor with real content — built-in or custom — without
waiting for the automatic unlock, when they want to prioritize it now.

EXPLICIT SCOPE CUTS, checked against both revision briefs and NOT built:
  - Assigning individual books/videos/PDFs/research papers/journals/
    practical exercises/backtesting/paper trading to a SPECIFIC
    employee: no per-employee assignment plumbing to those other real
    systems exists. The one real "assignment" mechanic that exists —
    bookmarked external resources (`FoundationalMentorResource`) — stays
    company-wide per mentor track, same as before.
  - The brief's full "Mentor Validation" pipeline (every concept
    Discussed → Backtested → Paper Traded → Sandbox Tested → Quant
    Reviewed → Risk Reviewed → Devil's Advocate Reviewed → Founder
    Council Reviewed → becomes Company Knowledge/Operating System/
    Constitution/Playbooks): this would mean building an entirely new
    cross-cutting approval-workflow engine touching six-plus existing
    systems. Graduation stays gated on the real, checkable
    lessons-plus-quiz signal only — the same honesty boundary
    `app/sandbox.py`'s own docstring already documents (no mechanism
    exists anywhere in this codebase to attribute a validated "concept"
    to a specific later trade).
  - "Quant Approval" as a literal second graduation gate — no real
    per-lesson Quant review signal exists to check against; CEO Approval
    is the one real gate.
  - Coach recommendation types with no real backing signal yet: Extra
    Reading, Extra Backtesting, Reflection Session, Research Assignment,
    Paper Trading Practice. Only "Repeat Lesson" and "One-on-One
    Coaching" are computed here, both driven by the real
    `consecutive_quiz_failures` counter — see `COACH_ESCALATION_THRESHOLD`.
  - CEO Daily Settings additions from the revision brief (Trading
    Sessions, Allowed Strategies): `RiskLimits` doesn't have these
    fields; a real, separate follow-up to Feature 49 Phase 1, not built
    here.
  - Post-halt automatic activity redirection (employees demonstrably
    switching to study/research/backtest/journal once the Daily Trading
    Objective halts trading): a real behavioral change to
    `schedule.py`/`nexus.py`'s task-assignment logic, large and
    orthogonal to this module — not built here.
  - "Growth" metrics (Knowledge/Discipline/Research Growth as deltas
    over time): no snapshot-history mechanism exists for these composite
    scores. The Academy Dashboard (frontend `lib/derive.ts`) shows real
    CURRENT aggregate values instead, explicitly relabeled rather than
    faking a trend.
  - TradeTown's own retired Founders/Coach/Quant becoming Foundational
    Mentors themselves: explicitly framed in the brief as a "long term
    goal," not this pass.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas import (
    AgentId,
    CertificationHistoryEntry,
    CertificationRecord,
    DisciplineReview,
    FoundationalMentorId,
    FoundationalMentorLesson,
    FoundationalMentorProfile,
    FoundationalMentorProgress,
    FoundationalMentorResource,
    FoundationalMentorState,
    FoundationalResourceType,
)

MAX_RESOURCES_PER_MENTOR = 20
MAX_CUSTOM_MENTORS = 20
MAX_LESSONS_PER_MENTOR = 30

_CUSTOM_CONTENT_NOTE = (
    "This track was added directly by the CEO. Its content is entirely CEO-authored — TradeTown has no ability to "
    "ingest external content for it either (no HTTP client or content-parsing exists anywhere in this codebase, "
    "the same boundary the original named tracks are built around)."
)

# See module docstring's "STUDENT ROSTER" section for the full reasoning.
STUDENT_AGENT_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova", "scribe", "sentinel", "pulse", "guardian")

# Mirrors academy_research.py's PROGRESS_GAIN_RANGE=(1.5, 4.0) pacing —
# real per-tick progress toward the employee's current in-flight lesson.
STUDY_GAIN_RANGE = (2.0, 5.0)
# A failed quiz doesn't erase all study progress — it lands the employee
# back at a partial "repeat the lesson" point rather than starting over,
# an honest middle ground between "no penalty" and "fully punishing."
FAILURE_STUDY_RESET_PCT = 50.0
# Clamped so no employee's real aptitude signal ever reads as a
# deterministic guaranteed pass or guaranteed fail.
MIN_QUIZ_PASS_PROBABILITY = 0.35
MAX_QUIZ_PASS_PROBABILITY = 0.90
# 3+ consecutive quiz failures escalates the Coach's recommendation from
# "Repeat Lesson" to "One-on-One Coaching" — see module docstring.
COACH_ESCALATION_THRESHOLD = 3

_CONTENT_DISCLAIMER = (
    "This track's name credits a real, respected trading educator whose stated area of expertise inspired it. "
    "TradeTown has no ability to watch, read, or otherwise ingest real external video, book, or article content "
    "(no HTTP client or content-parsing exists anywhere in this codebase) — every lesson below is original "
    "TradeTown-authored teaching material on that same subject area, never a transcription, summary, or quote of "
    "that person's actual work."
)

# v0.7 Feature 51 — the Market Intelligence Department's own Academy
# track. Deliberately NOT the same _CONTENT_DISCLAIMER as the six tracks
# above: this one credits no real external educator at all — it teaches
# the real mechanics of TradeTown's own in-house department
# (app/market_intelligence.py), so the honest content note is different.
_MARKET_INTELLIGENCE_CONTENT_NOTE = (
    "This track is not credited to any real external trading educator. It teaches the real, checkable mechanics "
    "behind TradeTown's own in-house Market Intelligence Department (app/market_intelligence.py) — every lesson "
    "below cites a specific real formula or signal that module actually computes, including where it's an honest "
    "proxy for something this codebase has no real data source for (see that module's own docstring)."
)

_ROADMAP_ORDER: tuple[FoundationalMentorId, ...] = (
    "tjr",
    "al_brooks",
    "linda_raschke",
    "mark_douglas",
    "tom_hougaard",
    "mike_bellafiore",
    "market_intelligence",
)

_ROADMAP_FOCUS: dict[FoundationalMentorId, tuple[str, list[str]]] = {
    "tjr": (
        "TJR",
        ["Trading Psychology", "Discipline", "Daily Routine", "Liquidity", "Market Structure", "Patience", "Risk Management", "Journaling", "Trade Planning", "High Quality Trade Selection"],
    ),
    "al_brooks": ("Al Brooks", ["Price Action", "Candlestick Reading", "Market Structure", "Breakouts", "Trading Ranges", "Probability"]),
    "linda_raschke": ("Linda Raschke", ["Professional Process", "Risk Management", "Trade Management", "Preparation", "Execution", "Professional Consistency"]),
    "mark_douglas": ("Mark Douglas", ["Psychology", "Consistency", "Probability", "Confidence", "Emotional Control", "Mindset"]),
    "tom_hougaard": ("Tom Hougaard", ["Professional Execution", "Mental Toughness", "Performance Under Pressure", "Confidence", "Elite Mindset"]),
    "mike_bellafiore": ("Mike Bellafiore", ["Building Elite Traders", "Performance Reviews", "Journaling", "Practice", "Trading Team Development", "Continuous Improvement"]),
    "market_intelligence": (
        "Market Intelligence Department",
        ["Market Structure", "Liquidity", "Trend Analysis", "Institutional Behavior", "Session Characteristics", "Volatility", "Market Regimes", "Probability Thinking", "Risk Context"],
    ),
}


@dataclass(frozen=True)
class _LessonSpec:
    id: str
    order: int
    title: str
    simple_explanation: str
    deeper_explanation: str
    quiz_question: str
    quiz_options: tuple[str, str, str, str]
    correct_index: int


_TJR_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="tjr-psychology",
        order=1,
        title="Trading Psychology: Process Over Outcome",
        simple_explanation="A single trade's outcome is mostly noise — even a well-planned, well-executed trade loses sometimes. Judging yourself by whether one trade won or lost, instead of whether you followed your process, is the single most common psychological trap in trading.",
        deeper_explanation="TradeTown's own Discipline Score (app/discipline.py) is built around exactly this idea: it never reads a trade's P&L. It scores real, checkable process signals instead — stop-loss discipline, position sizing, patience, and following the Gatekeeper's approval — so a losing trade with a strong process still earns a strong Discipline Score, and a winning trade with a sloppy process doesn't.",
        quiz_question="An agent takes a properly-sized, stop-loss-protected trade that the Gatekeeper approved, and it still loses money. What does TradeTown's Discipline Score do?",
        quiz_options=(
            "It stays high — Discipline Score never reads trade P&L",
            "It drops sharply because the trade lost",
            "It's deleted since the trade failed",
            "It's replaced by the trade's dollar loss",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-daily-routine",
        order=2,
        title="Building a Daily Routine",
        simple_explanation="A consistent pre-market routine — reviewing the plan, checking risk limits, confirming what setups you're looking for — reduces how many decisions you have to make in the heat of the moment, which is when trading mistakes are most likely.",
        deeper_explanation="This lesson is honestly conceptual: TradeTown's own app/schedule.py governs when an agent is available to trade (a workday/off-hours mechanic), which is a different concept from a pre-market mental routine — there's no real 'ritual' system here to point at as an example. The real, actionable version of this lesson is the CEO's own Daily Trading Objectives (Command Center → RISK tab) — reviewing today's profit target, max loss, and trade count limit before the day starts is a real routine step this codebase actually supports.",
        quiz_question="Why does having a routine reduce trading mistakes, according to this lesson?",
        quiz_options=(
            "It cuts down on in-the-moment decisions made under pressure",
            "It guarantees every trade will be profitable",
            "It removes the need for stop losses",
            "It replaces the need for a trading plan",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-liquidity-market-structure",
        order=3,
        title="Liquidity and Market Structure",
        simple_explanation="Price often moves toward pools of resting orders (liquidity) before reversing — clusters of stops above old highs or below old lows. Understanding where that liquidity likely sits helps explain moves that otherwise look random.",
        deeper_explanation="This is the same real, honestly-scoped ground app/education.py's own 8-lesson Liquidity module (orders 11-18) already covers in depth — see that module's own docstring for exactly which pieces have a real TradeTown analog (the What-If Simulation Lab's Liquidity Sweep scenario, the Scanner's volume-confirmed breakout) and which are honestly conceptual (no real order-book data exists in this codebase). This lesson doesn't repeat that whole curriculum — it points a professional trader's own daily practice at it.",
        quiz_question="Why does TradeTown's liquidity curriculum explicitly disclaim some concepts rather than claiming to detect them?",
        quiz_options=(
            "Because this codebase has no real order-book or bid/ask data to detect them from",
            "Because liquidity concepts aren't useful for trading",
            "Because the Scanner already detects every liquidity concept perfectly",
            "Because only CEO-level users are allowed to see liquidity data",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-patience",
        order=4,
        title="Patience as a Skill",
        simple_explanation="Patience in trading isn't just 'waiting for a good setup' — it also means giving a position room to work once you're in it, instead of closing it out of nerves the moment it moves against you slightly.",
        deeper_explanation="TradeTown's Discipline Score has a real Patience factor (app/discipline.py's PATIENCE_TARGET_MINUTES, currently 240 simulated minutes): a position held at or past that target scores well on patience, one closed out early scores lower. That's a real, measured signal, not a vibe — you can check any agent's real hold durations against it.",
        quiz_question="What does TradeTown's real Patience factor actually measure?",
        quiz_options=(
            "How long a position was actually held versus a real target duration",
            "How many trades an agent avoided taking",
            "How much money a position made",
            "How many minutes the agent spent thinking before entering",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-risk-management",
        order=5,
        title="Risk Management Fundamentals",
        simple_explanation="Professional traders size every position around a fixed real risk-per-trade percentage, not a gut feeling — the position size is a consequence of the stop distance and the risk budget, never the other way around.",
        deeper_explanation="This is exactly what app/risk_engine.py's recommended_quantity() computes: a real formula using RiskLimits.riskPerTradePct, account equity, and the trade's own stop distance — the same real number the Gatekeeper checks every proposal against, and the same one the Daily Trading Objectives (RiskLimits.maxDailyLossPct/maxTradesPerDay) build on top of.",
        quiz_question="In TradeTown, what actually determines a trade's position size?",
        quiz_options=(
            "A real formula using risk-per-trade percentage, account equity, and stop distance",
            "Whatever amount feels right for that trade",
            "Always the maximum the account can afford",
            "A fixed number of shares for every trade",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-journaling",
        order=6,
        title="Trade Planning & Journaling",
        simple_explanation="Writing down why you took a trade, what you expected, and what actually happened turns a single trade into a reusable lesson — without a journal, you're relying on memory, which quietly rewrites itself to make you look better or worse than you were.",
        deeper_explanation="TradeTown's real Trading Journal (app/journal.py) auto-fills a coach review and lessons-learned entry for every closed trade, tied to the exact TradeDecision that approved it. Its `screenshot` field is honestly a fixed placeholder string, not a real chart image — there's no chart-rendering pipeline in this codebase to generate one, and journal.py's own docstring says so directly rather than faking an image.",
        quiz_question="Why is the Trading Journal's `screenshot` field just a placeholder string?",
        quiz_options=(
            "Because there's no real chart-rendering pipeline to generate an actual image, and the code says so honestly",
            "Because screenshots are considered unimportant",
            "Because it's a bug that was never fixed",
            "Because it's a real image that's just compressed",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-trade-selection",
        order=7,
        title="High-Quality Trade Selection",
        simple_explanation="Not every setup that looks interesting is worth taking. Professional traders filter aggressively — most potential trades get passed on, and that's the system working, not a missed opportunity.",
        deeper_explanation="TradeTown has two real filters that do exactly this: the Gatekeeper (app/gatekeeper.py) blocks a proposal outright on confidence, risk-manager veto, debate disagreement, exposure, correlation, or an active risk warning; and the Daily Trading Objectives (app/risk_engine.py) halt new trades for the rest of the day once the daily loss limit, profit target, or trade-count cap is hit. Both are real, visible rejections in the Command Center — not bugs.",
        quiz_question="A trade proposal gets blocked by the Gatekeeper. What does that mean?",
        quiz_options=(
            "The filter is working as intended — a real check caught a real problem with the trade",
            "The system has a bug and needs to be restarted",
            "The agent is being punished unfairly",
            "The trade will be automatically resubmitted with different numbers",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="tjr-consistency",
        order=8,
        title="Emotional Control & Consistency",
        simple_explanation="Consistency means trading the same process on your best day and your worst day. It's less about never feeling anything and more about not letting how you feel change what you do.",
        deeper_explanation="TradeTown honestly can't read literal emotion — there's no sentiment or mood signal anywhere in this codebase. The closest real, checkable analogs are the Discipline Score's tier stability over time (app/discipline.py) and the company-wide Wisdom Score (app/wisdom.py), both of which measure real behavioral consistency from real trade and review history, rather than inventing a fabricated 'mood' number.",
        quiz_question="How does TradeTown honestly approach measuring 'emotional control'?",
        quiz_options=(
            "By measuring real behavioral consistency (Discipline tier stability, Wisdom Score) instead of fabricating an emotion reading",
            "By running a sentiment-analysis model on agent dialogue",
            "By asking the agent directly how it feels",
            "It doesn't attempt to measure this at all, silently",
        ),
        correct_index=0,
    ),
)

# Trading Psychology & Discipline, Piece F — the first real content for
# two of the five previously-empty roadmap tracks (see module docstring's
# "WHAT'S REAL VS. ROADMAP"). Same content-attribution boundary as
# _TJR_LESSONS: "Mark Douglas" names the real subject area (trading
# psychology, probability-based thinking) this track covers, never a
# transcription of his actual published work. Deliberately a small,
# honest 2-lesson start rather than backfilling to match TJR's 8 — each
# lesson below cites a specific real mechanic this codebase already
# computes for reasons unrelated to the Academy, the same "cite, don't
# fabricate" rule every other track's lessons already follow, and covers
# real ground the existing TJR/Market Intelligence tracks don't already
# teach (TJR's own lesson 1 is process-over-outcome; these two instead
# cover the Decision Confidence Engine's probability framing and the
# Behavioral Circuit Breaker's revenge-trading detection specifically).
_MARK_DOUGLAS_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="md-probability",
        order=1,
        title="Probability, Not Prediction",
        simple_explanation="A professional trader doesn't try to know what happens next — no one can. What separates a professional from a gambler is thinking in probabilities: how strong is this specific setup's evidence, right now, compared to setups like it historically? That question has a real answer. 'Will this trade win?' does not.",
        deeper_explanation="app/confidence.py's Decision Confidence Engine is built around this exact distinction — its own module docstring states it directly: 'Never predicts whether a trade will win. It scores the quality of the evidence behind the current setup.' compute_confidence() produces a real 0-100 score from six real, weighted factors (multi-agent agreement, technical alignment, risk conditions, research confidence, sentiment, portfolio exposure) and tier_for_score() bands it into a real confidence tier — never a win/loss forecast. This isn't just one module's convention: app/probability_language.py is a real, automated regression test that scans every generated trade thesis, review, and case study in this codebase for absolute-certainty phrasing and fails if any appears — probability-first framing is enforced, not just encouraged.",
        quiz_question="What does TradeTown's Decision Confidence Engine actually score?",
        quiz_options=(
            "The quality of the evidence behind a setup right now — never a prediction of whether the trade wins",
            "The exact probability the trade will win, computed from historical odds",
            "The CEO's own personal gut feeling about the trade",
            "A guaranteed pass/fail grade on the trade's eventual outcome",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="md-revenge-trading",
        order=2,
        title="Recognizing Revenge Trading",
        simple_explanation="After a loss, the urge to immediately win it back — bigger, faster, on the same instrument that just burned you — is one of the most damaging and most human patterns in trading. The danger isn't feeling that urge; everyone does. The danger is acting on it without noticing.",
        deeper_explanation="app/behavioral_risk.py's Behavioral Circuit Breaker is a real, checkable detector for exactly this pattern, built as the Trade Gatekeeper's own tenth check. It never claims to read emotion — it only checks real, observable facts: did the account just lose (trade_history[-1].pnl < 0), is this new proposal arriving inside a real post-loss cooldown window, and does it corroborate that timing with a real warning sign (the same instrument that just lost, or a position sized well above this account's own recent normal). Timing alone is deliberately never enough to block a trade — compute_behavioral_check() only reaches 'triggered' when timing is corroborated by at least one of those real signals, so a legitimate, differently-sized setup on a different instrument minutes after a loss is never punished for bad timing alone.",
        quiz_question="What has to be true for TradeTown's Behavioral Circuit Breaker to actually block a trade (not just warn)?",
        quiz_options=(
            "Rapid post-loss timing corroborated by a real signal — same instrument as the loss, or a loss-driven size increase — not timing alone",
            "Any trade proposed within an hour of any loss, regardless of instrument or size",
            "The CEO manually flagging the trade as emotional",
            "A sentiment-analysis read of the agent's dialogue",
        ),
        correct_index=0,
    ),
)

# Trading Psychology & Discipline, Piece F — the first real content for
# the linda_raschke roadmap track, the same small, honest 2-lesson start
# and content-attribution boundary as _MARK_DOUGLAS_LESSONS above. Covers
# real ground neither TJR nor Market Intelligence already teaches: the
# Trade Gatekeeper's own full pre-trade checklist, and the risk-engine
# math behind position sizing.
_LINDA_RASCHKE_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="lr-gatekeeper-checklist",
        order=1,
        title="The Trade Gatekeeper: A Real Pre-Trade Checklist",
        simple_explanation="Professional preparation means having a real, consistent checklist a trade idea has to clear before it becomes a live position — not a fresh judgment call every time. A trade that skips the checklist because 'this one feels different' is exactly how process discipline erodes.",
        deeper_explanation="app/gatekeeper.py's evaluate_gatekeeper() is TradeTown's own real, disclosed pre-trade checklist: ten independent checks (decision confidence, risk-manager alignment, multi-agent agreement, the AI Debate's outcome, portfolio exposure, correlated positions, active risk warnings, market conditions, the weighted executive recommendation, and the Behavioral Circuit Breaker) run on every single proposal. `approved = all(c.passed for c in checks)` — a pure AND across all ten; there is no override, no partial credit, and no way for one strong check to compensate for a failed one. A rejected proposal is recorded as a real, auditable GatekeeperRejection naming exactly which check(s) failed, so the reason a trade didn't happen is never a mystery.",
        quiz_question="How does TradeTown's Trade Gatekeeper combine its ten real checks into an approve/reject decision?",
        quiz_options=(
            "A pure AND across all ten — every check must pass, and no strong check can offset a failed one",
            "A majority vote — six of ten checks passing is enough to approve",
            "Only the Risk Manager's own check actually matters; the other nine are informational",
            "The CEO manually overrides the checklist on a case-by-case basis",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="lr-position-sizing",
        order=2,
        title="Position Sizing Is Risk Management",
        simple_explanation="The single most controllable risk decision in trading isn't picking the right setup — it's deciding how much to risk on it. A great setup sized too large can still do lasting damage; a mediocre setup sized correctly rarely does.",
        deeper_explanation="app/risk_engine.py's recommended_quantity() sizes every new position from two real, independent limits at once: risk_budget (equity times the CEO's own configured risk_per_trade_pct) and position_cap (equity times max_position_pct) — and always takes the smaller of the two, never the larger. That min() rule is deliberate: it means tightening either limit alone is enough to shrink every future position size, without needing to touch the other, so the CEO always has two real, independent levers rather than one that can be bypassed by the other.",
        quiz_question="When TradeTown's risk engine sizes a new position, which of its two real caps (risk-per-trade budget, max-position cap) actually governs the trade?",
        quiz_options=(
            "Whichever of the two produces the SMALLER position size — the tighter limit is the one that actually governs",
            "Whichever of the two produces the LARGER position size — the looser limit is the one that actually governs",
            "Only the risk-per-trade budget; max-position cap is display-only",
            "Neither — position size is chosen at random within a range",
        ),
        correct_index=0,
    ),
)

# CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
# Session Intelligence Expansion," Phases 1-2 — al_brooks's first real
# content, filling a roadmap slot that shipped with zero lessons since
# the original build (see this module's docstring). Deliberately
# non-duplicative of mi-structure/mi-liquidity (market structure and
# liquidity are already taught there): this track focuses on the real
# candlestick/breakout/reversal detection app/technical_patterns.py adds
# for this same directive, plus the classical chart-pattern concepts
# (triangles, double tops, head & shoulders) that codebase has no
# auto-detector for — each such lesson says so honestly rather than
# implying one exists.
_AL_BROOKS_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="ab-price-action-basics",
        order=1,
        title="Price Action: Reading The Candles Themselves",
        simple_explanation="Price action means judging a market primarily from its own real candles — their size, direction, and shape — rather than from an indicator derived from them. It's the most direct evidence a chart offers, and the foundation every other framework in this track builds on.",
        deeper_explanation="TradeTown's real candlestick detection (app/technical_patterns.py's detect_candlestick_patterns()) is a direct price-action read: engulfing candles, hammers, shooting stars, and dojis are all judged purely from a candle's own open/high/low/close, with no indicator in between. This track and the Market Intelligence Department's track are complementary, not duplicates: Market Intelligence's mi-structure lesson already covers swing highs/lows and Break of Structure — this track picks up from there with candle-level reading, breakout behavior, and reversal recognition.",
        quiz_question="What does 'price action' mean in TradeTown's real implementation?",
        quiz_options=(
            "Judging the market from a candle's own real open/high/low/close data directly, not from a derived indicator",
            "Only ever looking at RSI",
            "A random label with no real technique behind it",
            "Trading based solely on news headlines",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-candlestick-signals",
        order=2,
        title="Candlestick Signals: Engulfing, Hammer, Shooting Star, Doji",
        simple_explanation="Four real, standard candle shapes are worth knowing cold: an engulfing candle whose real body covers the prior candle's body, a hammer's long lower wick rejecting a low, a shooting star's long upper wick rejecting a high, and a doji's tiny body showing real indecision.",
        deeper_explanation="app/technical_patterns.py's detect_candlestick_patterns() checks each against its own exact geometric rule: bullish/bearish engulfing (one candle's real body fully covers the prior candle's real body, opposite direction), hammer/shooting_star (a small body positioned near one end of the range with a long opposite wick, checked BEFORE the doji rule so a real hammer is never misread as a doji), and doji (body under 10% of the candle's own real range). None of these are a prediction — each names a real shape that already happened.",
        quiz_question="Why does TradeTown check hammer and shooting_star BEFORE doji in its real detection order?",
        quiz_options=(
            "Because a long-wick, small-body candle would otherwise also satisfy doji's broader small-body rule and be misclassified",
            "Alphabetical order",
            "It doesn't matter — order is irrelevant",
            "Because doji is checked first in every other system",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-breakouts-and-confirmation",
        order=3,
        title="Breakouts: Consolidation Into Expansion",
        simple_explanation="A breakout is a real move out of a consolidation range — but the move alone doesn't confirm anything. A real close beyond the range, ideally on real expanded range/volume, is stronger evidence than a single wick poking through.",
        deeper_explanation="TradeTown's real session-range tracking (app/technical_patterns.py's compute_session_range()) already gives a real, checkable range boundary (a session's own real high/low) and a real retested flag showing whether a later candle actually traded back into that range — the honest building block for judging whether a breakout held or immediately failed. TradeTown does not auto-classify a move as a 'confirmed breakout'; that judgment stays a real evidence-gathering step, not an automated label.",
        quiz_question="What real, existing TradeTown data helps judge whether a breakout out of a session's range actually held?",
        quiz_options=(
            "compute_session_range()'s real high/low and its real retested flag showing whether price traded back into the range",
            "A coin flip",
            "The CEO's gut feeling alone",
            "Nothing — breakouts are untracked",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-false-breakouts-and-retests",
        order=4,
        title="False Breakouts & Retests",
        simple_explanation="Not every breakout continues — a false breakout reverses back into the range shortly after, often trapping traders who entered on the initial move. A retest (price returning to the broken level before continuing) is a real, different, and generally healthier pattern.",
        deeper_explanation="This is a real, honest evidence question, not an assumption: does this specific setup, in this specific session and regime, actually tend to hold or fail after breaking a range? app/session_evidence.py's compute_session_regime_evidence() is exactly the mechanism that answers a version of this question from TradeTown's own real closed-trade history, honestly reporting NOT_ENOUGH_EVIDENCE rather than guessing when the sample is too thin — the same discipline this directive requires for every session-behavior claim.",
        quiz_question="How should a claim like 'this setup usually fails after a London breakout' be treated in TradeTown?",
        quiz_options=(
            "As a measurable hypothesis to check against this company's own real trade history, not an assumed rule",
            "As an absolute law that always holds",
            "As irrelevant since sessions don't matter",
            "As something only true on Mondays",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-trading-ranges",
        order=5,
        title="Trading Ranges & Consolidation",
        simple_explanation="Markets spend real time consolidating between real expansion moves — a trading range. Recognizing a genuine range, rather than mistaking it for a fading trend, changes what kind of setup actually makes sense.",
        deeper_explanation="TradeTown's real 13-way regime classifier (app/market_intelligence.py's _classify_regime()) already names 'sideways_range' as one of its real, threshold-based regime outcomes — not a separate concept this track invents, but the exact real signal a range is a checkable, named state, not a vague feeling. A real Fair Value Gap or session range forming and holding without expansion is real, additional evidence consistent with range conditions.",
        quiz_question="What real TradeTown signal already names a trading-range condition explicitly?",
        quiz_options=(
            "app/market_intelligence.py's 13-way regime classifier, which includes a real 'sideways_range' outcome",
            "Nothing — ranges are never labeled",
            "The CEO's calendar",
            "A random daily coin flip",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-classical-chart-patterns",
        order=6,
        title="Classical Chart Patterns: A Real Vocabulary, Not An Auto-Detector",
        simple_explanation="Double tops/bottoms, head & shoulders, triangles, and wedges are real, well-known reversal and continuation patterns worth recognizing by eye. TradeTown does not currently auto-detect any of them — this lesson teaches the real vocabulary honestly, without implying a detector exists.",
        deeper_explanation="A full grep audit of this codebase found no implementation of double/triple top or bottom detection, head & shoulders (or inverse), cup & handle, or triangle/wedge/rectangle classification — only real Fair Value Gap, order block, candlestick, session-range, and Fibonacci detection exist today (app/technical_patterns.py). Naming this boundary honestly here matters for the same reason this directive requires it for Elliott Wave and harmonic patterns: a named framework is not the same claim as a working detector.",
        quiz_question="Does TradeTown currently auto-detect double tops, head & shoulders, or triangle patterns?",
        quiz_options=(
            "No — a full audit confirms none of these are implemented; they remain real concepts worth understanding manually",
            "Yes, all of them are fully automated",
            "Only double tops are detected",
            "Only on weekends",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-reversal-confirmation",
        order=7,
        title="Reversal Confirmation vs. Failed Reversals",
        simple_explanation="Spotting a possible reversal shape is only step one — a real reversal needs real confirmation (a break of the prior trend's own structure), and plenty of apparent reversals fail and the prior trend resumes.",
        deeper_explanation="The real, checkable confirmation TradeTown already computes is a genuine Break of Structure in the opposite direction from the prior trend (app/market_intelligence.py's compute_market_structure(), reused directly by app/technical_patterns.py rather than re-implemented) — a new swing low below the prior one after an uptrend, or a new swing high above the prior one after a downtrend. A reversal-looking candle or pattern without that real structural break is still just a candidate, not confirmed evidence.",
        quiz_question="What real, existing TradeTown signal counts as structural confirmation of a reversal?",
        quiz_options=(
            "A real Break of Structure in the opposite direction from the prior trend",
            "Any single red candle",
            "A news headline mentioning the symbol",
            "The passage of exactly 24 hours",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="ab-probability-not-certainty",
        order=8,
        title="Reading Probability, Not Certainty",
        simple_explanation="Every framework in this track — candlestick shapes, breakouts, ranges, reversals — describes a real pattern in past price. None of them, alone or combined, guarantees what happens next. Professional analysis means weighing real, disclosed evidence, never assuming certainty.",
        deeper_explanation="This closes the track on the same real, structural rule the rest of TradeTown already enforces end to end: the Market Intelligence Department's own Probability First rule (app/market_intelligence.py's module docstring) forbids treating any signal as a guarantee; app/gatekeeper.py's Trade Gatekeeper still runs its full ten-check pipeline regardless of how convincing a price-action read looks; and 'no trade' remains a fully valid, often preferable outcome when the real evidence — however many patterns line up — still isn't sufficient.",
        quiz_question="What should happen when a trade candidate has multiple price-action patterns lining up but the Trade Gatekeeper still rejects it?",
        quiz_options=(
            "The Gatekeeper's rejection stands — no pattern, or combination of patterns, overrides the real risk/evidence pipeline",
            "The patterns should override the Gatekeeper automatically",
            "The CEO should disable the Gatekeeper for that trade",
            "More patterns always means the trade must be taken",
        ),
        correct_index=0,
    ),
)

# v0.7 Feature 51 — the Market Intelligence Department's own Academy
# track. Not attributed to any real external educator (see
# _MARKET_INTELLIGENCE_CONTENT_NOTE above) — every lesson teaches a real
# mechanic app/market_intelligence.py actually computes, the exact same
# "cite the real module/field, never fabricate" discipline _TJR_LESSONS
# above already established.
_MARKET_INTELLIGENCE_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="mi-regimes",
        order=1,
        title="Market Regimes & Trend Analysis",
        simple_explanation="Markets don't move the same way every day — sometimes they trend hard, sometimes they chop sideways, sometimes volatility expands or compresses. Naming the current regime honestly, before looking for a trade, is the first real step of professional market analysis.",
        deeper_explanation="app/market_intelligence.py's _classify_regime() names one of thirteen real regimes (strong/weak bull or bear trend, sideways range, expansion, compression, high/low volatility, accumulation, distribution, liquidity hunt, transitional) from real, ordered thresholds on the average trend and volatility across the watchlist's own real (mock) candle data — never a guess, and never a forecast of what happens next per the department's own Probability First rule.",
        quiz_question="What does TradeTown's 13-way regime classification actually describe?",
        quiz_options=(
            "The market's current real state, computed from real candle data — never a prediction of what happens next",
            "A forecast of tomorrow's price direction",
            "A random label chosen for flavor text",
            "The CEO's own personal opinion of the market",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-structure",
        order=2,
        title="Market Structure",
        simple_explanation="Market structure is the real skeleton underneath price — swing highs and lows, and whether a new swing breaks past the last one (a real Break of Structure). Reading structure tells you whether a trend is continuing, reversing, or just consolidating.",
        deeper_explanation="app/market_intelligence.py's compute_market_structure() finds real local-extrema swing points in a symbol's own candle history and checks the standard real definition of a Break of Structure — a new swing high above the prior one (bullish) or a new swing low below the prior one (bearish) — never an invented pattern.",
        quiz_question="What is a real Break of Structure, as TradeTown computes it?",
        quiz_options=(
            "A new real swing high (or low) that goes beyond the prior real swing high (or low)",
            "Any single red candle in an uptrend",
            "A random event chosen once per day",
            "Whenever the CEO manually flags it",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-liquidity",
        order=3,
        title="Liquidity",
        simple_explanation="Price is often drawn toward clusters of similar highs or lows before reversing — probable liquidity zones. Watching for a wick that pierces one of these zones and then closes back inside is a real, standard price-action signal.",
        deeper_explanation="app/market_intelligence.py's compute_liquidity() clusters real equal-high/equal-low swing points into LiquidityZones and flags a real sweepDetected pattern (a wick beyond the zone that closes back inside it) — an honest, real price-action read. It is explicitly NOT real order-book data: this codebase's MarketDataProvider has no bid/ask depth or resting-order feed, so a LiquidityZone is a probable zone inferred from real price structure, never a claim about actual stop orders.",
        quiz_question="What does a TradeTown LiquidityZone actually represent?",
        quiz_options=(
            "A probable zone inferred from real price structure — not a real read of actual resting orders, which this codebase has no data for",
            "A confirmed list of every trader's real stop-loss price",
            "A guaranteed reversal point",
            "A random price level generated for flavor",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-institutional",
        order=4,
        title="Institutional Behavior",
        simple_explanation="Unusually high volume alongside a surprisingly small price move can hint that a large participant is absorbing supply or demand quietly. It's a real, useful clue — but on ordinary price/volume data alone, it's a clue, not proof of who's actually trading.",
        deeper_explanation="app/market_intelligence.py's InstitutionalActivityRead is an explicit, named PROXY: a real volume-vs-price-move divergence ('absorption') score computed from real (mock) volume and price data. It is never presented as verified institutional order flow, Level 2 data, or dark-pool prints — this codebase's MarketDataProvider exposes no order book at all, and none is fabricated. The department's own module docstring states this boundary directly.",
        quiz_question="Why does TradeTown call its Institutional Activity read a 'proxy' rather than real institutional data?",
        quiz_options=(
            "Because this codebase has no real order-flow, Level 2, or dark-pool data source — it's a real but indirect volume/price-divergence signal instead",
            "Because it's randomly generated and meaningless",
            "Because only the CEO is allowed to see real institutional data",
            "Because it was too expensive to build a real version",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session",
        order=5,
        title="Session Characteristics",
        simple_explanation="Liquidity and volatility change dramatically by time of day — the London/New York overlap trades very differently than the quiet hours between the Asian and London sessions. Knowing which session is active is real, useful context before evaluating any setup.",
        deeper_explanation="app/market_intelligence.py's compute_session() reads real wall-clock UTC time (the same convention Candle.timestamp already uses, not TradeTown's simulated clock) against fixed, documented session windows — Asian, London, the London/New York Overlap, NY Lunch Hour, New York, and dedicated Market Open/Close windows — an honest, documented simplification (no live timezone/DST feed).",
        quiz_question="What real-world clock does TradeTown's Session Intelligence read from?",
        quiz_options=(
            "Real wall-clock UTC time — the same convention real candle timestamps already use",
            "TradeTown's own simulated in-game clock",
            "The CEO's local computer time zone, unadjusted",
            "It doesn't track time at all",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-volatility",
        order=6,
        title="Volatility",
        simple_explanation="Volatility isn't just 'is the market moving a lot' — professional analysis compares the CURRENT range against a real historical baseline, so an unusually quiet or unusually wild period stands out clearly.",
        deeper_explanation="app/market_intelligence.py's VolatilityRead carries four real numbers: currentPct and historicalAvgPct (both from the real volatility_pct() helper app/signal_calibration.py and app/player_vs_ai.py already use, over different real candle sub-windows), sessionPct (volatility computed only from candles inside the current real session), and a percentile comparing the two — never a forecast, always a real comparison against this same data's own history.",
        quiz_question="What does TradeTown's Volatility percentile actually compare?",
        quiz_options=(
            "The current real volatility reading against this same symbol set's own real historical average",
            "This company's volatility against every other real trading firm",
            "A random number with no real basis",
            "Tomorrow's expected volatility",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-probability",
        order=7,
        title="Probability Thinking",
        simple_explanation="TradeTown never claims to know what happens next — it thinks in probabilities and comparisons instead: how good are today's conditions, really, and how often has this same situation shown up before?",
        deeper_explanation="The Market Quality Score (MarketQualityScore) grades today's real conditions Excellent/Good/Average/Poor/Avoid Trading from a real weighted composite of volatility fit, structure clarity, session liquidity, sweep risk, and news activity — with a confidencePct that is deliberately capped below 100, since the department's own Probability First rule forbids claiming full certainty. historicalSimilarity is a real, honest count of how often this exact regime has occurred in this company's own prior daily reports — never an external dataset, never a fabricated statistic.",
        quiz_question="Why does the Market Quality Score's confidence never reach 100%?",
        quiz_options=(
            "Because the Probability First rule forbids claiming full certainty about market conditions",
            "Because of a rounding bug",
            "Because the CEO capped it arbitrarily for no reason",
            "Because the formula is broken",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-risk-context",
        order=8,
        title="Risk Context",
        simple_explanation="Even a well-researched trade idea should be checked against the market's own current conditions — thin session liquidity, an active liquidity sweep, or an outright poor Market Quality read are all real reasons to pause, independent of the trade's own individual merits.",
        deeper_explanation="Two real, independent checks enforce this: the Market Debate's Risk specialist (app/market_debate.py) reads only real market-CONDITION risk (session, quality tier, news volume) — never portfolio exposure, which stays Sentinel/Guardian's job — and the Trade Gatekeeper's own market_intelligence check (app/gatekeeper.py) mechanically blocks a trade outright while the real Market Quality Score reads 'avoid_trading', regardless of how confident any single department is.",
        quiz_question="What real check can block a trade purely because of market conditions, independent of the proposal's own confidence?",
        quiz_options=(
            "The Trade Gatekeeper's market_intelligence check, when the real Market Quality Score reads 'avoid_trading'",
            "A coin flip",
            "The CEO's mood that day",
            "Nothing — market conditions are never actually checked",
        ),
        correct_index=0,
    ),
    # CEO directive "Session Trading Education & Agent Training" — a real
    # session-intelligence sub-module, orders 9-15, extending this same
    # track rather than a new curriculum system. mi-session (order 5,
    # above) already introduces real Session Intelligence mechanics
    # (compute_session()'s real UTC windows); these seven lessons build
    # the actual DECISION discipline on top of it — session context as
    # evidence to check, never as a signal to act on — closing with the
    # real 8-step process app/session_evidence.py and the existing
    # Gatekeeper/risk pipeline already enforce end to end.
    _LessonSpec(
        id="mi-session-foundations",
        order=9,
        title="Session Context Is Evidence, Not a Signal",
        simple_explanation="A session name alone — 'it's London right now' — is not a reason to trade. Session context can inform a decision the same way regime or volatility does, but it never replaces checking whether a real setup actually exists and whether the evidence supports it.",
        deeper_explanation="app/session_evidence.py's compute_session_regime_evidence() is the literal enforcement of this idea: it never asks 'is London happening,' it asks 'how has this real (session, regime) pairing actually performed across this company's own real closed trades' — and it reports NOT_ENOUGH_EVIDENCE honestly whenever the sample is too thin to say anything, rather than assuming a session is good or bad. The department's own Probability First rule (mi-probability, above) already forbids treating any single signal as decisive; session is no exception.",
        quiz_question="Which statement is correct about session context in TradeTown?",
        quiz_options=(
            "Session context informs a decision; it does not make the decision",
            "Trading during London always produces a better outcome than trading during Asia",
            "A trade should be entered automatically whenever a session opens",
            "Session context replaces the need to check the Trade Gatekeeper",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-asia",
        order=10,
        title="Reading the Asian Session",
        simple_explanation="The Asian session (00:00-08:00 UTC in TradeTown's fixed windows) is a real, lower-weighted session in the Market Quality Score — historically thinner participation than London or New York. That's a real starting hypothesis about liquidity, not a proven rule about this company's own results.",
        deeper_explanation="app/market_intelligence.py's _SESSION_QUALITY weights 'asian' at 45/100 — real, but only one input (weight 0.2) into the broader Market Quality Score alongside volatility, structure, and news. Whether a specific strategy actually performs better or worse during Asia is a separate, checkable question app/session_evidence.py answers from this company's own real closed DecisionVaultEntry history — never assumed from the quality weight alone.",
        quiz_question="TradeTown's Market Quality Score weights the Asian session lower than London or New York. What does that real weight NOT tell you on its own?",
        quiz_options=(
            "Whether a specific strategy has actually performed well or poorly during Asia in this company's own real trade history",
            "That the Asian session exists in TradeTown's fixed UTC windows",
            "That session is one input among several in the Market Quality Score",
            "That liquidity assumptions should be treated as hypotheses to check",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-london",
        order=11,
        title="Reading the London Session",
        simple_explanation="London (08:00-13:00 UTC) carries a real Market Quality weight of 70/100 — noticeably higher than Asia. A common real-world hypothesis is that the London open can move price out of a range the Asian session established. TradeTown has the real pieces to check that hypothesis (session data, structure/liquidity reads) — it does not assert it as fact.",
        deeper_explanation="app/market_intelligence.py's compute_market_structure() and compute_liquidity() (mi-structure/mi-liquidity, above) run on the same real candle history regardless of session — there is no London-specific breakout detector. A department opinion citing 'London is active' alongside a real structure break or liquidity-zone sweep is combining two real, independent signals; citing 'London is active' alone is not.",
        quiz_question="What should an agent check before treating a London-session breakout idea as worth acting on?",
        quiz_options=(
            "Whether real structure/liquidity signals (Break of Structure, a liquidity sweep) actually support it, and whether session×regime evidence backs it — not the session label alone",
            "Nothing further — London being active is sufficient on its own",
            "Whether the CEO is currently online",
            "The color of the candlestick chart",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-new-york",
        order=12,
        title="Reading the New York Session",
        simple_explanation="New York (17:00-21:00 UTC, with a dedicated Market Open window at 13:30-14:00 and Market Close at 20:30-21:00) carries the same real 70/100 quality weight as London, plus real, separately-tracked Market Open/Close windows for the highest-participation minutes. More activity is real — it is not automatically higher-quality activity.",
        deeper_explanation="High volume alongside a surprisingly small price move is exactly what mi-institutional (above) calls a real but indirect proxy — 'absorption' — never proof of favorable conditions. New York's higher participation can widen spreads and increase noise as easily as it can create a genuine move; the Market Quality Score's own volatility and structure-clarity components (not the session label) are what actually separates the two.",
        quiz_question="Why doesn't TradeTown treat 'New York is active' as automatically meaning 'better trading conditions'?",
        quiz_options=(
            "Because high activity does not automatically mean high-quality trades — volatility and structure clarity are checked separately, not assumed from participation alone",
            "Because New York is scored identically to a closed market",
            "Because the Market Quality Score ignores volume entirely",
            "Because New York never actually has real volatility",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-overlap",
        order=13,
        title="The London/New York Overlap",
        simple_explanation="The Overlap (13:00-16:00 UTC) carries the highest real Market Quality weight in TradeTown, 90/100 — both sessions' participants are active at once, which can mean faster, larger moves as well as faster, larger mistakes.",
        deeper_explanation="This higher weight feeds the Market Quality Score exactly like every other session weight — it does NOT change app/schemas.py's own RiskLimits (risk_per_trade_pct, max_open_positions, max_drawdown_pct, ...) or app/gatekeeper.py's checks in any special-cased way. The existing risk and governance pipeline is authoritative regardless of how favorable a session looks; a busier session is a reason for a closer look, never an automatic reason to size up.",
        quiz_question="Should an agent's position sizing automatically increase during the London/New York Overlap because it's the highest-quality session?",
        quiz_options=(
            "No — RiskLimits and the Trade Gatekeeper remain the authority on sizing and approval regardless of session; the Overlap is not a special case",
            "Yes — always double size during the Overlap",
            "Yes, because the Gatekeeper is skipped during the Overlap",
            "It doesn't matter — risk limits don't apply to the Overlap",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-transitions",
        order=14,
        title="Session Transitions",
        simple_explanation="The moment one session hands off to the next — Asia into London, London into New York — is when conditions are most likely to actually change, not just the clock. The real question isn't 'what session is it now,' it's 'did anything real actually change.'",
        deeper_explanation="Six real, checkable questions frame a transition: did VolatilityRead's real currentPct/historicalAvgPct comparison move? did SessionRead's real component of the Market Quality Score change? did the prior session's real structure (compute_market_structure()) establish a meaningful range? did price break or reject that range (a real Break of Structure or liquidity sweep)? does session_evidence.py show this strategy has historically performed during this transition? and — the one that matters most — is there enough real evidence (MIN_SESSION_REGIME_SAMPLE observations) to trust that read at all?",
        quiz_question="What should an agent check first when a session transition occurs, according to TradeTown's own real data?",
        quiz_options=(
            "Whether volatility, liquidity, or structure actually changed — not merely that the clock crossed into a new session window",
            "Nothing — the new session name is sufficient on its own",
            "Only the CEO's mood",
            "Whether the transition happened on a weekend",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-session-decision-process",
        order=15,
        title="How To Actually Use Session Context",
        simple_explanation="This is the most important lesson in the module: session context earns a place in a REAL structured process, and it never skips a real step of that process just because the session looks favorable.",
        deeper_explanation=(
            "The real, existing pipeline, unchanged by this lesson: (1) identify the current session — app/market_intelligence.py's compute_session(); (2) identify the current regime — the same module's 13-way _classify_regime(); (3) identify the setup/proposal actually being considered — a real TradeProposal, never a hypothetical; (4) check session×regime evidence — app/session_evidence.py's compute_session_regime_evidence(), honestly reporting NOT_ENOUGH_EVIDENCE below MIN_SESSION_REGIME_SAMPLE real observations, never assumed favorable; (5) evaluate current real conditions — the Market Quality Score, VolatilityRead, active RiskWarnings; (6) a real proposal is generated only when the existing confidence/setup conditions in app/executive.py's generate_proposal() are already satisfied — session never creates a proposal by itself; (7) the real Trade Gatekeeper (app/gatekeeper.py, all 11 checks) always runs, unchanged; (8) execution happens only once every existing requirement — Gatekeeper approval and RiskLimits — is satisfied. Steps 3 through 7 are never skipped, no matter how favorable a session appears."
        ),
        quiz_question="According to TradeTown's real decision process, which steps must never be skipped just because a session looks favorable?",
        quiz_options=(
            "Checking the actual setup, the real evidence, current conditions, and running the Trade Gatekeeper and risk pipeline (steps 3 through 7)",
            "None — a favorable session can skip straight to execution",
            "Only the confidence check, everything else can be skipped",
            "All of them can be skipped once the Overlap begins",
        ),
        correct_index=0,
    ),
    # CEO directive "Professional Trading Firm — Market-Analysis
    # Knowledge + Session Intelligence Expansion," Phases 1-3 and 6-8 —
    # orders 16-23, extending this same track a second time rather than
    # starting a new one. Every lesson below cites a real function in
    # app/technical_patterns.py, app/technical_indicators.py, or
    # app/signal_correlation.py (all built for this same directive) —
    # or, where the underlying concept genuinely has no auto-detection
    # in this codebase (classical chart patterns, Elliott Wave, harmonic
    # patterns, Gann), the lesson says so plainly rather than implying a
    # detector exists.
    _LessonSpec(
        id="mi-fvg-liquidity-imbalance",
        order=16,
        title="Fair Value Gaps & Price Imbalance",
        simple_explanation="When price moves fast enough that three consecutive candles leave a real, checkable gap between them — no overlap at all — that gap is called a Fair Value Gap. It marks a real price imbalance, not a guarantee that price returns to fill it.",
        deeper_explanation="app/technical_patterns.py's detect_fair_value_gaps() checks the standard 3-candle definition exactly: candle 1's high below candle 3's low (bullish) or candle 1's low above candle 3's high (bearish), with candle 2 the real displacement move between them. Each real gap also tracks a real filled flag — whether a later candle actually traded back into it — never assumed. Naming a gap is a description of what already happened, never a prediction that price will return to it.",
        quiz_question="What does TradeTown's real Fair Value Gap detection actually check?",
        quiz_options=(
            "A real, exact 3-candle price gap with no overlap between candle 1 and candle 3 — a description of what happened, not a prediction it gets filled",
            "A guess based on the candle's color alone",
            "A guaranteed reversal signal",
            "A random zone with no real geometric definition",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-order-blocks",
        order=17,
        title="Order Blocks — One Disclosed Definition Among Several",
        simple_explanation="\"Order block\" means different specific things to different professional traders. TradeTown takes one real, disclosed stance — the last opposite-direction candle immediately before a real Break of Structure — rather than pretending there's a single universal definition.",
        deeper_explanation="app/technical_patterns.py's detect_order_block() reuses compute_market_structure()'s real Break of Structure detection directly (never a second structure engine) and reads the one candle immediately preceding it that closed the opposite direction from the break. This is a real, named, checkable proxy — not a claim of institutional order-flow data, which this codebase's MarketDataProvider does not have. Its own detail field discloses this boundary on every read.",
        quiz_question="Why does TradeTown call its order block read a disclosed proxy rather than a definitive read?",
        quiz_options=(
            "Because \"order block\" has more than one real professional definition, and this codebase has no real institutional order-flow data to confirm any of them",
            "Because it's randomly generated",
            "Because order blocks don't really exist",
            "Because only Al Brooks himself could confirm one",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-fibonacci",
        order=18,
        title="Fibonacci — A Candidate Area, Never A Guarantee",
        simple_explanation="Fibonacci retracement and extension levels (0.382, 0.5, 0.618, and others) mark candidate areas worth watching after a real swing — not a level that price is bound to respect.",
        deeper_explanation="app/technical_patterns.py's compute_fibonacci_levels() reuses the same real swing-high/swing-low detection compute_market_structure() already performs (never a second swing engine) and computes real retracement ratios (0.236/0.382/0.5/0.618/0.786) and extension ratios (1.272/1.618) against that real swing range. No level is ever encoded as 'always reverses' — each is a real, checkable price, nothing more, exactly matching this directive's own explicit rule against treating any Fibonacci level as guaranteed.",
        quiz_question="What is the correct way to treat a TradeTown Fibonacci level?",
        quiz_options=(
            "A candidate area worth watching, requiring its own separate confirmation before acting on it",
            "A guaranteed reversal price",
            "The exact price the market must close at",
            "A random number unrelated to the real swing range",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-candlestick-patterns",
        order=19,
        title="Candlestick Patterns — Real Shapes, Not Fortune-Telling",
        simple_explanation="Engulfing candles, hammers, shooting stars, and dojis are real, geometrically-checkable candle shapes. Naming one describes what a candle looks like — it is never, on its own, a claim about what the next candle will do.",
        deeper_explanation="app/technical_patterns.py's detect_candlestick_patterns() checks each shape against its own real, textbook geometric definition — body size relative to range, wick length relative to body, direction of the prior candle for engulfing patterns. Order matters in its own detection logic: a long-wick, small-body candle is checked against hammer/shooting-star's lopsided-wick definition before the broader doji check, so a real hammer is never misread as a doji.",
        quiz_question="What does detecting a candlestick pattern in TradeTown actually confirm?",
        quiz_options=(
            "That a specific, real, geometrically-defined candle shape occurred — not a prediction of the next candle",
            "A guaranteed reversal on the very next candle",
            "That the CEO should trade immediately",
            "Nothing real — it's flavor text",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-indicators",
        order=20,
        title="Indicators: What They Measure, And What They Don't",
        simple_explanation="RSI, MACD, Stochastic, moving averages, ATR, and VWAP are all real, standard-formula calculations over real candle data. Each measures a specific, narrow thing — none of them predicts the future, and several measure closely related information.",
        deeper_explanation="app/technical_indicators.py computes each with its real textbook formula: SMA/EMA (trend, lagging), RSI/Stochastic (momentum/overbought-oversold, both derived from the same underlying price momentum), MACD (trend-following momentum, itself built from two EMAs), ATR (volatility, non-directional), and VWAP (a real volume-weighted average price, not a trend signal). Parabolic SAR and SuperTrend are deliberately NOT implemented here — both are more implementation-sensitive, and adding them without equal rigor would be exactly the 'indicator soup, added because the list asked for it' anti-pattern this directive warns against. They remain real, named, un-implemented research candidates.",
        quiz_question="Why might RSI and Stochastic both agreeing NOT count as two fully independent confirmations?",
        quiz_options=(
            "Because both are momentum oscillators derived from closely related underlying price-movement information, not two unrelated data sources",
            "Because they always disagree",
            "Because one of them is fabricated",
            "Because TradeTown doesn't compute either one",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-derived-charts",
        order=21,
        title="Heikin-Ashi & Renko: Derived, Never Executable",
        simple_explanation="Heikin-Ashi and Renko charts filter noise and can make a trend easier to read — but they are mathematically DERIVED from real price, not real price itself. TradeTown's real execution — entries, exits, stops, fills, P&L, risk — always uses the real, underlying price, never a derived representation.",
        deeper_explanation="This is a hard architectural rule, not a style preference: app/portfolio.py's open_position()/close_position() only ever receive real Quote/Candle-sourced prices — nothing in TradeTown's execution path reads from a derived chart type. Neither Heikin-Ashi nor Renko is currently computed anywhere in this codebase (confirmed by a full grep audit); this lesson exists so the rule is understood BEFORE either is ever built, exactly as this directive requires.",
        quiz_question="If TradeTown ever adds Heikin-Ashi or Renko charts, what must remain true?",
        quiz_options=(
            "Real execution (entries, exits, stops, fills, P&L, risk) must always use the real underlying price, never the derived chart's values",
            "Execution should switch to using the derived chart's price instead",
            "It doesn't matter which price is used for execution",
            "Heikin-Ashi candles become the new real price once computed",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-hypothesis-frameworks",
        order=22,
        title="Elliott Wave, Harmonic Patterns, & Gann: Hypotheses, Not Detectors",
        simple_explanation="Elliott Wave counts, harmonic patterns (Bat, Butterfly, Crab), and Gann angles are real, named frameworks used by real traders — but TradeTown does not auto-detect any of them. Treat each as a research hypothesis with real ambiguity, never as a system with proven predictive power just because the framework has a name.",
        deeper_explanation="A full grep audit of this codebase found zero implementations of Elliott Wave counting, harmonic XABCD/Fibonacci-ratio validation, or Gann angle computation — building an honest version of any of them would require forcing a specific wave count or angle onto every chart, which this directive explicitly forbids without a required invalidation level and alternative count. They remain real, named, documented research candidates — never a claim that TradeTown's own validated data has demonstrated predictive value for any of them, because no such validation exists yet.",
        quiz_question="What is the correct stance on Elliott Wave, harmonic patterns, and Gann angles in TradeTown today?",
        quiz_options=(
            "Real, named frameworks worth understanding as hypotheses — none are auto-detected or validated as predictive in this codebase",
            "All three are auto-detected and proven profitable",
            "They should be ignored entirely as fake",
            "TradeTown trades automatically whenever a wave count completes",
        ),
        correct_index=0,
    ),
    _LessonSpec(
        id="mi-confluence-and-overfitting",
        order=23,
        title="Confluence, Independence, & The Anti-Overfitting Discipline",
        simple_explanation="More agreeing signals is not automatically stronger evidence — if those signals are measuring the same underlying thing, they're the same evidence counted twice, not real confluence. And a strategy that looks better only because it grew more complex, not because out-of-sample results actually improved, is a real overfitting warning sign, not progress.",
        deeper_explanation="app/signal_correlation.py's assess_confluence() is built on a real audit of TradeTown's own six analyst votes: news and macro votes are NOT mutually independent (both driven by the same underlying ResearchItem.confidence value through the same probabilistic mechanism), and the execution vote is a pure majority synthesis of the other five, contributing zero new evidence. Separately, app/model_validation.py's Meridian/CIO now runs two real anti-overfitting checks: regime_dependence (real sign disagreement in return across tested regime buckets — a strategy that only works in one regime) and optimization_scrutiny (an implausibly high win rate on a still-small sample — the classic 'too good, too soon' shape of an overfit result, flagged for scrutiny, never automatically rejected).",
        quiz_question="Why doesn't TradeTown count 'RSI bullish + MACD bullish + a moving average bullish' as three independent confirmations?",
        quiz_options=(
            "Because those signals measure closely related momentum/trend information, so agreement among them is not automatically three genuinely independent evidence sources",
            "Because RSI and MACD are never real",
            "Because moving averages are banned from TradeTown",
            "Because three agreeing signals are always wrong",
        ),
        correct_index=0,
    ),
)

_LESSON_SPECS_BY_MENTOR: dict[FoundationalMentorId, tuple[_LessonSpec, ...]] = {
    "tjr": _TJR_LESSONS,
    "market_intelligence": _MARKET_INTELLIGENCE_LESSONS,
    # Trading Psychology & Discipline, Piece F.
    "mark_douglas": _MARK_DOUGLAS_LESSONS,
    "linda_raschke": _LINDA_RASCHKE_LESSONS,
    # CEO directive "Professional Trading Firm — Market-Analysis
    # Knowledge + Session Intelligence Expansion," Phases 1-2.
    "al_brooks": _AL_BROOKS_LESSONS,
    # The remaining two roadmap tracks (tom_hougaard, mike_bellafiore)
    # intentionally have no entry here yet — see this module's
    # docstring. Adding real content for one of them later is exactly:
    # write its own _LessonSpec tuple and add it here.
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _specs_for(mentor_id: FoundationalMentorId) -> tuple[_LessonSpec, ...]:
    return _LESSON_SPECS_BY_MENTOR.get(mentor_id, ())


def _public_lessons(specs: tuple[_LessonSpec, ...]) -> list[FoundationalMentorLesson]:
    return [
        FoundationalMentorLesson(
            id=s.id,
            order=s.order,
            title=s.title,
            simpleExplanation=s.simple_explanation,
            deeperExplanation=s.deeper_explanation,
            quizQuestion=s.quiz_question,
            quizOptions=list(s.quiz_options),
        )
        for s in sorted(specs, key=lambda s: s.order)
    ]


def default_foundational_mentor_state() -> FoundationalMentorState:
    mentors = []
    for mentor_id in _ROADMAP_ORDER:
        name, focus_areas = _ROADMAP_FOCUS[mentor_id]
        specs = _specs_for(mentor_id)
        mentors.append(
            FoundationalMentorProfile(
                id=mentor_id,
                name=name,
                trackLabel=f"{name} Track",
                focusAreas=focus_areas,
                contentNote=_MARKET_INTELLIGENCE_CONTENT_NOTE if mentor_id == "market_intelligence" else _CONTENT_DISCLAIMER,
                status="active" if specs else "planned",
                lessons=_public_lessons(specs),
                resources=[],
            )
        )
    return FoundationalMentorState(
        mentors=mentors, progress={}, ceoProgress={}, activeMentorId="tjr", roadmapOrder=list(_ROADMAP_ORDER), customLessonAnswers={}, updatedAt=_now_iso()
    )


def _mentor_by_id(state: FoundationalMentorState, mentor_id: FoundationalMentorId | None) -> FoundationalMentorProfile | None:
    if mentor_id is None:
        return None
    for m in state.mentors:
        if m.id == mentor_id:
            return m
    return None


def _lesson_by_id(mentor: FoundationalMentorProfile, lesson_id: str) -> FoundationalMentorLesson | None:
    for lesson in mentor.lessons:
        if lesson.id == lesson_id:
            return lesson
    return None


def _next_lesson(mentor: FoundationalMentorProfile, progress: FoundationalMentorProgress) -> FoundationalMentorLesson | None:
    for lesson in sorted(mentor.lessons, key=lambda lesson: lesson.order):
        if lesson.id not in progress.completed_lesson_ids:
            return lesson
    return None


def _add_once(items: list[str], item: str) -> list[str]:
    return items if item in items else [*items, item]


def _is_graduated_progress(mentor: FoundationalMentorProfile, progress: FoundationalMentorProgress) -> bool:
    if not mentor.lessons:
        return False
    completed = set(progress.completed_lesson_ids)
    return all(lesson.id in completed for lesson in mentor.lessons)


def _next_roadmap_id(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> FoundationalMentorId | None:
    """Reads the real, persisted `state.roadmap_order` — not the module-
    level `_ROADMAP_ORDER` constant — so CEO-added custom mentors
    (appended to `roadmap_order` by `add_custom_mentor`) really do come
    up for company-wide study in their turn."""
    order = state.roadmap_order
    if mentor_id not in order:
        return None
    idx = order.index(mentor_id)
    if idx + 1 >= len(order):
        return None
    return order[idx + 1]


def _employee_progress(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId) -> FoundationalMentorProgress:
    return state.progress.get(agent_id, {}).get(mentor_id) or FoundationalMentorProgress(mentorId=mentor_id)


def _agent_aptitude(agent_id: AgentId, discipline_reviews: list[DisciplineReview]) -> float:
    """The real per-agent signal behind an employee's own auto-quiz pass
    probability — see module docstring's "AUTO-GRADED QUIZZES" section."""
    scores = [r.score for r in discipline_reviews if agent_id in r.attendees]
    if not scores:
        return 50.0
    return sum(scores) / len(scores)


def tick_employee_progress(
    state: FoundationalMentorState,
    *,
    discipline_reviews: list[DisciplineReview],
    sim_day: int,
) -> tuple[FoundationalMentorState, list[AgentId]]:
    """Advances every real employee student one real tick's worth of
    study progress on the company's one active mentor track, auto-grades
    a quiz whenever a lesson's study bar fills, and returns
    (new_state, agent_ids_newly_pending_approval). No-ops entirely if
    there's no active mentor or the active mentor has no real content
    yet (a roadmap-only track — see module docstring)."""
    active_mentor = _mentor_by_id(state, state.active_mentor_id)
    if active_mentor is None or active_mentor.status != "active" or not active_mentor.lessons:
        return state, []

    new_progress_map: dict[AgentId, dict[FoundationalMentorId, FoundationalMentorProgress]] = {aid: dict(m) for aid, m in state.progress.items()}
    newly_pending: list[AgentId] = []

    for agent_id in STUDENT_AGENT_IDS:
        progress = _employee_progress(state, agent_id, active_mentor.id)
        if progress.graduation_status != "in_progress":
            continue
        lesson = _next_lesson(active_mentor, progress)
        if lesson is None:
            continue

        new_study_pct = min(100.0, progress.current_lesson_study_pct + random.uniform(*STUDY_GAIN_RANGE))
        if new_study_pct < 100.0:
            progress = progress.model_copy(update={"current_lesson_study_pct": new_study_pct, "viewed_lesson_ids": _add_once(progress.viewed_lesson_ids, lesson.id)})
        else:
            pass_probability = max(MIN_QUIZ_PASS_PROBABILITY, min(MAX_QUIZ_PASS_PROBABILITY, _agent_aptitude(agent_id, discipline_reviews) / 100.0))
            passed = random.random() < pass_probability
            quiz_attempts = progress.quiz_attempts + 1
            if passed:
                completed_ids = _add_once(progress.completed_lesson_ids, lesson.id)
                progress = progress.model_copy(
                    update={
                        "completed_lesson_ids": completed_ids,
                        "current_lesson_study_pct": 0.0,
                        "quiz_attempts": quiz_attempts,
                        "correct_quiz_attempts": progress.correct_quiz_attempts + 1,
                        "consecutive_quiz_failures": 0,
                    }
                )
                if progress.graduation_status == "in_progress" and _is_graduated_progress(active_mentor, progress):
                    progress = progress.model_copy(update={"graduation_status": "pending_approval"})
                    newly_pending.append(agent_id)
            else:
                progress = progress.model_copy(
                    update={
                        "current_lesson_study_pct": FAILURE_STUDY_RESET_PCT,
                        "quiz_attempts": quiz_attempts,
                        "consecutive_quiz_failures": progress.consecutive_quiz_failures + 1,
                    }
                )

        agent_map = new_progress_map.setdefault(agent_id, {})
        agent_map[active_mentor.id] = progress

    new_state = state.model_copy(update={"progress": new_progress_map, "updated_at": _now_iso()})
    return new_state, newly_pending


def _certification_key(agent_id: AgentId, mentor_id: FoundationalMentorId) -> str:
    return f"cert-{agent_id}-{mentor_id}"


def _certification_by_key(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId) -> CertificationRecord | None:
    key = _certification_key(agent_id, mentor_id)
    return next((c for c in state.certifications if c.id == key), None)


def _append_certification_history(record: CertificationRecord, *, action: str, reason: str | None, sim_day: int) -> CertificationRecord:
    """Appends one permanent history entry, bumping `updated_sim_day` —
    never changes `status` itself, so every call site chains its own
    `.model_copy(update={"status": ...})` to make that transition
    explicit at the call site."""
    entry = CertificationHistoryEntry(id=f"{record.id}-h{len(record.history)}", action=action, reason=reason, simDay=sim_day, createdAt=_now_iso())  # type: ignore[arg-type]
    return record.model_copy(update={"updated_sim_day": sim_day, "history": [*record.history, entry]})


def approve_graduation(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId, *, sim_day: int) -> tuple[FoundationalMentorState, bool, str | None]:
    """A real CEO action — the Graduation Queue's Approve button. Returns
    (state, company_just_graduated, error). Also upserts this employee's
    permanent CertificationRecord (Certification Management, below) —
    "active" status with a real "earned" history entry, whether this is
    the first time or a real re-earning after an earlier revoke."""
    if agent_id not in STUDENT_AGENT_IDS:
        return state, False, "Unknown employee — not a real Academy student."
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, False, "Unknown mentor track."
    progress = _employee_progress(state, agent_id, mentor_id)
    if progress.graduation_status != "pending_approval":
        return state, False, f"{agent_id} has no pending graduation on {mentor_id} to approve."

    progress = progress.model_copy(update={"graduation_status": "graduated", "graduated_sim_day": sim_day, "coach_note": None})
    new_progress_map = {aid: dict(m) for aid, m in state.progress.items()}
    new_progress_map.setdefault(agent_id, {})[mentor_id] = progress

    existing_cert = _certification_by_key(state, agent_id, mentor_id)
    if existing_cert is None:
        cert_id = _certification_key(agent_id, mentor_id)
        entry = CertificationHistoryEntry(id=f"{cert_id}-h0", action="earned", reason=None, simDay=sim_day, createdAt=_now_iso())
        new_cert = CertificationRecord(id=cert_id, agentId=agent_id, mentorId=mentor_id, mentorName=mentor.name, status="active", updatedSimDay=sim_day, history=[entry])
        new_certifications = [*state.certifications, new_cert]
    else:
        updated_cert = _append_certification_history(existing_cert, action="earned", reason=None, sim_day=sim_day).model_copy(update={"status": "active"})
        new_certifications = [updated_cert if c.id == existing_cert.id else c for c in state.certifications]

    new_state = state.model_copy(update={"progress": new_progress_map, "certifications": new_certifications, "updated_at": _now_iso()})

    company_graduated = all(_employee_progress(new_state, aid, mentor_id).graduation_status == "graduated" for aid in STUDENT_AGENT_IDS)
    if not company_graduated:
        return new_state, False, None

    new_mentors = [m.model_copy(update={"status": "graduated", "company_graduated_sim_day": sim_day}) if m.id == mentor_id else m for m in new_state.mentors]
    new_active_id = new_state.active_mentor_id
    next_id = _next_roadmap_id(new_state, mentor_id)
    if next_id is not None:
        new_mentors = [m.model_copy(update={"status": "active"}) if m.id == next_id else m for m in new_mentors]
        new_active_id = next_id
    new_state = new_state.model_copy(update={"mentors": new_mentors, "active_mentor_id": new_active_id, "updated_at": _now_iso()})
    return new_state, True, None


# --- Certification Management — full CEO controls over an earned certification ---
#
# A quality-of-life fix: previously, once an employee's certification
# appeared in the Current Certifications list, the only way to revoke it
# was to happen to find that employee in one of the ACTIVE mentor
# track's own summary lists (Currently Studying/Top Students/Needing
# Help) — impossible for a certification on an already-completed, no-
# longer-active track. `CertificationRecord` (schemas.py) is now the
# real, independent, permanent record every action below reads and
# writes, so every certification — regardless of which track is
# currently active — is always directly addressable.
#
# Deliberately NOT built: "Promote"/"Downgrade" to a performance tier
# (Bronze/Silver/Gold or similar). No tiered-certification concept
# exists anywhere in this codebase — Foundational Mentor graduation is a
# real pass/fail signal (all lessons quizzed correctly), not a graded
# scale, and inventing tier thresholds with no real signal behind them
# would be exactly the kind of fabrication this codebase's own
# established discipline avoids throughout. "Downgrade"/"Promote" are
# instead real *standing* transitions — active <-> suspended — matching
# a real, professional certification lifecycle: Active (currently
# qualified), Suspended (temporarily disabled, reinstatable), Revoked
# (permanently pulled, must re-earn). "Expired" (a natural, non-punitive
# lapse) is also not built — it needs a real time-based renewal/decay
# signal this codebase has none of yet. Postponed to v1.0 (see
# docs/ROADMAP.md) rather than built here without one.


def downgrade_certification(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId, *, reason: str, sim_day: int) -> tuple[FoundationalMentorState, str | None]:
    """Suspends an active certification — a real, reversible demotion
    short of full revocation. The employee's underlying lesson/quiz
    progress is untouched (they're still nominally graduated on the raw
    curriculum); only their certification's own standing changes, so
    Promote can cleanly reinstate it without re-earning anything."""
    record = _certification_by_key(state, agent_id, mentor_id)
    if record is None:
        return state, f"{agent_id} has no certification on {mentor_id} to downgrade."
    if record.status != "active":
        return state, f"Only an active certification can be downgraded (current status: {record.status})."
    clean_reason = reason.strip()
    if not clean_reason:
        return state, "A reason is required to downgrade a certification."

    updated = _append_certification_history(record, action="suspended", reason=clean_reason, sim_day=sim_day).model_copy(update={"status": "suspended"})
    new_certifications = [updated if c.id == record.id else c for c in state.certifications]
    return state.model_copy(update={"certifications": new_certifications, "updated_at": _now_iso()}), None


def promote_certification(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId, *, sim_day: int, reason: str | None = None) -> tuple[FoundationalMentorState, str | None]:
    """Reinstates a suspended certification back to active — only
    "eligible" (offered at all) when a certification is currently
    suspended; the mirror image of downgrade_certification."""
    record = _certification_by_key(state, agent_id, mentor_id)
    if record is None:
        return state, f"{agent_id} has no certification on {mentor_id} to promote."
    if record.status != "suspended":
        return state, f"Only a suspended certification is eligible for promotion (current status: {record.status})."

    clean_reason = reason.strip() if reason else None
    updated = _append_certification_history(record, action="reinstated", reason=clean_reason, sim_day=sim_day).model_copy(update={"status": "active"})
    new_certifications = [updated if c.id == record.id else c for c in state.certifications]
    return state.model_copy(update={"certifications": new_certifications, "updated_at": _now_iso()}), None


def revoke_certification(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId, *, reason: str, sim_day: int) -> tuple[FoundationalMentorState, str | None]:
    """The full Revoke Certification action — a real CEO action, never
    automatic. Treated as remedial education, never as deleting company
    history: the CertificationRecord itself is never removed, only
    flipped to "revoked" with a permanent, reasoned history entry (see
    schemas.py's CertificationRecord/CertificationHistoryEntry) — so
    "View Certification History" always shows the complete real
    timeline. The employee's own lesson/quiz progress on this track
    resets to fresh (the same reset repeat_mentor_company_wide already
    uses per student) so they genuinely return to the Mentor Track and
    can re-earn the certification later, and the Coach's real note
    explains why. Deliberately narrow: only this one employee's own
    progress record changes. The mentor track's own company-wide status/
    roadmap position, and Company Knowledge (`academy_research.py`'s
    separate, company-wide project system — never gated by any one
    employee's individual graduation), are untouched — reverting a whole
    track's roadmap position over one employee's revocation would be a
    much larger, unrequested side effect. A reason is REQUIRED — this is
    a permanent audit entry, never optional (see also the Newspaper's
    "company" news category, this codebase's real analog to an
    Executive Log, which state.py appends to alongside this call)."""
    if agent_id not in STUDENT_AGENT_IDS:
        return state, "Unknown employee — not a real Academy student."
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    clean_reason = reason.strip()
    if not clean_reason:
        return state, "A reason is required to revoke a certification."
    record = _certification_by_key(state, agent_id, mentor_id)
    if record is None or record.status not in ("active", "suspended"):
        return state, f"{agent_id} has no active or suspended certification on {mentor_id} to revoke."

    updated_cert = _append_certification_history(record, action="revoked", reason=clean_reason, sim_day=sim_day).model_copy(update={"status": "revoked"})
    new_certifications = [updated_cert if c.id == record.id else c for c in state.certifications]

    note = f"Certification revoked by the CEO on sim day {sim_day}. Reason: {clean_reason} Repeat {mentor.track_label}'s curriculum to re-earn it."
    new_progress = FoundationalMentorProgress(mentorId=mentor_id, coachNote=note)
    new_progress_map = {aid: dict(m) for aid, m in state.progress.items()}
    new_progress_map.setdefault(agent_id, {})[mentor_id] = new_progress

    return state.model_copy(update={"progress": new_progress_map, "certifications": new_certifications, "updated_at": _now_iso()}), None


def reset_certification_progress(state: FoundationalMentorState, agent_id: AgentId, mentor_id: FoundationalMentorId, *, sim_day: int) -> tuple[FoundationalMentorState, str | None]:
    """Wipes any renewed lesson/quiz progress an employee has made toward
    RE-earning a revoked certification, restarting their repeat attempt
    from lesson one. Only offered on a "revoked" certification — a
    revoke already resets progress once (see revoke_certification), so
    this is specifically for zeroing out real headway made *since* that
    revoke, a genuine, separate admin action, not a duplicate of revoke
    itself. The CertificationRecord's own status/history is untouched
    beyond a new "progress_reset" entry — this never changes standing."""
    if agent_id not in STUDENT_AGENT_IDS:
        return state, "Unknown employee — not a real Academy student."
    record = _certification_by_key(state, agent_id, mentor_id)
    if record is None or record.status != "revoked":
        return state, f"{agent_id} has no revoked certification on {mentor_id} to reset progress for."

    updated_cert = _append_certification_history(record, action="progress_reset", reason=None, sim_day=sim_day)
    new_certifications = [updated_cert if c.id == record.id else c for c in state.certifications]

    new_progress = FoundationalMentorProgress(mentorId=mentor_id)
    new_progress_map = {aid: dict(m) for aid, m in state.progress.items()}
    new_progress_map.setdefault(agent_id, {})[mentor_id] = new_progress

    return state.model_copy(update={"progress": new_progress_map, "certifications": new_certifications, "updated_at": _now_iso()}), None


def pause_company_training(state: FoundationalMentorState) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, state.active_mentor_id)
    if mentor is None:
        return state, "No active mentor track to pause."
    if mentor.status != "active":
        return state, "Only an active track can be paused."
    new_mentors = [m.model_copy(update={"status": "paused"}) if m.id == mentor.id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "updated_at": _now_iso()}), None


def resume_company_training(state: FoundationalMentorState) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, state.active_mentor_id)
    if mentor is None:
        return state, "No active mentor track to resume."
    if mentor.status != "paused":
        return state, "Only a paused track can be resumed."
    new_mentors = [m.model_copy(update={"status": "active"}) if m.id == mentor.id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "updated_at": _now_iso()}), None


def skip_to_next_mentor(state: FoundationalMentorState) -> tuple[FoundationalMentorState, str | None]:
    """CEO manual override — every employee's progress on the skipped
    track is preserved, not discarded."""
    mentor = _mentor_by_id(state, state.active_mentor_id)
    if mentor is None:
        return state, "No active mentor track to skip."
    if mentor.status not in ("active", "paused"):
        return state, "Only an active or paused track can be skipped."
    next_id = _next_roadmap_id(state, mentor.id)
    if next_id is None:
        return state, "This is the last track on the roadmap — nothing to skip to."
    new_mentors = [
        m.model_copy(update={"status": "paused"}) if m.id == mentor.id else (m.model_copy(update={"status": "active"}) if m.id == next_id else m)
        for m in state.mentors
    ]
    return state.model_copy(update={"mentors": new_mentors, "active_mentor_id": next_id, "updated_at": _now_iso()}), None


def repeat_mentor_company_wide(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    """Resets every employee's progress on a graduated track and puts
    the whole company back through it."""
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if mentor.status != "graduated":
        return state, "Only a graduated track can be repeated."
    new_mentors = [m.model_copy(update={"status": "active", "company_graduated_sim_day": None}) if m.id == mentor_id else m for m in state.mentors]
    new_progress_map = {aid: dict(m) for aid, m in state.progress.items()}
    for agent_id in STUDENT_AGENT_IDS:
        new_progress_map.setdefault(agent_id, {})[mentor_id] = FoundationalMentorProgress(mentorId=mentor_id)
    return state.model_copy(update={"mentors": new_mentors, "progress": new_progress_map, "active_mentor_id": mentor_id, "updated_at": _now_iso()}), None


# --- The CEO's own, entirely optional personal learning (ceo_progress) ---
# Never required, never gates real company progress — see module
# docstring. Grading here still uses the real hidden correct_index, the
# same as the original CEO-facing design, since a human player actually
# does pick an option.


def mark_ceo_lesson_viewed(state: FoundationalMentorState, mentor_id: FoundationalMentorId, lesson_id: str) -> FoundationalMentorState:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None or _lesson_by_id(mentor, lesson_id) is None:
        return state
    progress = state.ceo_progress.get(mentor_id) or FoundationalMentorProgress(mentorId=mentor_id)
    if lesson_id in progress.viewed_lesson_ids:
        return state
    new_progress = progress.model_copy(update={"viewed_lesson_ids": [*progress.viewed_lesson_ids, lesson_id]})
    return state.model_copy(update={"ceo_progress": {**state.ceo_progress, mentor_id: new_progress}, "updated_at": _now_iso()})


def grade_ceo_lesson_quiz(
    state: FoundationalMentorState,
    mentor_id: FoundationalMentorId,
    lesson_id: str,
    selected_index: int,
) -> tuple[FoundationalMentorState, bool, int, str] | None:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return None
    lesson = _lesson_by_id(mentor, lesson_id)
    if lesson is None:
        return None

    spec = next((s for s in _specs_for(mentor_id) if s.id == lesson_id), None)
    if spec is not None:
        correct_index = spec.correct_index
    elif lesson_id in state.custom_lesson_answers:
        correct_index = state.custom_lesson_answers[lesson_id]
    else:
        return None
    correct_option = lesson.quiz_options[correct_index]

    correct = selected_index == correct_index
    progress = state.ceo_progress.get(mentor_id) or FoundationalMentorProgress(mentorId=mentor_id)
    completed_ids = _add_once(progress.completed_lesson_ids, lesson_id) if correct else progress.completed_lesson_ids
    new_progress = progress.model_copy(
        update={
            "completed_lesson_ids": completed_ids,
            "quiz_attempts": progress.quiz_attempts + 1,
            "correct_quiz_attempts": progress.correct_quiz_attempts + (1 if correct else 0),
        }
    )
    new_state = state.model_copy(update={"ceo_progress": {**state.ceo_progress, mentor_id: new_progress}, "updated_at": _now_iso()})
    return new_state, correct, correct_index, correct_option


def add_resource(
    state: FoundationalMentorState,
    mentor_id: FoundationalMentorId,
    *,
    title: str,
    url: str | None,
    resource_type: FoundationalResourceType,
) -> tuple[FoundationalMentorState, str | None]:
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    clean_title = title.strip()
    if not clean_title:
        return state, "Resource title cannot be empty."
    if len(mentor.resources) >= MAX_RESOURCES_PER_MENTOR:
        return state, f"This track already has the maximum of {MAX_RESOURCES_PER_MENTOR} bookmarked resources."
    resource = FoundationalMentorResource(
        id=f"resource-{mentor_id}-{len(mentor.resources)}",
        title=clean_title,
        url=url,
        resourceType=resource_type,
        addedAt=_now_iso(),
    )
    new_mentors = [m.model_copy(update={"resources": [*m.resources, resource]}) if m.id == mentor_id else m for m in state.mentors]
    return state.model_copy(update={"mentors": new_mentors, "updated_at": _now_iso()}), None


# --- Mentor Lab: real, in-product Foundational Mentor Library expansion ---
# The CEO-facing version of what this module's own docstring originally
# described as a code-only scope cut ("add an id, roadmap entry, and
# lesson tuple to this file"). Every mentor/lesson added this way is
# real, persisted state — never a fabricated placeholder.


def add_custom_mentor(state: FoundationalMentorState, *, name: str, track_label: str, focus_areas: list[str]) -> tuple[FoundationalMentorState, str | None, str | None]:
    """Appends a new, CEO-authored mentor track to the end of the real
    roadmap. Starts `"planned"` with zero lessons — exactly like the
    original 5 roadmap-only tracks — until the CEO adds real lesson
    content via `add_custom_lesson`. Returns (state, new_mentor_id, error)."""
    custom_count = sum(1 for m in state.mentors if m.id not in _ROADMAP_FOCUS)
    if custom_count >= MAX_CUSTOM_MENTORS:
        return state, None, f"The Mentor Library already has the maximum of {MAX_CUSTOM_MENTORS} CEO-added tracks."
    clean_name = name.strip()
    clean_label = track_label.strip()
    clean_focus = [f.strip() for f in focus_areas if f.strip()]
    if not clean_name:
        return state, None, "Mentor name cannot be empty."
    if not clean_label:
        return state, None, "Track label cannot be empty."
    if not clean_focus:
        return state, None, "At least one focus area is required."

    slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-") or "mentor"
    existing_ids = {m.id for m in state.mentors}
    mentor_id = slug
    suffix = 1
    while mentor_id in existing_ids:
        suffix += 1
        mentor_id = f"{slug}-{suffix}"

    new_mentor = FoundationalMentorProfile(
        id=mentor_id,
        name=clean_name,
        trackLabel=clean_label,
        focusAreas=clean_focus,
        contentNote=_CUSTOM_CONTENT_NOTE,
        status="planned",
        lessons=[],
        resources=[],
    )
    new_state = state.model_copy(
        update={"mentors": [*state.mentors, new_mentor], "roadmap_order": [*state.roadmap_order, mentor_id], "updated_at": _now_iso()}
    )
    return new_state, mentor_id, None


def add_custom_lesson(
    state: FoundationalMentorState,
    mentor_id: FoundationalMentorId,
    *,
    title: str,
    simple_explanation: str,
    deeper_explanation: str,
    quiz_question: str,
    quiz_options: list[str],
    correct_index: int,
) -> tuple[FoundationalMentorState, str | None]:
    """A real, CEO-authored lesson — for any mentor, built-in or custom.
    Employee auto-progression (`tick_employee_progress`) already works
    generically over `mentor.lessons` with no changes needed; only the
    CEO's own optional quiz-taking (`grade_ceo_lesson_quiz`) needs the
    hidden answer key, stored in `state.custom_lesson_answers`."""
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if len(mentor.lessons) >= MAX_LESSONS_PER_MENTOR:
        return state, f"This track already has the maximum of {MAX_LESSONS_PER_MENTOR} lessons."
    clean_title = title.strip()
    clean_question = quiz_question.strip()
    clean_options = [o.strip() for o in quiz_options]
    if not clean_title:
        return state, "Lesson title cannot be empty."
    if not clean_question:
        return state, "Quiz question cannot be empty."
    if len(clean_options) != 4 or any(not o for o in clean_options):
        return state, "Exactly 4 non-empty quiz options are required."
    if not 0 <= correct_index < 4:
        return state, "correctIndex must be between 0 and 3."

    lesson_id = f"custom-{mentor_id}-{len(mentor.lessons)}"
    new_lesson = FoundationalMentorLesson(
        id=lesson_id,
        order=len(mentor.lessons) + 1,
        title=clean_title,
        simpleExplanation=simple_explanation.strip(),
        deeperExplanation=deeper_explanation.strip(),
        quizQuestion=clean_question,
        quizOptions=clean_options,
    )
    new_mentors = [m.model_copy(update={"lessons": [*m.lessons, new_lesson]}) if m.id == mentor_id else m for m in state.mentors]
    new_answers = {**state.custom_lesson_answers, lesson_id: correct_index}
    return state.model_copy(update={"mentors": new_mentors, "custom_lesson_answers": new_answers, "updated_at": _now_iso()}), None


def set_active_mentor(state: FoundationalMentorState, mentor_id: FoundationalMentorId) -> tuple[FoundationalMentorState, str | None]:
    """A real CEO override — jumps company-wide focus straight to any
    mentor with real lesson content (built-in or custom) without waiting
    for the roadmap's automatic sequential unlock. Whatever was active
    before is paused, not discarded — same as skip_to_next_mentor."""
    mentor = _mentor_by_id(state, mentor_id)
    if mentor is None:
        return state, "Unknown mentor track."
    if not mentor.lessons:
        return state, "This track has no lessons yet — add at least one before making it active."
    if mentor.id == state.active_mentor_id:
        return state, "This track is already the active one."

    new_mentors = list(state.mentors)
    if state.active_mentor_id is not None:
        previous = _mentor_by_id(state, state.active_mentor_id)
        if previous is not None and previous.status == "active":
            new_mentors = [m.model_copy(update={"status": "paused"}) if m.id == previous.id else m for m in new_mentors]
    new_mentors = [m.model_copy(update={"status": "active"}) if m.id == mentor_id else m for m in new_mentors]
    return state.model_copy(update={"mentors": new_mentors, "active_mentor_id": mentor_id, "updated_at": _now_iso()}), None
