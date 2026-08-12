# Chapter 74.5 — CEO Vision Board & Strategic Alignment Engine

**Status:** Target design, not yet implemented. **Chapter number
note:** inserted between Chapters 74 and 75, the same decimal-insertion
precedent Chapter 73.5 already established, per explicit instruction to
keep this chapter separate from — but immediately following — Chapter
74's Continuous Learning & Self-Improvement System. **Researched first,
and the finding is stark:** most of what this brief asks for already
exists as a real, separate, already-documented system under a
different name. "Company Philosophy" is a near-verbatim match for
`app/constitution.py`'s 13 real, CEO-amendable Articles (Founder
debate, employee votes, citation enforcement, ratification — all
real). "Company Identity" collides directly with `app/company_dna.py`'s
real `classify_identity()` — a different concept (derived from
historical behavior, not CEO-declared) under the same name. "Long-Term
Roadmap" is explicitly claimed by the still-unwritten Volume 14 and
`docs/ROADMAP.md`. "CEO Long-Term Objectives" runs headlong into
`app/goals.py`'s real `Goal` schema, which deliberately supports only 4
real, computable metrics — most of the brief's named objective types
(risk tolerance, preferred trading style, lifestyle goals, tech
roadmap wishes) have no real signal anywhere in this codebase to
compute progress against. This chapter's real job is narrower than its
brief: reuse every one of those real systems by reference, refuse to
build a second, competing copy of any of them, and add exactly two
genuinely new things — a small, honest CEO Priorities/Objectives
surface for what `goals.py` structurally cannot represent, and a real,
disclosed Vision Alignment Engine.

## Executive Summary

The brief's own thesis — "every recommendation should be evaluated
against the CEO's long-term vision" — does not require inventing a
second Constitution, a second Goal system, or a second monthly report.
It requires exactly one new thing this codebase has never had: a real,
mechanical way to read the CEO's own explicit priorities and apply them
as a score to a handful of already-real CEO-facing decision points.
That is what ships here — `VisionBoardState` (a CEO-authored priority
ranking plus a small set of honestly-labeled qualitative objectives)
and a Vision Alignment Engine that scores exactly three real subject
types, per explicit scope: Chapter 74's `SelfImprovementProposal`,
`app/goals.py`'s `Goal`, and `app/constitution.py`'s
`ConstitutionAmendment`. Every other section of the brief either
already exists elsewhere (cited, not rebuilt) or has no real signal to
build honestly (named as a Deferred Feature, not faked).

## Mission

Give the CEO one place to state what matters most, in their own words
and their own explicit ranking — and give every other CEO-facing
decision point in this codebase a real, mechanical way to check itself
against that ranking, without ever fabricating what "alignment" means.

## Philosophy

