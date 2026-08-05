# Chapter 63 — Executive Performance & Company Health Engine

**Status:** Substantially implemented. The Company Health Score
(`app/company_health.py`), the seven-metric Company Score
(`app/company_score.py`), Department Scorecards (`app/executive_intelligence.py`'s
Weekly Self-Evaluation), and the Performance Review Cycle
(`app/executive_review.py`'s monthly Executive Review) are all real,
backend and frontend, and predate this chapter — this pass is
documentation-only, no code changes. Two sections are genuine, partial
gaps: Early Warning System (a few real signals exist but no dedicated
proactive-alert subsystem unifies them) and Benchmarking (one real
period-over-period delta exists; historical-period and industry-standard
comparison do not). See [Volume 9's chapter template](README.md) for
what every section below must contain, and the Implementation Notes at
the bottom for exactly what's real today.

## Executive Summary

A company that can't measure its own health can't manage it. TradeTown
should know, at any moment, exactly how the organization is doing — not
just whether trades are winning, but whether the company itself is
functioning well. **Researched first, and the finding matches Chapters
61/62's own precedent**: almost everything this brief asks for already
exists as a real, working system, in most cases from earlier in this
project's history (v0.5's Company Score, v0.7 Feature 23's Company
Health, v0.7 Feature 50's Executive Intelligence redesign). This
chapter's real job is naming and connecting what's already built, and
honestly scoping the two pieces that aren't.

## Mission

Give the CEO one clear, always-current, always-explainable answer to
"how is the company actually doing?" — broken down by department,
tracked over time, and never a single opaque number.

## Philosophy

Every sub-score must be a real, named, checkable formula over real
state — never a black box, and never fabricated to look more precise
than the underlying data supports. A department with nothing to report
this week reads as an honest "no real decisions yet," not a
silently-invented number. Health is diagnosed continuously, not
discovered after something has already gone wrong.

## Responsibilities

**Owns:** the Company Health Score and its two tiers (Operational,
Executive); the seven-metric Company Score; Department Scorecards
(Weekly Self-Evaluation); the monthly Executive Review.

**Does NOT own** (see Appendix E): Trade Execution, Risk Veto Authority
(Sentinel/Guardian, unchanged), Portfolio Management, the Executive
Intelligence Network's own per-proposal department opinions (Chapter
50/`app/executive_intelligence.py`'s `generate_department_opinions()` —
this chapter's Department Scorecards *consume* those opinions
retrospectively over a trailing week, they do not generate them).

## Ownership

Every one of these already exists and is already real:

| System | Module | What it really does |
|---|---|---|
| Company Health Score | `app/company_health.py` | `compute_company_health()` — eleven real "Operational" sub-scores (v0.7 Feature 23: Operational Stability, Department Efficiency, Employee Morale, Research Progress, Capital Health, Resource Usage, Reputation, Technology Level, Office Expansion, Education Progress, Team Chemistry) producing `overall`/`tier`, plus ten more real "Executive" sub-scores (v0.7 Feature 50 Part 2/3: Decision Quality, Executive Alignment, Risk Governance, Simulation Coverage, Department Consensus, Self-Evaluation Health, Institutional Memory, Innovation Velocity, Talent Development, Founder Oversight) producing `executiveOverall`/`executiveTier`, and `combinedOverall`/`combinedTier` — an equal blend of the two, the true redesigned headline number. A real `recommendations` list names the two (or more, on a tie) weakest sub-scores in plain language, never generic filler. |
| Company Score | `app/company_score.py` | `compute_company_score()` — a different, older (v0.5) seven-metric read answering "is the company *performing* well" rather than Company Health's "is the company *healthy to keep operating*": Research Quality, Decision Quality, Risk Management, Paper Trading Performance, Team Coordination, Knowledge Growth, Simulation Success. A plain unweighted mean, no hidden weighting. |
| Department Scorecards | `app/executive_intelligence.py`'s `generate_weekly_self_evaluations()` | One real `DepartmentSelfEvaluation` per department (all nine Executive Intelligence Network roles: research, quant, risk, simulation, decision_intelligence, coach, founders, devils_advocate, market_intelligence) per week, built entirely from that department's own real `DepartmentOpinion` entries already logged to the Executive Meeting Log over the trailing 7 sim days — `decisionsReviewed`, a real average-confidence `score`, `strengths`/`improvementAreas` derived from real agree/concern counts. A department with zero logged opinions that week gets an honest neutral 50.0 and "No real decisions reached the network this week" rather than a fabricated evaluation. |
| Performance Review Cycle | `app/executive_review.py`'s `generate_executive_review()` | The CIO's real monthly Executive Review, generated on the same monthly cadence as the Coach's own `CoachReport` (see `app/nexus.py`'s monthly-cadence gate). Real department activity ranking, research/knowledge counts, conflict counts (real Debate Room challenge-stance turns), major events, flags, a real `companyScoreChange` period-over-period delta, long-term goals framed from real configured state, and Knowledge Connections (real "this builds on that" callbacks between same-category research/Academy items). |
| Executive Meeting Log | `app/executive_intelligence.py`'s `generate_meeting_log_entry()` | The permanent record every Department Scorecard and every Executive Review's own conflict/activity counts are built from — one real entry per actual `resolve_proposal()` call, carrying that decision's real Decision Grade and whether the Executive Network's own recommendation agreed with the CEO's actual choice. |
| Frontend | Command Center's COMPANY tab | Already shipped — real Company Health (via the COMPANY tab's health card) and the Operating Mode toggle, verified live in this session's own Playwright pass (`commandCenter.spec.ts` — "Company tab shows real Company Health, Market Environment, and a working Operating Mode toggle"). |

