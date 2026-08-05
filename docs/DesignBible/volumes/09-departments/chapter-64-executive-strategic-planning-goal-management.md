# Chapter 64 — Executive Strategic Planning & Goal Management Engine

**Status:** Target design. Not yet implemented as a dedicated system —
three real, partial building blocks already exist and are named exactly
where they overlap below, but no code in this repository tracks a goal,
a milestone, a deadline, or a resource allocation against one. See
[Volume 9's chapter template](README.md) for what every section below
must contain, and the Implementation Notes at the bottom for exactly
what's real today versus new here.

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

Nothing in this codebase today implements a goal object, a milestone, or
a deadline. Three real, adjacent systems exist and would need to be
either reused as inputs or explicitly left alone:

| Brief concept | Closest real system | Why it is NOT the same thing |
|---|---|---|
| Executive Priority Engine (ranks *goals*) | `app/capital_priority.py`'s `rank_trade_proposals()` (Chapter 59) | Ranks *pending trade proposals* by a real Decision Score, recomputed every tick. There is no real concept of a company *goal* anywhere in this codebase for an equivalent engine to rank — this would be a genuinely new, separately-scoped ranking over a genuinely new object type, not an extension of Chapter 59's. |
| Company Priority (a "strategic stance") | `SettingsState.company_priority` (`CompanyPriority`: `"balanced"`/`"learning"`/`"research"`/`"risk_reduction"`) | A real, CEO-set, persistent toggle that biases exactly one real lever per value (see `app/nexus.py`'s `_effective_risk_limits()`, `PRIORITY_KNOWLEDGE_MULTIPLIER`, `PRIORITY_RESEARCH_SPEED_MULTIPLIER`). This is the closest real thing to a "strategic priority" in the whole codebase — but it is one global stance with four fixed values, not a set of CEO-authored goals with their own text, deadlines, or progress. |
| SMART Objectives / goal text | `app/executive_review.py`'s `_long_term_goals()` | Generates one or two real sentences ("Hold max drawdown under X%, the standing risk limit," "Advance the Academy past tier Y") from real current state, every month, as part of the Executive Review. These are real and non-fabricated, but they are regenerated fresh each time from a fixed, hardcoded rule set — nothing is ever CEO-authored, stored, tracked over time, or marked complete. |

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

None today. A real future implementation would produce: a `Goal`/`SmartObjective`
schema (title, category, target metric, deadline, progress), a ranked
list of active goals (the real Executive Priority Engine), a Resource
Allocation recommendation, and Milestone events.

## Internal Workflow

Not real yet — there is no workflow to document against actual code, per
this volume's own template rule ("documented against the real code path,
not an idealized one"). A future implementation's honest workflow would
need, at minimum: CEO defines a goal with a real target metric → the
engine picks which already-real number in this codebase maps to that
metric (Company Health sub-score, Company Score metric, portfolio
return, Academy level, etc. — not every conceivable goal has a real
metric to attach to) → progress is read fresh each tick/review cycle from
that real number → the Strategic Review Cycle reports honest progress or
an honest "off track."

## Decision Logic

Not real yet. The one real decision-logic precedent this chapter could
reuse is Chapter 59's own "reuse a real composite, never invent a
second one" discipline — an Executive Priority Engine over goals would
need its own real, named formula (e.g., urgency-by-deadline combined with
real distance-to-target), not a copy of Chapter 59's trade-proposal
Decision Score, since goals and trade proposals are structurally
different objects.

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
| Goal Categories / SMART Objective authoring | **Not built** — no schema, no input surface. |
| Executive Priority Engine (goal ranking) | **Not built** — see Ownership for why Chapter 59's engine is not a substitute. |
| Resource Allocation targets | **Not built** — no goal-level capital-allocation concept exists. |
| Milestone definitions | **Not built** — no milestone object exists anywhere. |
| Strategic Review cadence | **Not built** — no review cycle exists for this chapter's own concept (distinct from Chapter 63's real monthly Executive Review, which reviews company *performance*, not CEO-authored *goals*). |
| Company Priority (existing four-value stance) | **Already real** — `SettingsState.companyPriority`, CEO-configurable today via the existing RISK/Company panel, unrelated to this chapter's own not-yet-built goal system except as a possible future input. |

## Learning System

Not real yet. A genuine future version would ask, per goal, "did the
company's real progress metric move the way the goal predicted, and by
how much" — the same "wait for real time to pass, then check real data"
convention every other Learning System section in this volume already
uses, applied to whichever real metric that goal was actually attached
to.

## KPIs

Not honestly computable today — there is nothing to measure. Once real,
the honest candidates are: Goal Completion Rate (a real check against
each goal's own real target metric), Milestone Hit Rate (real,
timestamped, checkable), Resource Allocation Efficiency (would require
the same kind of real before/after portfolio comparison Chapter 60's own
KPIs section already flags as needing a new ledger).

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
monthly, but static text with no tracking). None of the three is a
substitute for this chapter's actual scope, and none was extended or
modified in writing this chapter — this is a documentation-only pass, no
code changes.

**What's genuinely new and not yet built, and it is substantial:** the
entire goal/objective data model (nothing like it exists — no `Goal`
schema, no storage, no CEO input surface); the Executive Priority Engine
for ranking goals (structurally distinct from Chapter 59's, per
Ownership — cannot be built by extending that module); Resource
Allocation recommendations at the goal level; Milestone Tracking; the
Strategic Review Cycle. This is comparable in size to Chapter 60's own
flagged "largest real gap" — honest scoping here matters as much as it
did there.

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step, satisfied by
this pass. Given the size of the real gap, a future implementation
should likely start with the smallest real, independently-useful slice —
a `Goal` schema plus manual CEO authoring and one real progress metric
per goal (reusing Company Health/Company Score directly, no new ranking
engine yet) — before attempting the Executive Priority Engine or
Resource Allocation, the same "smallest real slice first" sequencing
Chapter 60's own Implementation Notes already recommend for a
comparably-sized gap.
