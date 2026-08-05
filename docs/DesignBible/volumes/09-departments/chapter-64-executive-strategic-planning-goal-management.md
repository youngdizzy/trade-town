# Chapter 64 — Executive Strategic Planning & Goal Management Engine

**Status:** Three real slices implemented (backend + frontend), following
this chapter's own recommended sequencing: a CEO-authored `Goal` naming
one real, already-computed metric and a target value, with real
progress recomputed every tick; Milestone Tracking, three real 25/50/75%
checkpoints on that same progress; and the Executive Priority Engine,
ranking active goals by a real urgency formula. Only Resource Allocation
remains explicitly out of scope, named below — it depends on the
Priority Engine existing first. See
[Volume 9's chapter template](README.md) for what every section below
must contain, and the Implementation Notes at the bottom for exactly
what's real today versus still target design.

## Executive Summary

A company without real goals drifts. TradeTown should be able to set a
real objective, track real progress toward it, and know honestly whether
it's on pace — not as flavor text, but as a genuine system a CEO can
configure and check. **Researched first, and unlike Chapters 61–63, this
is a real gap, not an already-built system under a different name.**
Three things in this codebase brush up against "strategic planning" —
`CompanyPriority` (a real CEO-set operating stance that biases a handful
of real levers), the Capital Priority Engine (Chapter 59, which ranks
*trade proposals*, not company goals), and `ExecutiveReview`'s own
`_long_term_goals()` (which generates one or two real but static goal
*sentences* from current state, with no tracking, deadline, or progress
bar attached to them). None of the three is a goal-management system.
This chapter is honestly scoped as target design because of that.

## Mission

Give the CEO a real way to set a small number of concrete company
objectives, see honest progress toward each one measured from real data,
and understand how the company's limited capital and attention are being
allocated across them.

## Philosophy

A goal without a real, checkable progress measure is just a wish. Every
objective this chapter would track must be backed by a real number this
codebase already computes or can honestly compute — never a fabricated
percentage, never an invented "on track" label without a real metric
behind it. Fewer, real goals beat many vague ones.

## Responsibilities

**Would own:** defining and tracking company-level goals (SMART
Objectives), an Executive Priority Engine ranking those goals (distinct
from Chapter 59's *trade-proposal* Priority Score — see Ownership),
Resource Allocation recommendations across goals, Milestone Tracking, and
a Strategic Review Cycle.

**Does NOT own** (see Appendix E): ranking the pending trade-proposal
queue (Chapter 59 — a different kind of priority entirely, already
built, not duplicated here), Trade Execution, Risk Approval, Portfolio
Management, Company Health measurement (Chapter 63 — this chapter would
*consume* Company Health trends as one real goal-progress signal, never
recompute them).

## Ownership

`app/goals.py` (`Goal`, `Milestone`, `GoalPriority` schemas; `create_goal()`,
`tick_goal()`/`tick_goals()`, `cancel_goal()`, `compute_goal_priority()`,
`rank_goals_by_priority()`), `app/routers/goals.py` (`POST /api/goals/create`,
`POST /api/goals/cancel`, `GET /api/goals/priorities`), and the COMPANY
tab's Company Goals card (`CompanyPanel.tsx`) are now real and
authoritative over everything this chapter owns. Three real, adjacent
systems were checked first and remain explicitly separate, not reused:

| Brief concept | Closest real system | Why it is NOT the same thing |
|---|---|---|
| Company Priority (a "strategic stance") | `SettingsState.company_priority` (`CompanyPriority`: `"balanced"`/`"learning"`/`"research"`/`"risk_reduction"`) | A real, CEO-set, persistent toggle that biases exactly one real lever per value (see `app/nexus.py`'s `_effective_risk_limits()`, `PRIORITY_KNOWLEDGE_MULTIPLIER`, `PRIORITY_RESEARCH_SPEED_MULTIPLIER`). This is the closest real thing to a "strategic priority" in the whole codebase — but it is one global stance with four fixed values, not a set of CEO-authored goals with their own text, deadlines, or progress. |
| SMART Objectives / goal text | `app/executive_review.py`'s `_long_term_goals()` | Generates one or two real sentences ("Hold max drawdown under X%, the standing risk limit," "Advance the Academy past tier Y") from real current state, every month, as part of the Executive Review. These are real and non-fabricated, but they are regenerated fresh each time from a fixed, hardcoded rule set — nothing is ever CEO-authored, stored, tracked over time, or marked complete. Not reused or extended by `app/goals.py`, which remains an entirely separate, CEO-authored object. |
| Chapter 59's trade-proposal Priority Score | `app/capital_priority.py`'s `rank_trade_proposals()` | Ranks *pending trade proposals* by `WarRoomSession.decisionScore`, a composite built entirely from trade-specific signals (Expected Value, Evidence, Risk, Portfolio Compatibility, ...) that don't exist for a goal. `app/goals.py`'s own `compute_goal_priority()` is a real, separate formula over goal-specific signals (distance-to-target, real deadline pace) — never a reuse of Chapter 59's engine, per this chapter's own Decision Logic below. |

## Inputs

Every input a real future implementation could honestly use already
exists: `CompanyHealth`/`CompanyScore` (Chapter 63, as a goal-progress
signal), `RiskLimits` (current risk posture, a real constraint on
resource allocation), `PaperPortfolio` (real capital available to
allocate), `CompanyPriority` (the real existing "stance" a goal could be
framed against), `ExecutiveReview` history (real month-over-month
company state to measure progress against). **Not a real input
anywhere:** anything describing a CEO-authored goal itself — no schema,
no storage, no input surface exists yet.

## Outputs

**Built:** a real `Goal` object (title, category, target metric, target
value, current value, progress %, created/deadline sim day, status,
timestamps, milestones); a real ranked list of active goals with real
priority scores (`GoalPriority`, via `GET /api/goals/priorities`) — see
`app/goals.py`. **Not built:** a Resource Allocation recommendation —
it depends on the Priority Engine existing first to have anything real
to allocate against, per this chapter's own recommended
smallest-slice-first sequencing.

## Internal Workflow

**Built, matching the honest workflow this section originally
described:** CEO defines a goal naming one real target metric
(`app/goals.py`'s `create_goal()`, validated by `validate_target_value()`
against that metric's own real ceiling) → `resolve_metric_value()`
reads the one already-real number that metric maps to (Company Health
combined score, Company Score, portfolio return %, or Academy level —
not every conceivable goal has a real metric to attach to, so only these
four are offered) → `tick_goals()` recomputes every active goal's real
progress every tick, alongside `company_health`/`company_score` in
`app/nexus.py`'s `tick()` → a goal transitions to `completed` the moment
its real current value reaches its target, or to `expired` if a real
deadline passes unmet — both permanent, one-way transitions, the same
"a crossed milestone stays crossed" convention `app/hall_of_fame.py`
already establishes. **Not built:** the Strategic Review Cycle itself
(a periodic report over goal progress) — today's real workflow updates
every goal silently every tick; nothing yet surfaces a periodic summary
of that progress the way Chapter 63's monthly Executive Review does for
company performance.

## Decision Logic

**Built.** `app/goals.py`'s `compute_goal_priority()` is the real,
named formula predicted here: urgency-by-deadline combined with real
distance-to-target, deliberately not a copy of Chapter 59's
trade-proposal Decision Score (see Ownership). Two real cases, both
built entirely from fields a `Goal` already carries: with no real
deadline, the score is `100 - progressPct` alone — an open-ended goal
still deserves attention proportional to how far it has to go, with no
time pressure driving it; with a real deadline, the score is the real
pace required per day to hit it (`remainingPct / daysRemaining`),
clamped against a stated, transparent ceiling
(`MAX_URGENCY_PACE_PCT_PER_DAY = 5.0` — a goal needing 5+ percentage
points of real progress per real remaining day reads as maximally
urgent) and scaled into the same 0-100 range as the no-deadline case.
Never a hidden weighting — the same "no black-box composite" convention
every other scoring engine in this codebase already follows.

## Department Cooperation

**Would receive from:** Chapter 63 (Company Health/Company Score as real
progress signals), Chapter 56 (Portfolio Intelligence, for real capital
available to allocate), Chapter 59 (Capital Priority Engine — explicitly
NOT reused directly, per Ownership, but the same module could sit
alongside it). **Would send to:** the CEO (goal progress, resource
allocation recommendations); Company Priority's existing four-value
stance could remain the simpler, always-on default even after this
chapter exists, the same way Chapter 57's hard risk floor stays active
underneath Chapter 59's softer, opt-in reserve target.

## CEO Controls

| Control | Status |
|---|---|
| Goal Categories / SMART Objective authoring | **Built** — a real "Company Goals" card in the COMPANY tab: title, category (growth/risk/research/trading/operations), one of four real target metrics, target value, optional deadline. `POST /api/goals/create`, validated server-side (`app/goals.py`'s `validate_target_value()`; a positive target within that metric's own real ceiling, a future deadline). |
| Cancel an active goal | **Built** — `POST /api/goals/cancel`, a real ✕ control per active goal in the same card. |
| Executive Priority Engine (goal ranking) | **Built** — `GET /api/goals/priorities` returns every active goal's real `GoalPriority` (score, remaining %, days left), computed fresh per request (`app/goals.py`'s `rank_goals_by_priority()`), never a reuse of Chapter 59's engine (see Ownership/Decision Logic). The COMPANY tab's Company Goals card now orders active goals by this real score and shows a PRIORITY badge plus real days-remaining per goal. |
| Resource Allocation targets | **Not built** — no goal-level capital-allocation concept exists; was the one piece still explicitly deferred, since it depends on the Priority Engine existing first. |
| Milestone definitions | **Built** — every goal automatically gets three real checkpoints at 25%/50%/75% of its own real progress (`app/goals.py`'s `MILESTONE_THRESHOLDS`), each permanently marked reached the moment real progress crosses it (checked both at creation, so a goal can honestly start past a milestone, and on every tick). Rendered as filled/hollow markers on each Goal card. No CEO configuration of the thresholds themselves yet — a real future "promote a constant" candidate, same pattern as Chapter 63's tier thresholds. |
| Strategic Review cadence | **Not built** — no periodic review report exists for this chapter's own concept yet (distinct from Chapter 63's real monthly Executive Review, which reviews company *performance*, not CEO-authored *goals*). |
| Company Priority (existing four-value stance) | **Already real** — `SettingsState.companyPriority`, CEO-configurable today via the existing RISK/Company panel, unrelated to this chapter's own goal system except as a possible future input. |

## Learning System

Not real yet. A genuine future version would ask, per goal, "did the
company's real progress metric move the way the goal predicted, and by
how much" — the same "wait for real time to pass, then check real data"
convention every other Learning System section in this volume already
uses, applied to whichever real metric that goal was actually attached
to.

## KPIs

**Built:** Goal Completion Rate is now honestly computable — every
`Goal`'s own real `status` (`completed` vs. `expired`/`cancelled`) is a
real, checkable outcome, and `progressPct` is a real, continuously
updated number. Milestone Hit Rate is now honestly computable too —
every `Milestone`'s own real `reached`/`reachedAt` is a real, checkable,
timestamped fact. **Still not honestly computable:** Resource Allocation
Efficiency (would require the same kind of real before/after portfolio
comparison Chapter 60's own KPIs section already flags as needing a new
ledger).

## Reports

Not real yet. A Strategic Review Report is the natural first real
report, mirroring Chapter 63's monthly `ExecutiveReview` structure but
over CEO-authored goals instead of overall company performance.

## Safety Systems

Not real yet, but the discipline is already established by every other
chapter in this volume: any future Resource Allocation *recommendation*
this chapter produces must never auto-move capital — the same
recommend-only boundary Chapter 60's Capital Rotation and Chapter 59's
Priority Score both already respect. No goal should ever be marked
complete by anything other than a real, checkable metric crossing its
real target.

## Dependencies

Chapter 63 (Executive Performance & Company Health Engine — the real
progress signals this chapter would consume), Chapter 59 (Capital
Priority & Opportunity Cost Engine — a structurally different priority
system this chapter must not duplicate, per Ownership), Chapter 56
(Enterprise Portfolio Intelligence — real capital data for allocation).
**A note on the brief's own named dependency:** "Chapter 53 —
Probabilistic Trading Philosophy" does not exist anywhere in this
codebase or Design Bible under that number or title — the same
non-existent reference already checked and flagged in Chapters 58, 59,
and 60's own Dependencies sections; this brief repeats the same citation
and it is no more real here than there.

## Connected Features

Chapter 63 (would supply the real metrics most goals are measured
against). Chapter 60 (Portfolio Rebalancing — itself still target
design; a future Resource Allocation recommendation here and a future
Capital Rotation recommendation there would both ultimately compete for
the same real, limited capital, and should be designed to cooperate
rather than issue conflicting CEO-facing recommendations once both
exist).

## Future Expansion

Multi-goal portfolios, goal templates by company stage, and AI-assisted
goal-setting all require either more real company history than a fresh
game has, or an LLM dependency this codebase does not have (see Chapter
61's own Future Expansion section for the same confirmed absence) — not
invented or stubbed here.

## Company Principle

A goal is only real once it can be measured against something true.
TradeTown does not chase aspirations it cannot check — every objective
this company sets must be backed by a real number, or it isn't set at
all.

## Implementation Notes

**What's real today:** `SettingsState.companyPriority` (a real,
CEO-configurable four-value operating stance biasing real levers —
`app/nexus.py`'s `_effective_risk_limits()`/`PRIORITY_KNOWLEDGE_MULTIPLIER`/
`PRIORITY_RESEARCH_SPEED_MULTIPLIER`); Chapter 59's own real Capital
Priority Engine (ranks trade proposals, not goals);
`app/executive_review.py`'s `_long_term_goals()` (real, regenerated
monthly, but static text with no tracking). None of the three was
extended or reused to build the goal system below — each remains a
real, separate, structurally-different system.

**What was actually built (the smallest real slice — backend +
frontend):** a real `Goal` schema (`app/schemas.py`) and `app/goals.py`
module: `create_goal()` builds a new goal from CEO input;
`validate_target_value()` rejects a non-positive target or one above
its metric's own real ceiling (100 for the two composite scores, 5 for
Academy level, uncapped for portfolio return); `resolve_metric_value()`
reads the one real number each of the four offered metrics maps to;
`tick_goal()`/`tick_goals()` recompute every active goal's real progress
every tick (wired into `app/nexus.py`'s `tick()` alongside
`company_health`/`company_score`/`academy_state`), transitioning a goal
to `completed` (target reached) or `expired` (deadline passed unmet) —
both permanent, one-way, matching `app/hall_of_fame.py`'s "a crossed
milestone stays crossed" convention; `cancel_goal()` lets the CEO
withdraw an active goal. `POST /api/goals/create` and
`POST /api/goals/cancel` (`app/routers/goals.py`), capped at
`MAX_GOALS = 20` like every other real CEO-authored list in this
codebase. Frontend: a real "Company Goals" card in the COMPANY tab —
create form (title, category, metric, target, optional deadline), a
real progress bar per goal, cancel control, honest validation-error
display. Full data-layer plumbing: `types.ts`'s `Goal`/`GoalCategory`/
`GoalMetric`/`GoalStatus`, `api.ts`'s `createGoal`/`cancelGoal`,
`NexusManager.setGoals()`, the `goals:updated` EventBus event, and the
`goals` field threaded through the shared `NexusSnapshot` interface in
both `NexusManager.ts` and `socket.ts` so it survives the initial
`/api/load` and every live WS tick.

**What was actually built (Milestone Tracking — backend + frontend, a
second pass):** the "next honest slice" this chapter's own
Implementation Notes named — extends `Goal` rather than introducing a
second tracking concept. A new `Milestone` schema (id, thresholdPct,
reached, reachedAt) and `Goal.milestones`.
`app/goals.py`'s `_build_milestones()` generates three real, fixed
checkpoints (`MILESTONE_THRESHOLDS = (25.0, 50.0, 75.0)`) for every new
goal — no milestone for 100%, since goal completion already tracks that
real fact via `status`. `_mark_reached_milestones()` marks a milestone
permanently reached the moment real `progress_pct` crosses it, checked
both at creation (a goal can honestly start past a milestone if the CEO
sets a target the company already exceeds part of the way to) and on
every subsequent tick. A milestone, once reached, never reverts — the
same "a crossed milestone stays crossed" convention `app/hall_of_fame.py`
and a `Goal`'s own `completed`/`expired` status already establish.
Frontend: each Goal card in the COMPANY tab renders its three
milestones as filled/hollow markers with a tooltip. Verified: 6 new
backend tests (including one that caught a real bug — the first version
of `_mark_reached_milestones()` passed `"reachedAt"`, the wire alias,
as a `model_copy()` update key instead of `"reached_at"`, the actual
field name; `model_copy()` silently ignored the unknown key, so
`reached` flipped to `True` but `reached_at` stayed `None` forever),
`mypy`/`ruff` clean, full backend suite 1079/1079 passing,
`tsc`/`eslint`/`vite build` clean, and live verification confirming all
three milestone percentages render for a freshly-created goal.

**What was actually built (Executive Priority Engine — backend +
frontend, a third pass):** the next honest slice in sequence. A new
`GoalPriority` schema (goalId, score, remainingPct, daysRemaining).
`app/goals.py`'s `compute_goal_priority()` scores an ACTIVE goal from
two real signals it already carries — see Decision Logic above for the
exact formula — and `rank_goals_by_priority()` sorts every active goal
by that real score, excluding non-active goals the same way Chapter
59's own `rank_trade_proposals()` only ranks its own real pending scope.
New `GET /api/goals/priorities` (read-only, computed fresh per request,
never a second persisted copy — same convention as
`GET /api/decision-vault/quality-score`). Frontend: the Company Goals
card now fetches real priorities (refetched whenever the goals list
changes) and orders active goals by real priority score, showing a
PRIORITY badge and real days-remaining per goal. Verified: 13 new
backend tests, `mypy`/`ruff` clean, full backend suite 1086/1086
passing, `tsc`/`eslint`/`vite build` clean, and a live scripted
Playwright verification (using the project's own real popup-dismissal
helpers) confirming a goal with a tight real deadline correctly ranks
above an open-ended one against the running dev stack.

**What's genuinely still not built:** Resource Allocation recommendations
at the goal level (the one piece that depended on the Priority Engine
existing first, now real); the Strategic Review Cycle (a periodic
report over goal progress, distinct from Chapter 63's own
company-performance Executive Review).

**A real bug found and fixed along the way, not scope (first pass):**
`app/ws_manager.py` builds its per-tick WebSocket broadcast as an
explicit field-by-field dict rather than a full `model_dump()` of
`GameSaveState` — the new `goals` field was added to the schema,
`GET /api/load` (via the generic module-based serialization), and
`tick()`, but was missed in this one explicit-list spot, so the
frontend's `goals` store field silently went from its real initial `[]`
default to `undefined` the moment the first live WS tick landed,
crashing the new Goals card. Found via live Playwright verification of
the running dev stack, not by any automated test (no test exercised a
live WS tick's `goals` field specifically) — fixed in its own commit.

**Before implementation begins for the remaining pieces:** per Appendix
G's Permanent Development Policy, this chapter's design-first step was
satisfied before this implementation pass began. Resource Allocation is
the one remaining honest slice — it would need its own real design for
how a goal-level recommendation interacts with Chapter 56/59/60's
existing, real capital-allocation machinery without duplicating it.