## Inputs

Every input the brief names is already real: risk warnings
(`RiskWarning`, Sentinel/Guardian), agent locations/mood
(`AgentState`), research completion (`ResearchItem`), portfolio P&L
(`PaperPortfolio`), agent energy (`AgentEnergy`), Hall of Fame count
(`HallOfFameEntry`), Signal Calibration level
(`SignalCalibrationState`), watchlist expansion (`app/watchlist.py`'s
`EXTRA_SYMBOL_POOL`), education progress (`EducationProgress`), Debate
stance history (`Debate`), Decision Grade (`TradeDecision`), Executive
Meeting Log agreement (`ExecutiveMeetingLogEntry.networkAgreed`),
Gatekeeper rejection ratio (`GatekeeperRejection`), department
self-evaluations (`DepartmentSelfEvaluation`), Company Wisdom Score
(`app/wisdom.py`), Innovation Points (`InnovationState`), Foundational
Mentor graduation rates (`FoundationalMentorState`), Founder Council
session count (`FounderCouncilSession`). **Not a real input anywhere:**
any externally-sourced industry benchmark — no such data source exists
in this codebase (see Benchmarking below).

## Outputs

`CompanyHealth` (eleven Operational sub-scores + ten Executive
sub-scores + three headline overall/tier pairs + recommendations),
`CompanyScore` (seven metrics + overall), `DepartmentSelfEvaluation` (one
per department per week), `ExecutiveReview` (one per month).

## Internal Workflow

```
Real per-tick state (risk warnings, agent state, research, portfolio,
energy, hall of fame, calibration, watchlist, education, debates)
        v
compute_company_health() — eleven Operational + ten Executive formulas,
each a small named function reading one real signal
        v
overall/tier (unchanged since v0.7 Feature 23, every existing consumer
keeps working identically) + executiveOverall/executiveTier (new) +
combinedOverall/combinedTier (equal blend, the true headline)
        v
recommendations — the two weakest real sub-scores, named in plain
language, only surfaced when below 70.0
        v
[weekly] generate_weekly_self_evaluations() over the trailing 7 sim
days' real Executive Meeting Log entries -> nine real DepartmentSelfEvaluations
        v
[monthly] generate_executive_review() over cumulative capped-history
lists + the current CompanyHealth/CompanyScore reading -> one real
ExecutiveReview, alongside the Coach's own monthly CoachReport and the
Founder Council's own monthly session
```

## Decision Logic

Every sub-score is Evidence-based by construction — a named formula over
one real, already-tracked signal, never an LLM judgment call and never a
weighted composite with hidden coefficients (Company Score's `overall`
is a plain mean; Company Health's three headline numbers are a plain
mean and an equal blend, both stated explicitly in `app/company_health.py`'s
own module docstring). Where a real signal is genuinely absent (an
unlisted department having zero Executive Meeting Log entries this week,
a fresh company with zero closed trades), the honest fallback is a
neutral 50.0, never a fabricated number and never a 0 that would read as
"failing" for a company that simply hasn't been measured yet — the same
convention `app/analytics.py`'s own module docstring already established
for exactly this reason.

