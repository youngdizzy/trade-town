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

WHAT'S REAL VS. ROADMAP (unchanged): only the "tjr" track ships real
lesson content (8 original lessons — see `_TJR_LESSONS` below, expanded
from the original 6 to match this revision's wider TJR focus-area list).
The
other five named tracks are seeded as real, ordered, named roadmap
entries — real display name, real track label, real focus-area topics —
but deliberately ship with zero lessons and `status: "planned"` rather
than five fabricated placeholder shells. `_LESSON_SPECS_BY_MENTOR` is
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
)

_LESSON_SPECS_BY_MENTOR: dict[FoundationalMentorId, tuple[_LessonSpec, ...]] = {
    "tjr": _TJR_LESSONS,
    "market_intelligence": _MARKET_INTELLIGENCE_LESSONS,
    # The other five roadmap tracks intentionally have no entry here yet —
    # see this module's docstring. Adding real content for one of them
    # later is exactly: write its own _LessonSpec tuple and add it here.
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
# signal this codebase has none of yet.


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
