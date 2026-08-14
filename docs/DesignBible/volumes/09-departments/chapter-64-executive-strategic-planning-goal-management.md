# Chapter 64 — Executive Strategic Planning & Goal Management Engine

**Status:** Fully implemented (backend + frontend) — five real slices,
following this chapter's own recommended sequencing: a CEO-authored
`Goal` naming one real, already-computed metric and a target value,
with real progress recomputed every tick; Milestone Tracking, three
real 25/50/75% checkpoints on that same progress; the Executive
Priority Engine, ranking active goals by a real urgency formula;
Resource Allocation, a recommend-only share of executive attention
normalized from that same Priority Engine; and the Strategic Review
Cycle, a real monthly report over what genuinely changed for CEO-
authored goals. See [Volume 9's chapter template](README.md) for what
every section below must contain, and the Implementation Notes at the
bottom for exactly what was built and how.

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

`app/goals.py` (`Goal`, `Milestone`, `GoalPriority`, `GoalAllocation`,
`StrategicReview` schemas; `create_goal()`, `tick_goal()`/`tick_goals()`,
`cancel_goal()`, `compute_goal_priority()`, `rank_goals_by_priority()`,
`compute_resource_allocation()`, `generate_strategic_review()`,
`record_strategic_review()`), `app/routers/goals.py`
(`POST /api/goals/create`, `POST /api/goals/cancel`,
`GET /api/goals/priorities`, `GET /api/goals/allocations`), the monthly
Strategic Review generation wired into `app/nexus.py`'s `tick()`
alongside Chapter 63's Executive Review, and the COMPANY tab's Company
Goals and Strategic Review Cycle cards (`CompanyPanel.tsx`) are now real
and authoritative over everything this chapter owns. Three real,
adjacent systems were checked first and remain explicitly separate, not
reused:

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
priority scores (`GoalPriority`, via `GET /api/goals/priorities`); a
real Resource Allocation recommendation (`GoalAllocation`, via
`GET /api/goals/allocations`) — a normalized share of executive
ATTENTION across active goals, never a claim about moving real capital
(see Decision Logic); and a real monthly Strategic Review
(`StrategicReview`, broadcast alongside every other real save-state
field) — active goal count, which goals completed/expired and which
milestones were newly reached since the previous review, the current
top-priority goal, and a real summary sentence — see `app/goals.py`.

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
already establishes → on the same monthly boundary as Chapter 63's
Executive Review, `generate_strategic_review()` runs, comparing every
goal's real `updated_at`/`completed_at` and every milestone's real
`reached_at` against the previous review's own real `created_at` to
find what genuinely changed this period, then `record_strategic_review()`
appends it to the capped review history — the same "compute once,
append, cap" pattern the Executive Review itself already uses.

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

**Also built.** `app/goals.py`'s `compute_resource_allocation()` is the
real Resource Allocation recommendation this chapter's Mission always
named — but honestly scoped to what a `Goal` actually is: a company-wide
metric, not a set of open positions with a real capital pool behind it.
So the "resource" being allocated is executive ATTENTION, not capital —
each active goal's real `GoalPriority.score` (above) normalized against
the sum of every active goal's score, so the recommendation always sums
to ~100% across whatever active goals exist. Reuses the Priority
Engine's own score directly rather than inventing a second composite,
the same "don't duplicate a real number" discipline this chapter's own
Ownership table already applies to Chapter 59. Recommend-only,
computed fresh per request, never persisted — the same boundary and
convention every other scoring engine in this chapter and Chapter 59/60
already respect (see Safety Systems).

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
| Resource Allocation targets | **Built** — `GET /api/goals/allocations` returns every active goal's real `GoalAllocation` (score, allocation %), normalized from the same Priority Engine scores so they sum to ~100% (`app/goals.py`'s `compute_resource_allocation()`). Recommend-only, an ATTENTION share not a capital one (see Decision Logic). The COMPANY tab's Company Goals card renders a "Recommended attention" bar with a real % under each active goal's progress meter. |
| Milestone definitions | **Built** — every goal automatically gets three real checkpoints at 25%/50%/75% of its own real progress (`app/goals.py`'s `MILESTONE_THRESHOLDS`), each permanently marked reached the moment real progress crosses it (checked both at creation, so a goal can honestly start past a milestone, and on every tick). Rendered as filled/hollow markers on each Goal card. No CEO configuration of the thresholds themselves yet — a real future "promote a constant" candidate, same pattern as Chapter 63's tier thresholds. |
| Strategic Review cadence | **Built** — a real monthly `StrategicReview` generates on the same evening/monthly boundary as Chapter 63's Executive Review (`app/goals.py`'s `generate_strategic_review()`, wired into `app/nexus.py`'s `tick()`), reviewing CEO-authored *goal* progress — distinct from Chapter 63's own Executive Review, which reviews company *performance*. The COMPANY tab's own "Strategic Review Cycle" card lists every real review newest-first with its own real summary. |
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

**Built.** The Strategic Review Report — a real `StrategicReview`
generated monthly, mirroring Chapter 63's `ExecutiveReview` structure
but over CEO-authored goals: active goal count, which goals genuinely
completed or expired since the previous review, how many milestones
were newly reached, the current top-priority goal, and a real summary
sentence built entirely from those fields. Capped at
`MAX_STRATEGIC_REVIEWS = 20` like every other periodic-report list in
this codebase.

## Safety Systems

**Built and respected.** `compute_resource_allocation()` never writes to
or reads from `PaperPortfolio`, never touches `PaperBroker`, and is
called only from a `GET` endpoint — the same recommend-only boundary
Chapter 60's Capital Rotation and Chapter 59's Priority Score both
already respect, made real rather than just stated. No goal is ever
marked complete by anything other than a real, checkable metric crossing
its real target (`tick_goal()`'s own `current_value >= target_value`
check).

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

Chapter 63 (supplies the real metrics every goal is measured against —
Company Health, Company Score — and shares this chapter's own monthly
review cadence). Chapter 60 (Portfolio Rebalancing — itself still
target design; its own future Capital Rotation recommendation would
compete for real, limited capital in a way this chapter's Resource
Allocation deliberately does not, since this chapter's recommendation
is an ATTENTION share, never a capital one — see Decision Logic/Safety
Systems — so the two can coexist without issuing conflicting CEO-facing
capital recommendations).

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

**What was actually built (Resource Allocation — backend + frontend, a
fourth pass):** the last piece this chapter's own Implementation Notes
had named as depending on the Priority Engine — now that it exists, the
real design question was what a "resource" even is for a `Goal`. A goal
tracks a company-wide metric (Company Health, Company Score, portfolio
return, Academy level), not a set of open positions with a real capital
pool behind it, so there was never a real per-goal capital pool to
allocate — inventing one would have meant fabricating a number Chapter
56/59/60's real capital machinery doesn't actually track per goal. The
honest slice instead: a normalized share of executive ATTENTION. A new
`GoalAllocation` schema (goalId, score, allocationPct).
`app/goals.py`'s `compute_resource_allocation()` reuses
`rank_goals_by_priority()`'s own real scores directly — no second
composite — and normalizes each active goal's score against the sum of
all of them, so the recommendation always sums to ~100%. The one real
edge case (every active goal's urgency score is exactly 0 — possible
only in the narrow window where a goal's `current_value` already meets
its target but the next tick hasn't yet flipped it to `completed`) falls
back to an even split rather than dividing by zero. New
`GET /api/goals/allocations` (read-only, computed fresh per request,
same convention as the Priority Engine). Frontend: each active goal's
card in the COMPANY tab now renders a "Recommended attention" bar with
a real % underneath its progress meter, refetched on the same real
triggers as priorities. Verified: 5 new backend tests, `mypy`/`ruff`
clean, full backend suite 1091/1091 passing, `tsc`/`eslint`/`vite build`
clean, and live Playwright verification against the running dev stack
confirming two active goals both showing a correctly normalized 50%
allocation bar.

**What was actually built (Strategic Review Cycle — backend + frontend,
a fifth and final pass):** the last piece this chapter's own
Implementation Notes had flagged as target design, closing out this
chapter's real, honest scope entirely. Mirrors Chapter 63's monthly
`ExecutiveReview` structure but asks a different question: not "how is
the company performing" but "how is CEO-authored goal progress moving."
A new `StrategicReview` schema (id, createdAt, activeGoalCount,
completedSinceLastReview, expiredSinceLastReview,
milestonesReachedSinceLastReview, topPriorityGoalId, topPriorityScore,
summary). `app/goals.py`'s `generate_strategic_review()` finds what
genuinely changed since the previous review by comparing each goal's
real `updatedAt`/`completedAt` and each milestone's real `reachedAt`
against the previous review's own real `createdAt` — a real, monotonic
ISO-timestamp comparison, never a fabricated delta — and reuses the
Executive Priority Engine's own top-ranked goal directly rather than a
second ranking. Generated on the exact same monthly boundary as the
Executive Review in `app/nexus.py`'s `tick()`
(`record_strategic_review()`, capped at `MAX_STRATEGIC_REVIEWS = 20`).
Frontend: a new "Strategic Review Cycle" card on the COMPANY tab lists
every real review newest-first with its own real summary sentence, an
honest empty state before the first monthly review generates. Verified:
8 new backend tests, `mypy`/`ruff` clean, full backend suite 1099/1099
passing, `tsc`/`eslint`/`vite build` clean, and live verification
against the running dev stack — advancing time to a real month boundary
via `POST /api/time/advance` produced a real review (2 goals expired,
4 milestones newly reached) that rendered correctly in the Command
Center.

**Nothing from this chapter's original scope remains target design.**
Every piece named in the Executive Summary, Mission, and CEO Controls —
Goal authoring, Milestone Tracking, the Executive Priority Engine,
Resource Allocation, and the Strategic Review Cycle — is real, tested,
and shipped backend + frontend.

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

Per Appendix G's Permanent Development Policy, this chapter's
design-first step was satisfied before each of its five implementation
passes began, and each pass's own real design decision is recorded
above rather than assumed. With the Strategic Review Cycle now real,
this chapter has no further pass to design against — any genuinely new
capability (e.g. CEO-configurable milestone thresholds, promoted from a
constant the same way Chapter 63's tier thresholds were) would be a new
chapter revision, not a continuation of this one's original scope.

**CEO Company Health + Live Market Realism directive, Section 13 —
Blocker Detection (sixth pass).** The CEO's directive asked Goals to
also carry owner/supporting-departments/evidence/blockers/outcome.
`progress_pct` and `status`/`completed_at` were already the real,
honest "progress" and "outcome" this chapter names. `owner` and
`supporting departments` were investigated and explicitly cut, not
silently dropped: a `Goal` tracks one company-wide metric (Company
Health, Company Score, portfolio return, Academy level) that every
department's real work already feeds into simultaneously — there is no
real per-goal assignment mechanism anywhere in this codebase to
attribute ownership to a single agent or a specific department subset
without inventing one, and this chapter's own Decision Logic section
has always drawn a hard line against inventing mechanics a system
doesn't actually have. `evidence` is likewise not a second, manufactured
narrative field — the real numbers (`current_value`/`target_value`/
`progress_pct`/`stalled_ticks`) already are the evidence.

`blockers` is the one genuinely new real signal: `stalled_ticks`/
`is_blocked` on `Goal`, computed in `tick_goal()`. A goal accumulates
one stalled tick for every real tick it stays active with essentially
zero real `progress_pct` movement (`_STALL_EPSILON_PCT`, the same
rounding-noise reasoning `_progress_pct()`'s own `round(..., 1)`
already applies), and resets to zero the instant real progress resumes.
`is_blocked` flips true once `stalled_ticks` crosses
`GOAL_STALLED_THRESHOLD_TICKS` (20 — the same order of magnitude as
`TEAM_CHEMISTRY_WINDOW`/`EXECUTIVE_METRIC_WINDOW`'s own "recent
behavior" sizing in `app/company_health.py`), and is forced back to
`false` the moment a goal completes or expires — a resolved goal is
never shown as blocked. Frontend: the Company tab's goal cards show a
red "BLOCKED" pill plus the real stalled-tick count
(`frontend/src/ui/components/CommandCenter/panels/CompanyPanel.tsx`).

Verified: 6 new backend tests (fresh goal starts unblocked, counter
increments under real stagnation, threshold crossing, reset on real
progress, completed/expired goals never read as blocked), full backend
suite (1775 tests), `mypy`/`ruff` clean, frontend `tsc`/`lint`/`build`
clean. Live-verified against the running dev server: created a real
goal via `POST /api/goals/create` (targeting Academy Level, a metric
that genuinely doesn't move tick-to-tick without real Academy
progress), let the live sim tick it forward in real wall-clock time
(~2s/tick), and confirmed `isBlocked` flipped `true` at exactly
`stalledTicks == 20` via direct `GET /api/load` polling before
confirming the same real transition rendered live in the Command Center
UI as the red "BLOCKED" pill and "No real progress in 33 consecutive
ticks." — not a fixture.