## Department Cooperation

**Receives from:** every department in the Executive Intelligence
Network (research, quant, risk, simulation, decision_intelligence,
coach, founders, devils_advocate, market_intelligence) via their own
real `DepartmentOpinion` entries; the Academy, Reasoning Lab, Reflection
Chamber, Founder Council, and Innovation Lab via Company Health's
Executive-tier sub-scores. **Sends to:** the CEO (Company Health/Company
Score readings, Department Scorecards, the monthly Executive Review);
the Founders (`app/founders.py`'s `compute_founder_state()` reads
`company_health_tier` directly — Legendary Status permanently unlocks
the first time it reaches `"excellent"`); Company Priorities (the
Operating Mode/Company Priority CEO settings read Company Health as one
of their own inputs).

## CEO Controls

| Control | Status |
|---|---|
| Company Health visibility | **Already real** — the COMPANY tab, always on, no configuration needed. |
| Weekly Self-Evaluation cadence | **Not built** — the 7-sim-day window (`SELF_EVAL_WINDOW_DAYS`) is a fixed constant, matching the Reflection Chamber's own weekly cadence. A real, closeable "promote a constant" candidate, same pattern as Chapters 61/62's own CEO Controls passes, not attempted here. |
| Executive Review cadence | **Not built** — fixed monthly, tied to the same cadence gate as the Coach's own monthly report. |
| Company Health tier thresholds | **Not built** — `_TIER_THRESHOLDS` (85/70/50/30) are fixed constants in `app/company_health.py`. A real, closeable "promote a constant" candidate. |
| Early Warning thresholds | **Not built** — see Early Warning System below; no dedicated threshold-crossing alert subsystem exists to configure. |
| Benchmark period selection | **Not built** — see Benchmarking below; only one fixed period-over-period comparison exists today. |

Every "Not built" row above is a genuine, buildable future slice in the
exact same pattern Chapters 57–62 already used to close comparable gaps
— none require inventing a signal this codebase doesn't have, just
promoting an existing fixed constant to a CEO-configurable `RiskLimits`
field.

## Learning System

Already real, per real event: `app/wisdom.py`'s weekly/monthly
`ReflectionSession` already asks what happened and why against the exact
same signals Company Health's Executive tier reads; `DepartmentSelfEvaluation`'s
own `improvementAreas` field is itself a real, evidence-backed
self-critique generated fresh every week rather than a static
description. What's not yet real: nothing currently *acts* on a
Department Scorecard automatically (e.g., no department's future
behavior changes because its own score was low) — scorecards are
diagnostic and CEO-visible, never a trigger for an automatic system
change, matching the same "recommend, never auto-correct" boundary every
other chapter in this volume already respects.

## KPIs

Real and already computed: Company Health's own three overall numbers
and every one of their 21 sub-scores; Company Score's seven metrics;
`companyScoreChange` (the one real period-over-period figure, already
computed in `generate_executive_review()`); Department Scorecard scores
over time (real, since every weekly `DepartmentSelfEvaluation` is
retained up to `MAX_SELF_EVAL_HISTORY = 250`, a genuine trend a frontend
view could chart from real historical data already on record).

## Reports

Already real: the COMPANY tab's Company Health card; the monthly
`ExecutiveReview` (summary, flags, recommendations, long-term goals,
knowledge connections); the weekly `DepartmentSelfEvaluation` set,
recorded to `app/state.py` history. **Not yet built:** a single unified
frontend view combining Department Scorecards with the Executive Review
in one screen — both are real and API-accessible today, only the
combined presentation is missing.

## Early Warning System