A Vision Board that duplicates the Constitution is not a vision board —
it is a second Constitution with a different name, and this codebase
already rejected that shape once (Chapter 62's own naming-collision
lesson: `app/innovation.py` looked like it should be the "Innovation
Lab" and wasn't). The discipline here is the same one Chapter 74 held
itself to: cite the real system, extend only where a real gap exists,
and when the brief asks for something with no real signal behind it —
a fabricated "alignment score" against vague text, an invented
progress percentage on "lifestyle goals" — name that gap and stop,
rather than build something that looks more complete than it is.

## Responsibilities

**Owns:** `VisionBoardState` (CEO-authored priority ranking over a
real, fixed category set; a small list of honestly-labeled qualitative
objectives with no fabricated progress; an optional CEO identity
annotation), and the Vision Alignment Engine (`compute_vision_
alignment_score()`), scoped to exactly three real subject types.

**Does NOT own, and explicitly refuses to duplicate:** Company
Philosophy / permanent company principles (`app/constitution.py`'s real
Articles — CEO-amendable, Founder-debated, citation-enforced; this
chapter surfaces them, never re-declares them), Company Identity
(`app/company_dna.py::classify_identity()` — a real, derived,
historical read; this chapter adds an optional annotation alongside
it, never a competing re-classification), CEO-authored computable
goals (`app/goals.py`'s real `Goal`/`GoalMetric`/Milestone/Priority
Engine/Resource Allocation/Strategic Review Cycle — extended by
reference for the Vision Alignment Engine, never re-implemented), the
Long-Term Roadmap (claimed by the still-unwritten Volume 14 and
`docs/ROADMAP.md` — this chapter's in-game "roadmap" is just the real,
existing `GET /api/goals` list, nothing new), and monthly CEO
reporting (`app/goals.py`'s real `StrategicReview` and Chapter 74
Part 2's `InstitutionalEvolutionReport` already cover this cadence — no
third monthly report is built here).

## Ownership

| Brief concept | Real system today | This chapter's real move |
|---|---|---|
| "Company Philosophy" (CEO-defined permanent principles) | `app/constitution.py`'s `ConstitutionState` — 13 real Articles, Founder debate, employee votes, CEO ratification, citation enforcement (`MISTAKE_ARTICLE_MAP`), plus `docs/DESIGN_BIBLE.md`'s existing static Philosophy section | **Cited, not rebuilt.** The Vision Board's own frontend would read `GET /api/constitution` directly — no new backend surface, no second permanent-principles list |
| "Company Identity" (who TradeTown is) | `app/company_dna.py::classify_identity()` — real, but *derived* from historical behavioral traits, not CEO-declared | **Naming collision, not duplicated.** `VisionBoardState.identity_note` is an optional CEO-authored annotation displayed *alongside* the real derived classification, never a competing re-classification of it |
| "CEO Long-Term Objectives" (financial/risk/lifestyle/roadmap goals) | `app/goals.py`'s real `Goal` — structurally limited to 4 real `GoalMetric` values (`company_health_combined`, `company_score_overall`, `portfolio_return_pct`, `academy_level`) | **Split honestly.** Anything with a real signal: the CEO creates a normal `Goal` (no new mechanism). Anything without one (risk tolerance, preferred trading style, tech roadmap wishes, lifestyle goals): a `VisionBoardObjective` — CEO text only, explicitly no fabricated progress percentage |
| "Long-Term Roadmap" | Claimed by unwritten Volume 14 + `docs/ROADMAP.md`; in-game, the closest real analog is `GET /api/goals`' active/completed list | **Not duplicated.** No new "roadmap" state — the CEO's own real Goals already are this, in-game |
| "Vision Alignment Engine" (score every recommendation) | *(genuinely does not exist)* | **Real, new, and deliberately narrow** — scores exactly three real subject types: `SelfImprovementProposal` (Chapter 74), `Goal`, `ConstitutionAmendment`. Does not score every trade recommendation — see Decision Logic |
| "Monthly CEO Review / Vision Alignment Report" | `app/goals.py::generate_strategic_review()` (real, monthly) and Chapter 74 Part 2's `InstitutionalEvolutionReport` (real, monthly) already cover this cadence | **Not built as a third report.** Building one would repeat the exact duplication Chapter 74 Part 2's own cadence/focus table was written to prevent |
| "Self-Correction" (detect drift, notify CEO) | *(genuinely does not exist)* | **One real, narrow check**, not the brief's open-ended list — see Self-Correction below |

## Vision Board

`VisionBoardState` — one real, permanent, CEO-mutated object (like
`RiskLimits`/`TradingModeState`, not a growing log):

- **`mission`** — free CEO-authored text, optional, no computed
  progress against it (there is no real signal to compute one from).
- **`priorities`** — a CEO-ranked ordering over a fixed, disclosed
  6-value category set, `VisionPriorityCategory`: the 5 real
  `GoalCategory` values (`growth`, `risk`, `research`, `trading`,
  `operations`) plus one new value, `governance` — added specifically
  so `ConstitutionAmendment`s (which have no `GoalCategory` of their
  own) have a real category to rank against, not because governance is
  a `Goal` concept.
- **`objectives`** — a list of `VisionBoardObjective`: CEO-authored
  text, a category tag from a small fixed set (`trading_style`,
  `expansion`, `research_priority`, `technology`, `lifestyle`,
  `other`), and nothing else. No progress bar, no percentage, no
  target value — the same honesty boundary `app/goals.py`'s own
  4-metric limit already drew for itself, applied here to the
  objectives that fall outside even that limit.
- **`identity_note`** — optional CEO text, displayed next to
  `company_dna.py`'s real derived identity classification, never
  replacing it.

## Vision Alignment Engine

`compute_vision_alignment_score()` — a real, disclosed, purely
mechanical formula, never a fabricated "does this feel aligned" read.
Every subject type maps to a `VisionPriorityCategory`:

- `Goal.category` maps directly (it already is one of the 5 shared
  values).
- `SelfImprovementProposal.category` maps through a fixed, disclosed
  table (`SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY` — e.g. `risk_rule` →
  `risk`, `research_workflow` → `research`, `automation` →
  `operations`), the same "no hidden weighting" convention
  `app/company_score.py` established.
- `ConstitutionAmendment` always maps to `governance` — a true
  statement (every amendment is inherently a governance action), not a
  guess.

The score itself: if the mapped category appears at rank *R* among *N*
CEO-ranked priorities, `score = 100 × (N − R + 1) / N`. If the CEO has
not ranked that category at all, `score = 50.0` — an explicit,
disclosed neutral default, never an invented "we think you'd care
about this." `supporting_reasons` names the real rank (e.g. `"risk" is
ranked #1 of 3 CEO priorities`); `conflicting_goals` flags only when
the mapped category is the CEO's own lowest-ranked priority.
`confidence` is `100.0` when a real rank was found, `40.0` for the
neutral-default case — an honest signal that the second number is a
placeholder reading, not a real assessment. Computed on-demand, never
persisted, for `Goal` and `ConstitutionAmendment` (no reserved field
exists for either — adding one would touch `app/state.py`'s goal/
amendment creation flows beyond this chapter's real scope). For
`SelfImprovementProposal`, the score *is* persisted: Chapter 74 already
reserved `vision_alignment_score` on that schema for exactly this
chapter to fill in, so it is computed once, at generation time, in
`app/nexus.py`/`app/state.py`'s existing two proposal-generation call
sites.

## Self-Correction

One real, narrow check, not the brief's open-ended list of drift
scenarios: if the CEO's own rank-1 priority is `risk` and the real
Daily Circuit Breaker tier (`app/trading_modes.py`'s
`DailyCircuitBreakerRead.tier`) is `tier2` or worse, surface a real
drift note — the CEO's own stated top priority and the company's own
real current risk state have diverged. No other drift scenario from
the brief (research priorities shifting, automation conflicting with
philosophy, risk profile exceeding tolerance in the general case) has
an equally clean, single real signal to check against without
fabricating one — see Deferred Features.

## Inputs

Real: `ConstitutionState.articles` (`app/constitution.py`, read
directly, not duplicated), `CompanyDNA` (`app/company_dna.py`, read
directly), `Goal`/`GoalCategory` (`app/goals.py`), `SelfImprovementProposal`
(Chapter 74), `ConstitutionAmendment` (`app/constitution.py`),
`DailyCircuitBreakerRead.tier` (`app/trading_modes.py`).

## Outputs

Real: `VisionBoardState` (persisted, CEO-mutated), `VisionAlignmentScore`
(computed on-demand for `Goal`/`ConstitutionAmendment`; persisted on
`SelfImprovementProposal` at generation time), a self-correction drift
note (computed on-demand, not persisted — same convention Chapter 72's
Early Warning Score uses for a live read with no history to keep).

## Internal Workflow

`VisionBoardState` is CEO-mutated only, the same shape as `RiskLimits`.
`SelfImprovementProposal`'s alignment score is computed once, right
after generation, in `app/nexus.py`'s recurring-mistake check and
`app/state.py`'s retirement-cluster check — the exact two places
Chapter 74 already generates a proposal. `Goal`/`ConstitutionAmendment`
alignment and the self-correction check are computed fresh per request,
no new tick-loop cost.

## Decision Logic

The rank-based formula above is the entire decision logic — no
adaptive weighting, no machine-learned "fit," a fixed, published
category-mapping table for each of the three subject types.
**Deliberately not scored:** individual trade recommendations. Scoring
every trade proposal against the Vision Board would mean adding a 10th
unconditional check to `app/gatekeeper.py`'s real 9-check pipeline —
explicitly out of scope per your own instruction, and the same kind of
scope expansion Chapter 70 Part 3's Weighted Executive Decision Engine
was deliberately kept advisory-only to avoid.

## Department Cooperation

**Reads from:** `app/constitution.py`, `app/company_dna.py`,
`app/goals.py`, Chapter 74's `app/self_improvement.py`,
`app/trading_modes.py`. **Provides to:** the CEO (priority ranking,
objectives, alignment scores, drift notes). **Does not feed** the
Trade Gatekeeper — see Decision Logic.

## CEO Controls

| Control | Status |
|---|---|
| Set/edit mission text | Real |
| Rank priority categories | Real |
| Add/remove a qualitative objective | Real |
| Set an identity annotation | Real |
| View alignment score for a Goal/Amendment/Proposal | Real, read-only |
| View self-correction drift note | Real, read-only |

## KPIs

Not applicable in the usual sense — this chapter produces no new
measured performance metric of its own; `VisionAlignmentScore` is a
per-item read, not a trend to track over time (Chapter 74 Part 2's
Company Evolution Score already owns "is the company improving,"
deliberately not duplicated here).

## Reports

None built — see Ownership for why a third monthly report was
explicitly not added.

## Safety Systems

Read-only and advisory in every direction: the Vision Alignment Engine
can never block or force a decision, matches the same non-authoritative
posture Chapter 70 Part 3's Weighted Executive Decision Engine already
established for the Gatekeeper. `VisionBoardState` mutations are
CEO-only, never automation-eligible.

## Dependencies

`app/constitution.py`, `app/company_dna.py`, `app/goals.py`, Chapter
74's `app/self_improvement.py`, `app/trading_modes.py`.

## Connected Features

Chapter 74 (Self-Improvement Proposals — the one persisted alignment
score), `app/goals.py`'s Chapter 64 (Goal alignment scoring, on-demand),
`app/constitution.py` (Amendment alignment scoring, on-demand; also the
real Company Philosophy this chapter surfaces rather than duplicates),
`app/company_dna.py` (the real Company Identity this chapter annotates
rather than duplicates), `app/trading_modes.py` (the one real signal
Self-Correction checks against).

## Deferred Features

**Scoring individual trade recommendations.** *Current state:* not
built — see Decision Logic. *Missing infrastructure:* none, technically
buildable, but would require a 10th `app/gatekeeper.py` check.
*Dependencies:* `app/gatekeeper.py`'s real 9-check pipeline.
*Recommended future chapter:* an addendum to this chapter, only if
explicitly requested — this was an explicit scope decision, not a
technical gap. *Estimated complexity:* medium. *Risk of building
prematurely:* would add a 10th unconditional Gatekeeper check without
the same deliberation Chapter 70 Part 3's WEDE integration received —
exactly the kind of unreviewed scope expansion the standing workflow
exists to prevent.

**General-purpose drift detection** (research priorities shifting,
automation conflicting with philosophy, risk profile exceeding
tolerance in the open-ended sense the brief describes). *Current
state:* only the one narrow risk-priority-vs-circuit-breaker check is
built. *Missing infrastructure:* each other named drift scenario would
need its own real, checkable signal — "research priorities have
shifted" has no real signal anywhere (no historical priority-tracking
exists to diff against), "automation conflicts with philosophy" would
require a formal mapping from `OperatingMode` behavior to Constitution
Articles that does not exist. *Dependencies:* vary per scenario.
*Recommended future chapter:* an addendum to this chapter, once a real
signal exists for any one of them. *Estimated complexity:* small per
scenario, once a real trigger is identified. *Risk of building
prematurely:* a fabricated drift signal would be the single most
CEO-visible way this chapter could violate the no-fabrication rule —
a false "your company has drifted from its values" reading is worse
than no reading at all.

**Vision Alignment scores persisted on `Goal`/`ConstitutionAmendment`.**
*Current state:* computed on-demand only. *Missing infrastructure:*
neither schema has a reserved field the way Chapter 74 reserved one on
`SelfImprovementProposal`. *Dependencies:* would touch `app/state.py`'s
`create_goal()`/`propose_constitution_amendment()` methods. *Recommended
future chapter:* an addendum to this chapter or to Chapter 64/the
Constitution's own future work. *Estimated complexity:* small.
*Risk of building prematurely:* none significant — this is a pure
scope-discipline decision (touch fewer files this pass), not a
honesty concern; deferred to keep this pass's blast radius contained
to what was explicitly asked for.

## Company Principle

"A vision the CEO cannot rank against a real decision is a slogan, not
a strategy." Every score this chapter produces must trace to the CEO's
own real, explicit ranking — never an inferred guess at what they
"probably" care about, and never a second copy of a principle they
already declared somewhere else in this codebase.

## Implementation Notes

**What's real today, before this chapter, and reused rather than
duplicated:** `app/constitution.py` (Company Philosophy), `app/
company_dna.py` (Company Identity, derived), `app/goals.py` (CEO
Objectives with a real signal, the Long-Term Roadmap, monthly CEO
reporting via `StrategicReview`), Chapter 74's `InstitutionalEvolutionReport`
(the other real monthly report this chapter does not duplicate).
**What this chapter adds, real:** `app/vision_board.py` (new) —
`VisionBoardState` CRUD, `compute_vision_alignment_score()` (a
disclosed, rank-based formula over three real subject types), one
narrow self-correction check. **What's genuinely, entirely unbuilt,
named and not faked:** trade-level alignment scoring, general-purpose
drift detection beyond the one risk/circuit-breaker check, and
persisted alignment scores on `Goal`/`ConstitutionAmendment` — see
Deferred Features.