**Partially real — the honest boundary matters here.** Two real signals
already function as informal early warnings: `app/executive_review.py`'s
`_flags()` names any research item stuck `in_progress` below a 20.0
confidence floor, and separately flags when `CompanyHealth.tier` reads
`"needs_attention"` or `"critical"`; Sentinel/Guardian's real
`RiskWarning`s already surface risk-specific alerts independently. What
does **not** exist: a dedicated subsystem that unifies these (plus
Department Scorecard score drops, Company Score declines, and any other
real threshold crossing) into one proactive, CEO-facing Early Warning
feed with its own configurable sensitivity — today each signal surfaces
in its own separate place (the Executive Review's flags list, the RISK
panel's warnings), never a single consolidated alert stream. This is a
real, scoped, buildable future chapter slice — every underlying signal
it would consume already exists — not attempted in this pass.

## Benchmarking

**Mostly not real — do not overstate this.** The one genuine benchmark
this codebase computes is `ExecutiveReview.companyScoreChange`: a real
delta against the *immediately previous* monthly review's own stored
score. That is the entire real benchmarking surface today. **Not real:**
comparison against a chosen historical period (e.g., "this month vs. 3
months ago" — no review is ever selected by anything other than "most
recent"); comparison against any industry standard or external
benchmark (no such data source exists anywhere in this codebase, the
same absence Chapter 61's own Future Expansion section already
documented for vector/semantic search — nothing external is fabricated
here either). A genuine future slice would extend `generate_executive_review()`
to accept an arbitrary prior review from `ExecutiveReview` history (already
retained up to `MAX_EXECUTIVE_REVIEWS = 20`) rather than only ever the
immediately-previous one — real data already exists to build this from.

## Safety Systems

Already real: every sub-score and scorecard is read-only and diagnostic
— nothing in this chapter ever changes company behavior automatically.
`FounderState.retired` is the one real, permanent, one-way consequence
of a Company Health reading (see Department Cooperation) — it never
reverts if health later dips, the same "a crossed milestone stays
crossed" convention `app/hall_of_fame.py` already established.

## Dependencies

Chapter 50/`app/executive_intelligence.py` (Executive Intelligence
Network — the real per-department opinions Department Scorecards
aggregate), Chapter 39/`app/founders.py` (Founders — Legendary Status'
real trigger), `app/wisdom.py` (Institutional Learning — several
Executive-tier Company Health sub-scores read it directly),
`app/coach.py` (the CoachReport the monthly Executive Review is
generated alongside).

## Connected Features

Chapter 61 (Knowledge Graph & Company Memory — `executive_review` is
already a real Knowledge Graph node type, so a future Chapter 63 graph
extension mirroring Chapter 61's own "trade"/"case_study"/"strategy"
additions is a natural next step, not attempted here). Chapter 64
(Executive Strategic Planning & Goal Management — its own SMART
Objectives and Milestone Tracking would be natural future consumers of
this chapter's real Company Health trend data as a goal-progress
signal).

## Future Expansion

A unified Early Warning feed and genuine multi-period Benchmarking (both
above) are the two real, scoped next slices. AI-generated narrative
health summaries, predictive health forecasting, and true
industry-benchmark ingestion would all require either an LLM dependency
or an external data source this codebase does not have — not invented
or stubbed here, the same honesty boundary every other chapter in this
volume already holds.

## Company Principle

A company that cannot see itself clearly cannot improve. TradeTown
measures its own health continuously, names its own weaknesses in plain
language, and never lets a single opaque number stand in for a real,
checkable answer.

## Implementation Notes

**What's real today:** the overwhelming majority of this chapter — the
Company Health Score's full two-tier system (`app/company_health.py`),
the Company Score (`app/company_score.py`), Department Scorecards via
Weekly Self-Evaluation (`app/executive_intelligence.py`), the monthly
Executive Review (`app/executive_review.py`), and the Executive Meeting
Log everything else is built from. This is the same "opposite research
outcome" pattern Chapters 61 and 62 already established for this volume:
the brief describes a system that is already, in large part, built. No
code was written for this chapter — it is a documentation-only pass,
consistent with this session's convention of writing a Design Bible
chapter first and waiting for an explicit implementation instruction.

**What's genuinely and honestly incomplete:** a unified Early Warning
feed (today's warnings are real but scattered across the Executive
Review's flags and Sentinel/Guardian's RiskWarnings, never consolidated);
genuine multi-period or industry-standard Benchmarking (today only one
real immediately-previous-period delta exists); five CEO Controls rows
that are real, closeable "promote a constant" candidates in the exact
pattern already used for Chapters 57–62, not yet attempted (Weekly
Self-Evaluation cadence, Executive Review cadence, Company Health tier
thresholds, Early Warning thresholds, Benchmark period selection).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step, satisfied by
this pass. Given how much of this chapter is already real, a future
implementation pass would likely be small — the CEO Controls
"promote a constant" rows first (lowest risk, established pattern),
Benchmarking's multi-period extension second (real data already
retained, no new storage needed), and the Early Warning consolidation
last (the only piece requiring a genuinely new subsystem, however small).
