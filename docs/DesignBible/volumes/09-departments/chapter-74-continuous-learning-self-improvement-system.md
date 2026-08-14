# Chapter 74 — Continuous Learning & Self-Improvement System (CLSIS)

**Status:** Substantially implemented, backend and frontend — see
Implementation Notes below for the complete, itemized honesty boundary;
this line was previously stale (it said "not yet implemented" even
after `app/self_improvement.py` shipped), fixed as part of the same
audit pass noted below. A Chapters 67–75 audit later found this chapter
(and Part 2, and Chapter 74.5's Vision Board) had zero frontend
presence despite a real, working backend — fixed by a real
`EvolutionPanel.tsx` Command Center tab (`EVOLUTION`, under AI
Workforce) bundling all three: Self-Improvement Proposals (approve/
reject/mark-implemented), the Executive Learning Summary, the Company
Evolution Score, Institutional Evolution Reports, and the CEO Vision
Board (mission/priorities/objectives/identity note/self-correction
note). Covered by `frontend/tests/evolutionPanel.spec.ts`. **Chapter
number note:**
the source brief for this chapter called itself "Chapter 75," but that
number already belongs to the real, implemented [Company Trading Modes
& Institutional Capital
Protection](chapter-75-company-trading-modes-institutional-capital-protection.md)
chapter. Chapter 74 was vacated by an earlier renumber (Trading Modes
moved 74→75) and has stood empty since — this chapter now claims it, by
explicit instruction, without renumbering anything else. **Researched
first, and the finding changes this chapter's whole shape:** the brief
describes a Post-Trade Review Engine, a Lesson Library, Strategy
Evolution tracking, Executive Learning, Academy Integration, Knowledge
Graph Expansion, an AI Improvement Lab, Self-Improvement Proposals, and
a Company Evolution Score as if none of it exists yet. Roughly 60-70%
of it already does, spread across `app/mistakes.py`, `app/successes.py`,
`app/wisdom.py`, `app/knowledge.py`, `app/knowledge_graph.py` (Chapter
61 — "Substantially implemented"), `app/strategy_lab.py`/`app/sandbox.py`
(Chapter 62 — "Partially implemented"), `app/coach.py`, `app/mentor.py`,
`app/foundational_mentors.py`, and `app/company_score.py`/`app/
company_health.py` (Chapter 63 — "Substantially implemented"). This
chapter's real job is narrower than its brief: name every place it
would duplicate an already-real, already-documented system, refuse to
rebuild any of them under a new name, and build only the pieces that
are genuinely missing. See Implementation Notes for the complete,
itemized honesty boundary and Part 2 for the Institutional Evolution
Engine.

## Executive Summary

"Every experience becomes institutional knowledge" is already mostly
true in this codebase — it is just spread across nine different modules
that were each built to answer a narrower question (was this trade a
mistake? does this agent deserve more Academy points? should this
strategy retire?) rather than one unified "learning system." Part 1
does not rebuild any of those nine modules. It adds exactly two
genuinely new things this codebase has never had: a **Self-Improvement
Proposal** system that lets the company propose changes to *itself* —
new risk rules, new research workflow steps — grounded only in real,
citable evidence from the systems above, never a fabricated trigger;
and a small set of real **aggregation views** (an Executive Learning
Summary, an extended Knowledge Graph) that compose already-real numbers
into one place without recomputing any of them under a new name.

## Mission

Give the CEO one honest answer to two questions this codebase can
otherwise only answer by checking nine different tabs: "what should
this company change about itself, based on real evidence?" and "how is
each executive's own learning actually progressing?" — without
inventing a tenth learning system to answer them.

## Philosophy

Winning teaches, losing teaches, research teaches — and this codebase
already builds a `CaseStudy`/`SuccessStudy` for every one of those
events (`app/mistakes.py`, `app/successes.py`). The discipline this
chapter holds itself to is refusing the easy, wrong move: re-deriving
"Strategy Evolution" as a new status enum when `app/strategy_lab.py`'s
`StrategyHealthStatus` already is that; re-deriving "Executive Learning"
as a new accuracy score when `app/coach.py`'s `AgentScore` already is
that. A learning system that duplicates its own memory to look more
complete is not more institutional — it is exactly the fragmentation
this chapter exists to prevent.

## Responsibilities

**Owns:** the Self-Improvement Proposal system (evidence-gated,
CEO-approved company-level change proposals), the Executive Learning
Summary (a real, non-recomputing aggregation of `AgentScore` +
`ThinkingProfile` + `AgentKnowledgeState` + Foundational Mentor
progress), and two new Knowledge Graph node types (`economic_event`,
extending Chapter 61's `build_knowledge_graph()`).

**Does NOT own** (see Appendix E), and explicitly refuses to duplicate:
Post-Trade Review / the Lesson Library (`app/mistakes.py`,
`app/successes.py`, `app/knowledge.py::search_knowledge()` — real,
unchanged), Strategy Evolution tracking (`app/strategy_lab.py`'s real
`StrategyHealthStatus`/`compute_strategy_health()` — reused by name,
never re-implemented), the strategy improvement pipeline itself
(Chapter 62's `sandbox.py`/`strategy_lab.py` idea→retired lifecycle),
per-agent skill/reflection systems (`app/academy.py`, `app/mentor.py`,
`app/foundational_mentors.py`, `app/wisdom.py` — all real, all
composed into the Executive Learning Summary rather than replaced), and
Company Health/Score (`app/company_health.py`, `app/company_score.py`
— Chapter 63's real territory; Part 2's Company Evolution Score is
explicitly *not* a third copy of these, see Part 2's own honesty
boundary).

## Ownership

| Brief concept | Real system today | This chapter's real move |
|---|---|---|
| "Post-Trade Review Engine" | `app/mistakes.py::generate_case_studies()`, `app/successes.py::generate_success_studies()` — real, wired into `nexus.py`'s tick loop on every closed trade, 9 named categories (6 loss, 3 win), `MAX_CASE_STUDIES`/`MAX_SUCCESS_STUDIES = 60` | **Cited, not rebuilt.** Every `CaseStudy`/`SuccessStudy` already carries thesis-adjacent fields (`decisionProcess`, `missedInformation`, `lessonsLearned`, `recommendedImprovements`) |
| "Lesson Library" | `app/knowledge.py::search_knowledge()`, `KNOWLEDGE_CATEGORIES = ("lesson", "mistake", "strategy", "coach_review")` | **Cited, not rebuilt.** Already searchable, already categorized |
| "Strategy Evolution" (win rate, profit factor, drawdown, improve/pause/retire) | `app/strategy_lab.py`'s real `StrategyHealthStatus` (7-value ladder: `excellent`→`retire_candidate`), `compute_strategy_health()`, reused verbatim by Chapter 75 already | **Cited by name, not re-invented.** "Sharpe Ratio" stays the same documented placeholder `app/analytics.py` already discloses (no real daily-return series exists); "recovery factor," "expand," and "merge" have no real signal anywhere and are explicit cuts, not fabricated |
| "Executive Learning" (per-executive accuracy, training recs) | `app/coach.py::AgentScore` (`researchAccuracy`, `confidenceCalibration`), `app/mentor.py::ThinkingProfile` (6 real traits), `app/academy.py::AgentKnowledgeState`, `app/foundational_mentors.py`'s real per-agent aptitude/certification | **Real, new aggregation only** — `compute_executive_learning_summary()` composes all four into one view per agent. Zero new computation |
| "Academy Integration" (auto-generate lessons) | `app/academy.py`, `app/academy_research.py` — a fixed 6-topic catalog, explicitly "no LLM available to write original research" (confirmed independently in three modules' own docstrings) | **Cannot be honestly built as briefed.** The one real hook: a `CaseStudy`/`SuccessStudy` now nudges the generating agent's `AgentKnowledgeState.points` (small, capped) — not "generated lesson content" |
| "Knowledge Graph Expansion" | Chapter 61's `build_knowledge_graph()` already has `trade`/`strategy`/`case_study`/`black_swan_event`/`research` nodes | **One real, narrow addition**: `economic_event` nodes sourced from Chapter 71's real `EconomicIntelligenceReport`, linked to same-`simDay` trade/case-study nodes. "Indicator" nodes are cut — no real per-trade indicator linkage exists to build them honestly |
| "AI Improvement Lab" | `app/innovation.py` is a naming trap (agent skill points from Devil's Advocate `ChallengeReport`s, unrelated) — the real pipeline is Chapter 62's `sandbox.py`/`strategy_lab.py`, scoped to strategies only | **Not built as a separate lab.** Chapter 62 already owns strategy-level continuous improvement; this chapter's Self-Improvement Proposals (below) cover the *company-level* gap Chapter 62 explicitly does not reach |
| "Self-Improvement Proposals" | *(genuinely does not exist)* | **Real, new.** See below |
| "Company Evolution Score" | `app/company_health.py`'s real 21 sub-scores, `app/company_score.py`'s real 7-metric mean | Deliberately deferred to **Part 2**, where it is built as a distinct rate-of-change metric, not a third snapshot score — see Part 2's own honesty boundary |

## Self-Improvement Proposals

The one genuinely new system in Part 1. TradeTown may propose a change
to itself — never a trade, never a strategy (Chapter 62 already owns
that) — grounded in real, citable evidence, never a fabricated trigger.
Two real, evidence-gated generators ship; the brief's other six
proposal categories are named in the schema but have no real generator
yet, exactly the same honesty posture Chapter 68 took for its
not-yet-real broker categories:

1. **Recurring Mistake Pattern → `"risk_rule"` proposal.** When the same
   `CaseStudy` category (`app/mistakes.py`'s six) occurs at or above a
   disclosed threshold among a recent window of closed losing trades,
   propose a risk-rule change, citing the specific `CaseStudy` ids as
   evidence — never a vague "the company makes mistakes."
2. **Strategy Retirement Cluster → `"research_workflow"` proposal.**
   When two or more strategies retire to `app/strategy_lab.py`'s Failed
   Archive within a recent window, propose a research-workflow change,
   citing the specific `FailedStrategyArchiveEntry` ids.

Every proposal carries: `title`, `category` (one of the brief's eight
named categories — `risk_rule`, `dashboard`, `research_workflow`,
`position_sizing`, `new_executive`, `automation`,
`knowledge_organization`, `ui` — only the first two have a real
generator), `reasoning`, `evidence` (real source ids, never invented),
`benefits`, `risks`, `estimatedComplexity` (`small`/`medium`/`large` —
not a dollar figure; no real development-cost signal exists anywhere in
this codebase to compute one honestly), `priority`, `confidence`,
`status` (`pending`/`approved`/`rejected`/`implemented`), and a
`ceoNote`. Resolution is CEO-manual only — never automation-eligible,
the same restraint `app/constitution.py`'s own Amendment flow already
holds itself to for company-level changes.

**Audit finding, fixed (this session):** `implemented` was a real,
declared `status` value that nothing in the codebase ever set — the only
real transition was `pending` → `approved`/`rejected`
(`decide_self_improvement_proposal()`), confirmed by grep before this
fix. There is no single, well-defined state mutation an approved
`risk_rule` or `research_workflow` proposal maps onto (a risk rule
could mean any of several `RiskLimits` fields, by an amount this
codebase has no formula for) — inventing one would fabricate a business
rule this Design Bible never specified, exactly what this chapter's own
KPIs section already names as the reason "proposal success rate" isn't
honestly computable ("a new risk rule someone manually adds to
`RiskLimits`"). So the fix mirrors that same sentence literally: a new
`mark_self_improvement_proposal_implemented()` (`app/self_improvement.py`)
and `POST /api/self-improvement/proposals/implement` let the CEO record,
in their own words (`implementationNote`), that they carried an approved
proposal out elsewhere in the game — a real, manual, CEO-authored status
transition, never an automatic mutation of `RiskLimits` or anything
else. Only an already-`approved` proposal can be marked `implemented`.
Covered by `tests/test_self_improvement.py::TestMarkSelfImprovementProposalImplemented`.
No frontend control exists for this yet (see this chapter's own missing
frontend panel, tracked separately). A `visionAlignmentScore`
field exists on the schema but stays `null` until Chapter 74.5 ships and
wires it — declared now so the schema does not need a breaking change
later, not because the field does anything yet.

## Executive Learning Summary

Per-agent, real, and purely compositional: `researchAccuracy`/
`confidenceCalibration` (latest `CoachReport.agentRankings` entry),
`ThinkingProfile` (curiosity/evidence quality/open-mindedness/
humility/reasoning/collaboration), `AgentKnowledgeState` (points, tier,
level), and Foundational Mentor progress (`graduationStatus`,
certification, if any). No new number is computed — this view exists
because no single screen joins these four already-real systems today.

## Knowledge Graph Extension

`build_knowledge_graph()` (Chapter 61) gains one new node type,
`economic_event`, sourced from Chapter 71's real
`EconomicIntelligenceReport` records, linked via a same-`simDay` edge
to any `trade`/`case_study` node recorded that day. This is the one
real, honestly-buildable gap Chapter 61's own Implementation Notes
already named ("indicators and economic events aren't graph nodes
yet") — "indicator" nodes are cut, since no per-trade indicator
linkage exists anywhere to build them from real data rather than a
guess.

## Inputs

Real: closed trades (`app/portfolio.py`), `CaseStudy`/`SuccessStudy`
records (`app/mistakes.py`/`app/successes.py`), `FailedStrategyArchiveEntry`
records (`app/strategy_lab.py`), `CoachReport` (`app/coach.py`),
`ThinkingProfile` (`app/mentor.py`), `AgentKnowledgeState`
(`app/academy.py`), Foundational Mentor certification records
(`app/foundational_mentors.py`), `EconomicIntelligenceReport`
(`app/economic_intelligence.py`).

## Outputs

Real: `SelfImprovementProposal` records (persisted, capped, WS-broadcast,
CEO-decidable), `ExecutiveLearningSummary` per agent (computed
on-demand, not persisted — same convention Chapter 61's Knowledge Graph
and Chapter 65's Regime Reconciliation already use), extended
`KnowledgeGraph` (computed on-demand, unchanged persistence model).

## Internal Workflow

Recurring-mistake and strategy-retirement-cluster checks run once per
sim-day tick in `app/nexus.py`, immediately after `mistakes.py`/
`strategy_lab.py`'s own real event generation for that tick (so a
proposal always cites events that already exist, never a
same-tick race). The Executive Learning Summary and extended Knowledge
Graph are computed fresh per request — no new persisted state, no new
tick-loop cost for either.

## Decision Logic

Proposal generation is threshold-based and disclosed, not a black-box
score: a fixed occurrence count within a fixed recent window per
generator (both constants named and published in Implementation
Notes), matching this codebase's "no hidden weighting" convention
throughout (`app/company_score.py`'s own stated rule, reused
everywhere since).

## Department Cooperation

**Reads from:** `app/mistakes.py`, `app/successes.py`,
`app/strategy_lab.py`, `app/coach.py`, `app/mentor.py`,
`app/academy.py`, `app/foundational_mentors.py`, `app/economic_
intelligence.py`. **Provides to:** the CEO (proposal approval),
Chapter 74.5's future Vision Alignment Engine (the reserved
`visionAlignmentScore` field). **Does not feed** the Trade Gatekeeper —
Self-Improvement Proposals are company-level, never trade-level, and
have no path into `app/gatekeeper.py`.

## CEO Controls

| Control | Status |
|---|---|
| Approve / Reject a Self-Improvement Proposal | Real — the only resolution path; never automation-eligible |
| Mark an approved proposal Implemented, with a note | Real — `POST /api/self-improvement/proposals/implement`; CEO-manual record only, never an automatic mutation |
| Recurring-mistake / retirement-cluster thresholds | Real, CEO-editable (mirrors `RiskLimits`' own editable-constant convention) |
| Executive Learning Summary view | Real, read-only |

## KPIs

Real: proposals generated, proposals approved vs. rejected, time from
proposal to CEO decision. **Not honestly computable:** any "proposal
success rate" — this codebase has no mechanism to measure whether an
*approved* proposal's real-world change (a new risk rule someone
manually adds to `RiskLimits`) actually reduced the mistake pattern
that triggered it; that would require a second, later evidence-gated
check this chapter does not build.

## Reports

Real: the Self-Improvement Proposal list itself, filterable by
category/status. Part 2's Institutional Evolution Report subsumes any
periodic "what did the company learn this month" reporting rather than
this chapter building a second one.

## Safety Systems

CEO-manual approval only; no proposal can self-implement. Proposals
never touch `RiskLimits`, `Account`, or any trading parameter directly
— approving one is an acknowledgment, not an automated mutation, since
this codebase has no real mechanism to safely apply "add a new risk
rule" as code at runtime.

## Dependencies

`app/mistakes.py`, `app/successes.py`, `app/strategy_lab.py`,
`app/coach.py`, `app/mentor.py`, `app/academy.py`,
`app/foundational_mentors.py`, `app/knowledge_graph.py`,
`app/economic_intelligence.py`.

## Connected Features

Chapter 61 (Knowledge Graph — extended, not duplicated), Chapter 62
(Innovation Lab / strategy pipeline — explicitly not re-implemented),
Chapter 63 (Company Health/Score — explicitly not re-implemented),
Chapter 71 (Economic Intelligence — source of the new `economic_event`
node type), Chapter 74.5 (future Vision Alignment Engine — reserved
`visionAlignmentScore` field only).

## Deferred Features

Per this codebase's established documentation structure (see Chapter
70's Deferred Features section for the template this reuses):

**Academy auto-generated lesson content.** *Current state:* `app/
academy_research.py` runs a fixed 6-topic catalog with pre-templated
text; no content-generation capability exists. *Missing
infrastructure:* an LLM or equivalent text-generation dependency —
confirmed absent project-wide (`requirements.txt` carries none).
*Dependencies:* none buildable without that dependency. *Recommended
future chapter:* none — this requires an infrastructure decision
(adding an LLM dependency) outside any single department chapter's
scope. *Estimated complexity:* large, and gated on an infrastructure
decision, not a chapter-sized task. *Risk of building prematurely:*
fabricated "lessons" with no real backing would violate this
codebase's no-fabrication rule at its most visible surface — the
Academy is the one place a CEO would directly read generated prose.

**"Indicator" Knowledge Graph nodes.** *Current state:* cut from this
chapter's real `economic_event` addition. *Missing infrastructure:* no
per-trade indicator linkage exists anywhere — `EconomicHealthScore`'s
five factors are computed company-wide, not per-trade, so there is no
real edge to draw from a specific indicator value to a specific trade.
*Dependencies:* would require Chapter 71 or Chapter 65 to start
recording a per-trade indicator snapshot, which neither does today.
*Recommended future chapter:* an addendum to Chapter 61 or Chapter 71,
whichever adds per-trade indicator recording first. *Estimated
complexity:* medium. *Risk of building prematurely:* a same-day
heuristic edge (like `economic_event`'s) would be honest for
event-to-trade proximity; a fabricated indicator-to-trade causal edge
would not be, and is exactly the kind of invented causality Chapter
71's own Market Narrative Engine already refuses to produce.

**The other five Self-Improvement Proposal categories** (`dashboard`,
`position_sizing`, `new_executive`, `automation`, `ui`). *Current
state:* named in the schema, no real generator. *Missing
infrastructure:* each would need its own real, evidence-gated trigger —
e.g. a `dashboard` proposal would need a real signal that a CEO is
manually cross-referencing multiple tabs repeatedly, which this
codebase has no telemetry to detect. *Dependencies:* vary per category.
*Recommended future chapter:* an addendum to this chapter once a real
trigger signal exists for any one of them. *Estimated complexity:*
small per category, once a real trigger is identified. *Risk of
building prematurely:* a proposal category with no real evidence path
would either sit permanently empty (harmless but dead weight) or tempt
a future implementer into fabricating a trigger just to populate it —
exactly what this chapter's Philosophy section exists to prevent. (A
sixth category, `knowledge_organization`, is no longer in this bucket —
see the Trading Psychology & Discipline, Piece D addendum at the end of
this chapter for its own real trigger, added later.)

## Company Principle

"A company that learns from the same mistake twice has not actually
learned — it has only recorded it." Every Self-Improvement Proposal
this chapter generates must trace to a *specific*, named, recurring
event, never a general sense that something could be better — the same
evidence-first standard `app/constitution.py`'s Amendment flow already
holds every company-level change to.

## Implementation Notes

**What's real today, before this chapter, and reused rather than
duplicated:** `app/mistakes.py`, `app/successes.py`, `app/knowledge.py`,
`app/knowledge_graph.py` (Chapter 61 — Substantially implemented),
`app/strategy_lab.py`/`app/sandbox.py` (Chapter 62 — Partially
implemented), `app/coach.py`, `app/mentor.py`,
`app/foundational_mentors.py`, `app/company_health.py`/`app/
company_score.py` (Chapter 63 — Substantially implemented). **What this
chapter adds, real:** `app/self_improvement.py` (new) — two
evidence-gated Self-Improvement Proposal generators, CEO
approve/reject/mark-implemented, `compute_executive_learning_summary()`;
a new `economic_event` node type in `app/knowledge_graph.py`'s
`build_knowledge_graph()`; a real frontend, `EvolutionPanel.tsx`'s
Self-Improvement Proposals and Executive Learning Summary sections
(shared with Part 2 below and Chapter 74.5, all bundled into one
Command Center tab). **What's genuinely, entirely unbuilt, named
and not faked:** auto-generated Academy lesson content, "indicator"
graph nodes, and six of eight Self-Improvement Proposal categories —
see Deferred Features. See Part 2 below for the Institutional Evolution
Engine and its own Company Evolution Score.

**Pass — Learning Events (CEO Company Health + Live Market Realism
directive, Section 3):** the one real Academy Integration hook named in
the table above (row 111) — a filed `CaseStudy`/`SuccessStudy` nudging
the generating agent's `AgentKnowledgeState.points` — plus `app/
academy.py`'s other three real point-award call sites (research
completion, an Academy project finishing, meeting attendance) and the
mentorship bonus all previously surfaced only as a free-text
`app/scribe.py` Memory entry the instant a real Knowledge Tier was
crossed, with no structured, queryable record of the transition itself.
`award_points()` now returns a real `LearningEvent`
(`agentId`/`skillDomain`/`previousCompetency`+`previousLevel`/
`newCompetency`+`newLevel`/`source`/`pointsAwarded`/`totalPoints`/
`createdAt`) instead of the raw `AgentKnowledgeState`, requiring an
explicit `source` naming exactly which of these five real callers
triggered the award — `research_completion`, `academy_project`,
`meeting_attendance`, `mentorship`, or `case_study_reflection` — never
a fabricated sixth reason. Each event is appended to a capped (60),
permanent `learningEvents` archive list (same cap-and-trim pattern as
`app/mistakes.py`'s `MAX_CASE_STUDIES`), broadcast live over the
WebSocket tick and surfaced in the Command Center's KNOWLEDGE tab
(`AcademyPanel.tsx`'s "Learning Events" card). The existing Memory entry
is kept unchanged as the human-readable company-history version of the
same real event — `LearningEvent` is the queryable structured version,
not a replacement. Along the way, fixed a real pre-existing gap:
`maybe_run_mentorship()` computed its own tier-up via `award_points()`
but discarded the result, so a mentorship bonus that itself crossed a
tier threshold was silently never recorded anywhere (no Memory entry,
no `LearningEvent`) — it now returns the `LearningEvent` alongside the
pairing, recorded through the same path as every other source.

---

# Part 2 — Institutional Evolution Engine

**Status:** Substantially implemented, backend and frontend — same
stale-line fix as Part 1 above; `app/evolution.py` and its two router
endpoints are real, now surfaced in `EvolutionPanel.tsx`'s Company
Evolution Score and Institutional Evolution Reports sections. Same
relationship to
Part 1 as Chapter 72's Institutional Survival Score has to its own Part
1 Early Warning Score: a company-wide, longer-horizon rollup built on
top of Part 1's real per-event machinery, not a second, competing
learning system. CLSIS (Part 1) is individual/event/trade-level
learning; the Evolution Engine (Part 2) is company-wide/monthly/
long-term learning — the same underlying architecture at two different
time horizons, per this chapter's own Company Principle: a mistake
noticed once (Part 1) only becomes institutional if the company also
notices the *pattern* of its own mistakes over months (Part 2).

## Executive Summary

The brief asks for a Monthly Company Review, Evolution Proposals, and
long-term Company Evolution tracking. Two of those three already have
close, real monthly precedents this codebase runs today —
`app/goals.py::generate_strategic_review()` and `app/executive_review.py
::generate_executive_review()` — so the Institutional Evolution Report
below is built as a real *composition* of those two reports plus Part
1's own Self-Improvement Proposals and the period's Case/Success
Studies, not a third independent monthly report competing with the two
that already exist (and not a fourth, alongside Chapter 70 Part 1's
Board Report — see Ownership below for why that one stays distinct).
Evolution Proposals reuse Part 1's own `SelfImprovementProposal` schema
and generators rather than inventing a parallel proposal system, per
this chapter's own "operating at two time horizons" design. The one
genuinely new artifact is the Company Evolution Score — built, per
explicit instruction, as a distinct rate-of-change metric rather than
a third snapshot alongside `CompanyHealth` and `CompanyScore`.

## Mission

Answer, once a real sim-month, "is this company actually getting better
at learning from itself?" — a question no existing report answers,
because `CompanyHealth`/`CompanyScore` measure current state and
`StrategicReview`/`ExecutiveReview` measure goal/department progress,
not the rate of institutional learning itself.

## Philosophy

A snapshot score answers "how healthy is the company right now."
An evolution score must answer a different question — "is the *rate* at
which this company learns increasing or decreasing" — or it is not
worth building at all. Every input below is therefore a real count or
delta over a real period, never a re-read of an existing static score.

## Ownership

**Owns:** the Institutional Evolution Report (monthly, composing real
existing reports), the Company Evolution Score (a new, disclosed,
5-factor plain-mean rate-of-change metric — matching `app/
company_score.py`'s own "no hidden weighting" convention — computed
over monthly/quarterly/yearly windows), Evolution Proposals (Part 1's
`SelfImprovementProposal`s, surfaced and prioritized at monthly
cadence).

**Does NOT own, and explicitly does not duplicate:** `CompanyHealth`'s
21 sub-scores or `CompanyScore`'s 7-metric mean (`app/company_health.py`,
`app/company_score.py` — Chapter 63's real territory; the Evolution
Score's inputs are disjoint counts/deltas, never a re-read of either),
`StrategicReview` (`app/goals.py` — real, monthly, composed into the
Institutional Evolution Report rather than replaced), `ExecutiveReview`
(`app/executive_review.py` — real, monthly, composed rather than
replaced), Chapter 70 Part 1's `BoardReport` (real, quarterly-and-daily,
governance/risk-focused — this report is learning-focused; both exist,
neither is a copy of the other, see the table below).

| Report | Cadence | Focus | Real source |
|---|---|---|---|
| `BoardReport` (Ch. 70 Pt. 1) | daily / quarterly / emergency | governance, risk, required CEO decisions | `app/board.py` |
| `StrategicReview` (Ch. 64) | monthly | goal progress, milestones, resource allocation | `app/goals.py` |
| `ExecutiveReview` (Ch. 63) | monthly | company score delta, department activity, knowledge gained | `app/executive_review.py` |
| `CoachReport` (v0.5) | weekly / monthly | per-agent research accuracy, win/loss patterns | `app/coach.py` |
| **`InstitutionalEvolutionReport` (this chapter)** | **monthly** | **learning volume, proposal outcomes, strategy maturation, Evolution Score** | **`app/evolution.py` (new)** |

## Institutional Evolution Report

Generated once per real sim-month, composing — never recomputing —
the period's: latest `StrategicReview`, latest `ExecutiveReview`,
latest monthly `CoachReport`, the top 3 `CaseStudy` and top 3
`SuccessStudy` records of the period (by real trade P&L magnitude,
already a field on both), every `SelfImprovementProposal` generated or
resolved in the period, and the period's Company Evolution Score.
Persisted, capped (`MAX_EVOLUTION_REPORTS`, matching the 20-cap
convention `MAX_COACH_REPORTS`/`MAX_EXECUTIVE_REVIEWS` already use for
monthly-cadence reports), WS-broadcast.

## Company Evolution Score

A disclosed, unweighted mean of five real, period-scoped factors — no
hidden weighting, matching `app/company_score.py`'s own stated
convention:

1. **Learning Volume** — `CaseStudy` + `SuccessStudy` count generated
   this period, normalized against a disclosed cap.
2. **Proposal Execution** — Self-Improvement Proposals *implemented*
   this period ÷ proposals *generated* this period (a real completion
   rate, floored at 0 when no proposals existed).
3. **Knowledge Growth** — company-wide `AgentKnowledgeState.points`
   gained this period, normalized against a disclosed cap.
4. **Strategy Maturation** — `app/strategy_lab.py` Hall of Fame
   entries minus Failed Archive entries this period, floored at 0,
   normalized.
5. **Governance Evolution** — 1 if at least one `app/constitution.py`
   Amendment was ratified this period, else 0 (a rare, binary signal by
   design — amendments are intentionally infrequent).

Each factor is 0-100; the score is their plain mean, published
alongside every one of its five inputs so the CEO can see exactly what
moved it — never a single opaque number. Computed over monthly,
quarterly (3-month), and yearly (12-month) windows on request, matching
the brief's own "Monthly / Quarterly / Yearly Improvement" framing.
**Explicitly not a duplicate of `CompanyHealth`/`CompanyScore`:** every
one of the five inputs above is a period-scoped count or delta: none of
them re-reads a `CompanyHealth` sub-score or the `CompanyScore` mean
directly.

## Evolution Proposals

The same `SelfImprovementProposal` records Part 1 generates — this
report simply groups and prioritizes them by the period they were
generated or resolved in. No second proposal schema, no second CEO
approval flow.

## Inputs

Real: `StrategicReview` (`app/goals.py`), `ExecutiveReview` (`app/
executive_review.py`), `CoachReport` (`app/coach.py`), `CaseStudy`/
`SuccessStudy` records (Part 1), `SelfImprovementProposal` records
(Part 1), `app/strategy_lab.py` Hall of Fame / Failed Archive entries,
`app/constitution.py` amendment history, `AgentKnowledgeState` deltas
(`app/academy.py`).

## Outputs

Real: `InstitutionalEvolutionReport` (persisted, capped, WS-broadcast),
`CompanyEvolutionScore` (monthly/quarterly/yearly, computed on request,
also embedded in each report).

## Internal Workflow

Generated once per real sim-month rollover, in `app/nexus.py`,
immediately after the existing monthly `ExecutiveReview`/`StrategicReview`
generation calls (so the report always composes that month's real,
already-generated data, never a stale prior month's).

## Decision Logic

The Company Evolution Score's five factors and their normalization caps
are fixed constants, published in Implementation Notes — no adaptive
or hidden weighting, the same discipline Part 1 holds its proposal
thresholds to.

## Department Cooperation

**Reads from:** Part 1 (`SelfImprovementProposal`), `app/goals.py`,
`app/executive_review.py`, `app/coach.py`, `app/strategy_lab.py`,
`app/constitution.py`, `app/academy.py`. **Provides to:** the CEO
(monthly report), Chapter 74.5's future Vision Alignment Engine (the
Evolution Score as one possible future alignment input — not wired
this pass).

## CEO Controls

| Control | Status |
|---|---|
| View Institutional Evolution Report | Real, read-only |
| View Company Evolution Score (monthly/quarterly/yearly) | Real, read-only |
| Evolution Score factor caps | Real, CEO-editable constants |

## KPIs

The Company Evolution Score itself, its 3 (monthly/quarterly/yearly)
window variants, and each of its 5 published factors individually.

## Reports

The Institutional Evolution Report is this chapter's one report — see
the cadence table above for why it does not duplicate `BoardReport`/
`StrategicReview`/`ExecutiveReview`/`CoachReport`.

## Safety Systems

Read-only; this report and score never gate a trade, never mutate
`RiskLimits`, and carry no automation authority — pure CEO-facing
synthesis, the same posture Chapter 73's Audit Log already holds.

## Dependencies

Part 1 (`app/self_improvement.py`), `app/goals.py`,
`app/executive_review.py`, `app/coach.py`, `app/strategy_lab.py`,
`app/constitution.py`, `app/academy.py`.

## Connected Features

Chapter 63 (Company Health/Score — deliberately disjoint inputs, not
duplicated), Chapter 64 (Strategic Review — composed, not replaced),
Chapter 70 Part 1 (Board Report — distinct cadence/focus, both real),
Chapter 74.5 (future Vision Alignment Engine — Evolution Score reserved
as a possible future input, not wired this pass).

## Long-Term Company Evolution

The brief's own "Track: Knowledge Graph Growth, Institutional Memory
Growth, Forecast Accuracy, Executive Improvement, Research Discoveries,
Automation Maturity, Capital Preservation, Decision Speed" list is
**not** built as eight separate new tracked metrics. Every one of them
either already has a real home (Forecast Accuracy = `CoachReport.
researchAccuracy`; Capital Preservation = `CompanyHealth`'s own real
sub-score; Executive Improvement = the Executive Learning Summary,
Part 1) or has no real signal to track honestly (Automation Maturity
and Decision Speed have no timing/telemetry infrastructure anywhere in
this codebase to measure from). The Company Evolution Score above is
this chapter's one real answer to "is the company getting better at
learning," not eight parallel new metrics duplicating seven other
chapters.

## Deferred Features

**Automation Maturity and Decision Speed tracking.** *Current state:*
no telemetry exists anywhere in this codebase measuring automation
adoption rate or decision latency. *Missing infrastructure:* a
timing/event-instrumentation layer around CEO decisions and
automation-mode usage — does not exist. *Dependencies:* would likely
piggyback on Chapter 67's Command Center event stream if extended.
*Recommended future chapter:* an addendum to Chapter 67 (TTOS), which
already owns the Command Center's real event surface. *Estimated
complexity:* medium. *Risk of building prematurely:* a fabricated
"Decision Speed" number with no real timestamps behind it would be
exactly the kind of manufactured sophistication this chapter's own
Philosophy section (Part 1) refuses to produce.

## Company Principle

"The company does not just remember what happened — it tracks whether
it is getting better at remembering." Every number in the Company
Evolution Score must be a real count over a real period; the day this
score stops moving because the underlying counts stopped moving is the
day the CEO should trust it, not the day it needs a sixth factor added
to keep climbing.

## Implementation Notes

**What's real today, reused rather than duplicated:** `app/goals.py::
generate_strategic_review()`, `app/executive_review.py::
generate_executive_review()`, `app/coach.py::generate_report()`,
`app/strategy_lab.py`'s Hall of Fame/Failed Archive, `app/
constitution.py`'s amendment history, Chapter 70 Part 1's `BoardReport`
(distinct, not superseded). **What this chapter adds, real:**
`app/evolution.py` (new) — `generate_institutional_evolution_report()`,
`compute_company_evolution_score()` (monthly/quarterly/yearly
windows), `MAX_EVOLUTION_REPORTS`. **What's genuinely, entirely
unbuilt, named and not faked:** Automation Maturity and Decision Speed
tracking — see Deferred Features above.

---

## Addendum — Loss/Win Classification, Formalized on Top of the
## Discipline Chamber (Trading Psychology & Discipline, Piece D)

**Origin.** The fourth piece of a CEO-approved trading-psychology
roadmap (Pieces A–C: the Behavioral Circuit Breaker, the Statistical
Evidence Gate on strategy retirement, and the Process Adherence Score —
see Chapter 66's own addenda). Piece D's brief: "Loss/Win classification
formalized on top of the existing Discipline Chamber; tie into CLSIS."

**Research finding that reshaped scope.** Most of "Loss/Win
classification" already existed before this piece touched anything:
`DisciplineReview.outcome` (`app/discipline.py`) is the real, single,
already-canonical win/loss definition (`pnl > 0` → win, else loss),
attached to every closed trade's review; the Library of Mistakes
(`app/mistakes.py`) and Library of Successes (`app/successes.py`)
already file real `CaseStudy` records on the loss and win sides
respectively, keyed off that same outcome. What was genuinely missing,
found by reading `app/nexus.py`'s own trade-close handler line by line:
the loss branch (`if trade.pnl <= 0:`) already called
`maybe_propose_recurring_mistake()` — CLSIS's own real tie-in — right
after filing new case studies; the win branch (`elif trade.pnl > 0:`)
filed its own real success studies but called nothing into CLSIS at
all. A real, literal structural asymmetry in the code itself, not a
hypothetical gap. This piece closes exactly that asymmetry and adds one
real, company-wide aggregate that didn't exist in any one place before
— it does not rebuild `DisciplineReview.outcome`, `app/mistakes.py`, or
`app/successes.py`.

**1. `compute_loss_win_classification()` (`app/discipline.py`) — the
"formalized" half.** A pure, on-demand aggregate over the Discipline
Chamber's own capped `DisciplineReview`/`CaseStudy` lists (the same
`MAX_DISCIPLINE_REVIEWS`/`MAX_CASE_STUDIES = 60` bound every other
aggregate in this codebase already lives within — honestly "the most
recent reviews on file," never claimed as a full historical archive).
Reads `outcome`/`tier` directly off each `DisciplineReview`, never
recomputes them. Reports:
- `winCount`/`lossCount`/`winRatePct` (null, never `0%`, when nothing
  has been reviewed yet).
- `byTier`: a win/loss count for each of the five Discipline tiers.
- `alignedCount` — a good-tier (`exemplary`/`sound`) win, or a
  poor-tier (`weak`/`reckless`) loss: process and outcome agree.
- `unluckyLossCount` — a good-tier trade that still lost. Real market
  variance, not a process failure — the exact distinction
  `discipline.py`'s own `_summary()` already draws per-review,
  formalized here across the whole population for the first time.
- `luckyWinCount` — a poor-tier trade that still won. A warning, not a
  validation — same source, same distinction, now aggregated.
- `mostCommonMistakeCategory`/`mostCommonSuccessCategory` — a real
  `Counter` over the loss-side and win-side `CaseStudy` categories
  respectively, `None` (never fabricated) when no case studies exist.
- `adequate`-tier trades count toward neither `alignedCount` nor
  `misalignedCount` — a genuine middle tier, not a strong signal either
  way; every count still sums back to `totalReviewed`.

Exposed at `GET /api/self-improvement/loss-win-classification`,
computed fresh on every call — the same on-demand convention
`get_evolution_score()` above already established, no sixth persisted
copy of these numbers.

**2. `maybe_propose_reinforce_success_pattern()`
(`app/self_improvement.py`) — the "tie into CLSIS" half.** The exact
structural mirror of `maybe_propose_recurring_mistake()` above, scanning
`SUCCESS_CASE_STUDY_CATEGORIES` (the win side) instead of the loss side:
when a real success-side `CaseStudy` category recurs at or above
`RECURRING_SUCCESS_THRESHOLD` (3) within the most recent
`RECURRING_SUCCESS_WINDOW` (15) win-side case studies, propose
formalizing that pattern as company knowledge — filed under
`knowledge_organization`, this category's **first real generator**
(previously named on the `SelfImprovementCategory` schema with no
trigger — see this chapter's own Deferred Features section, updated
above). Same edge-triggered dedup via `evidence` citation the loss-side
generator already uses; same CEO-manual approve/reject/implement flow,
no automation eligibility. Wired into `app/nexus.py`'s win-side
trade-close branch (`elif trade.pnl > 0:`), called once per trade right
after that trade's own success studies are recorded — line-for-line the
same placement the loss-side call already has in the branch above it.

**Frontend.** `EvolutionPanel.tsx` (the same Command Center `EVOLUTION`
tab this chapter's own Part 1/Part 2/Vision Board addenda already
share) gained a new "Loss/Win Classification" card between Self-
Improvement Proposals and Executive Learning Summary: win rate, by-tier
win/loss breakdown, the aligned/unlucky-loss/lucky-win counts, and the
most common mistake/success category — reusing `DisciplineTier`/
`CaseStudyCategory` types and `DisciplinePanel.tsx`'s own established
`TIER_TONE`/category-label conventions locally rather than
cross-importing another panel's module internals.

**What this addendum explicitly does not do.** It does not add a
second win/loss definition — `DisciplineReview.outcome` remains the one
canonical source. It does not touch `app/knowledge.py`'s older,
independent `derive_lesson()` (a cruder, pnl-sign-only "lesson"/
"mistake" classifier that predates the Discipline Chamber) — both
already agree on the same `pnl > 0` rule, so there is no real
divergence to reconcile, and `derive_lesson()` serves a different
consumer (`CompanyMemory`'s free-text log) this piece has no reason to
touch. It does not build a fourth/fifth CLSIS category — the six
categories with no real trigger (see Deferred Features) remain
genuinely deferred.

**Verification.** 22 new backend tests (`TestComputeLossWinClassification`
in `tests/test_discipline.py`, `TestMaybeProposeReinforceSuccessPattern`
in `tests/test_self_improvement.py`) covering empty input, win-rate
correctness, aligned/misaligned/unlucky-loss/lucky-win counts, the
`adequate`-tier neutral case, the full five-tier breakdown, most-common-
category derivation, threshold/window/dedup/refire behavior mirroring
the loss-side generator's own existing test matrix. Full backend suite:
1540/1540 passing. `mypy app/`, `ruff check app/ tests/` clean.
`tsc -b --noEmit`, `npm run lint`, `npm run build` clean. Live-verified
against the running dev server: `GET /api/self-improvement/loss-win-
classification` returns a correctly-shaped, honest empty-state response
against this session's real (currently trade-free) game state — no
crash, `winRatePct: null` rather than a fabricated `0%`, every count
zeroed rather than omitted; the new `EvolutionPanel.tsx` card renders
that same honest empty state live in Command Center (screenshotted).
Populating a non-empty live case was not reachable within this session
— the running dev server's current game state has never produced a
closed trade (all 29 decisions on file resolved `no_trade`) — so the
populated-classification and win-side-CLSIS-firing paths are proven by
the automated test suite above rather than a second live screenshot.

---

## Addendum — Two New Foundational Mentor Tracks (Trading Psychology & Discipline, Piece F)

**Origin.** The sixth piece of the CEO's trading-psychology roadmap.
Piece F's brief: "3-4 new Academy lessons via `app/
foundational_mentors.py`'s empty `mark_douglas`/`linda_raschke`
tracks."

**What already existed.** `app/foundational_mentors.py` (v0.7 Feature
49 Phase 3) already carries the real infrastructure this piece needed:
a seven-track roadmap (`_ROADMAP_ORDER`), each track a real, named,
ordered entry with real focus-area topics, but only `tjr` (8 lessons)
and `market_intelligence` (8 lessons, v0.7 Feature 51) shipped real
lesson content before this piece — the other five, including
`mark_douglas` and `linda_raschke`, were seeded `status: "planned"`
with zero lessons, exactly matching this module's own "seed the
roadmap entry, ship real content later" convention (see its module
docstring's "WHAT'S REAL VS. ROADMAP"). Adding a track's real content
is deliberately additive and small: write a `_LessonSpec` tuple, add it
to `_LESSON_SPECS_BY_MENTOR`, and `status: "active"` follows
automatically (`"active" if specs else "planned"` in
`default_foundational_mentor_state()`).

**The content-attribution boundary, unchanged.** Same rule `_TJR_
LESSONS`/`_MARKET_INTELLIGENCE_LESSONS` already established and this
module's own docstring states directly: this codebase has no HTTP
client, PDF/video parser, or LLM anywhere, so it cannot ingest any real
educator's actual published work. "Mark Douglas" and "Linda Raschke"
name only the real subject areas (trading psychology/probability
thinking; professional process/risk management) their tracks cover —
every lesson below is 100% original TradeTown-authored material citing
this codebase's own real, already-built mechanics, never a
transcription, summary, or quote of either person's actual work.

**The four new lessons — deliberately a small, honest start (2 per
track), not a backfill to match `tjr`'s 8 — each citing a specific real
mechanic, and each covering ground the existing `tjr`/`market_
intelligence` tracks don't already teach:**
- `md-probability` (Mark Douglas) — cites `app/confidence.py`'s
  Decision Confidence Engine, whose own module docstring already
  states "Never predicts whether a trade will win," and this same
  chapter's own Piece E `app/probability_language.py` regression guard
  as the enforced, permanent version of that principle.
- `md-revenge-trading` (Mark Douglas) — cites `app/behavioral_risk.py`
  's Behavioral Circuit Breaker (Chapter 66's Piece A): the real
  corroboration rule (timing alone never blocks; timing plus same-
  instrument or a loss-driven size increase does).
- `lr-gatekeeper-checklist` (Linda Raschke) — cites `app/
  gatekeeper.py`'s `evaluate_gatekeeper()`: ten real checks, a pure AND
  composition (`approved = all(c.passed for c in checks)`), a real
  auditable `GatekeeperRejection` naming exactly which check(s) failed.
- `lr-position-sizing` (Linda Raschke) — cites `app/risk_engine.py`'s
  `recommended_quantity()`: the real `min(risk_budget, position_cap)`
  rule, so tightening either of the CEO's two configured limits alone
  shrinks every future position size.

**A real, live catch from the Piece E regression guard.** Running
`audit_model()` against these four lessons during development caught
two genuine issues in the drafted text before they shipped: a quiz
option describing risk-engine sizing math used the phrase "the tighter
limit always wins" (a mechanical fact about which of two numeric caps
governs, not a market-outcome claim, but still matched the banned
`"always wins"` phrase) and a lesson explaining the probability-
language audit itself quoted literal banned-phrase examples
(`'sure thing'`, `'will definitely win'`) as illustration. Both were
rewritten (the sizing option now reads "is the one that actually
governs"; the audit lesson now says "absolute-certainty phrasing"
without quoting the literal banned examples) rather than weakening the
checker — proof the Piece E guard is a real, working enforcement
mechanism, not a report that only checks itself.

**Downstream consequence, found and fixed.** `app/company_health.py`'s
`_talent_development()` executive metric divides real graduated-student
count by `students × count of "active" mentor tracks` — a real
denominator that legitimately grows every time a new track ships real
content (the same consequence v0.7 Feature 51's own `market_
intelligence` addition already caused once, and left a code comment
documenting). `tests/test_company_health.py`'s `_strong_executive_
overrides()` fixture and two `TestExecutiveTier` tests assumed exactly
two active tracks; all three were updated to the new real count of four
(and the "everything strong" fixture now grants a graduated
credential on all four active tracks, not two) — a genuine, correct
behavioral consequence of shipping real content, not a workaround.

**What this addendum explicitly does not do.** It does not backfill
`al_brooks`/`tom_hougaard`/`mike_bellafiore` — those three roadmap
entries remain honestly `"planned"` with zero lessons. It does not add
any frontend code — `MentorLibraryPanel.tsx` already renders any
mentor's lessons generically from the real `FoundationalMentorProfile`
the backend serves, with no per-mentor-id branching anywhere in the
frontend, so no UI change was needed for the new content to render.

## Addendum — Agent Performance Reviews (CEO directive "Features 26-30," Feature 27)

**Research finding, documented before code was written.** This chapter's
own `app/coach.py` (`AgentScore`) and `app/mentor.py` (`ThinkingProfile`)
are the two closest existing per-agent evaluation signals, and both have
real gaps against the CEO's Feature 27 ask: `AgentScore` is scoped to
only the four `RESEARCHER_IDS` (Sentinel, Guardian, Keystone, and every
other non-researcher agent never gets one), and `ThinkingProfile` fake-
defaults every trait to a neutral 50.0 with zero real evidence instead
of an honest NOT_ENOUGH_EVIDENCE state. `app/mentor.py`'s own module
docstring already named this exact gap: *"Personal Coaching /
improvement areas per employee — would require a real per-agent
weakness signal distinct from ThinkingProfile's own traits ... none
exists, so this is left as an explicit scope cut."* `app/self_
improvement.py`'s `ExecutiveLearningSummary` is the closest thing to a
prior "one place for an agent's numbers" attempt, but it's a thin
composition of the above with no new evaluation logic, no disclosed
sample size, no role-awareness, and no process-vs-outcome split.

**What was built:** `app/performance_review.py`, a synthesis layer over
real, already-computed evidence — not a parallel scoring engine. One
real `AgentPerformanceReview` per agent per real week, across 8
dimensions (process quality, risk discipline, decision accuracy,
calibration, collaboration, learning trend, recurring mistakes, P&L
attribution), each either real evidence or an honest `value=null`
(reusing `app/process_adherence.py`'s exact nullable-score/disclosed-
sample-size shape rather than `ThinkingProfile`'s fake-neutral-50
pattern). `process_quality_avg`/`outcome_quality_avg` stay structurally
separate, mirroring `app/discipline.py`'s own process-score-never-sees-
pnl discipline — a good process that lost to real market variance never
drags down process quality; a lucky win from a weak process never
inflates it.

**Role-awareness, real not cosmetic.** `AGENT_ROLE_CLASS` is this
codebase's first machine-usable role-evaluation taxonomy over `app/
agents.py`'s `AGENT_PROFILES` (previously only free-text `occupation`
strings existed). It doesn't force every dimension to a number
regardless of role — it lets a reader correctly interpret a missing
one: Sentinel structurally never receives a `ResearchItem` assignment
(see `app/research.py`'s `RESEARCHER_IDS`), so its `decisionAccuracy`
dimension is honestly `NOT_ENOUGH_EVIDENCE` every single week — that's
the truth about the role, not a gap in the review. Live-verified: a
real review for Sentinel (`roleClass: "risk"`) generated by the running
dev server showed exactly this — real `processQuality`/`riskDiscipline`/
`collaboration`/`learningTrend` data, honest `null` for `decisionAccuracy`/
`calibration`/`recurringMistakes`/`pnlAttribution` (no closed trades
that week), `outcomeQualityAvg: null` (no outcome dimension had data),
`status: "evaluated"` (5 real evidence items cleared the threshold).

**Reused formulas, not reinvented ones:** `app/analytics.py`'s
`research_accuracy()`/`confidence_accuracy()` for decision accuracy and
calibration; `app/mentor.py`'s `_factor_average()` and
`_COLLABORATION_EVENTS_FOR_100` for risk discipline and collaboration.
`recurring_mistakes` and `pnl_attribution` are genuinely new
computations (no prior per-agent P&L/mistake-attribution signal
existed), built on the same `PaperTrade.supportingAgents`/
`TradeDecision.supportingAgents` join every other per-agent filter in
this codebase already uses.

**The real hook for Feature 28.** `trend` (improving/declining/stable/
not_enough_history, compared against the same agent's own prior review)
and `weakest_dimension_id` (the lowest-scoring measured dimension this
period) exist specifically so Feature 28's future training
recommendations have real data to read from, per the CEO's own worked
example (an agent misjudging volatility regime → flagged by Performance
Review → Academy recommends training) — without building Feature 28
itself yet, per that feature's own staging rule.

**Frontend:** extends the existing `TalentPanel.tsx` (`TALENT` tab, the
same panel that already reuses `ThinkingProfile` for its own
"Performance Analysis" section) with a new "Agent Performance Review"
card, reusing that panel's existing employee selector rather than
adding a new one or a new tab.

**Verified:** 21 new backend tests (`tests/test_performance_review.py`)
covering every real agent having a role class, zero-evidence honesty,
process quality never seeing P&L, recurring-mistake attribution only to
the real supporting agent (never blamed on an agent who didn't support
the decision, never counted from a non-mistake success-category case
study), decision accuracy/calibration real-filtering by agent and
period, collaboration's real contribution/insight counting, the
evidence-count status gate, trend detection against a real previous
review, and weakest-dimension selection. Full backend suite (1843
tests), `mypy`, `ruff` all clean. `tsc -b --noEmit`, `eslint`,
`vite build` all clean. Live Playwright verification confirmed real
`AgentPerformanceReview` data (15 reviews, one per real agent) generated
by the running simulation after a real `POST /api/time/advance` to a
week boundary, and rendered correctly in the TALENT tab's new card.

**Verified:** 6 new/extended tests in `tests/test_foundational_
mentors.py` (`TestMarkDouglasAndLindaRaschkeTracks`: real 2-lesson
content in order, exactly one real correct answer per quiz, the content
disclaimer, real employee auto-progression through either track once
activated, and the Piece E probability-language audit passing clean on
every new lesson) plus 3 updated tests in `tests/test_company_
health.py` reflecting the real four-active-track denominator. Full
backend suite green (1555/1555), `mypy app/`/`ruff check app/ tests/`
clean. No frontend changes, so no `tsc -b --noEmit`/`npm run lint`
re-verification was needed. Live-verified against the running dev
server: `default_foundational_mentor_state()` (the real function a
brand-new game calls) produces the correct real content and `status:
"active"` for both tracks. The running dev server's own persisted save
predates this change — `FoundationalMentorState` is seeded once at
game creation and never re-synced against newer code on load, the same
"new content applies to new games" boundary `market_intelligence`'s
own v0.7 Feature 51 rollout already established — so its live
Mentor Library screenshot honestly still shows `Linda Raschke Track —
PLANNED`/`Mark Douglas Track — PLANNED` for this specific, older save;
the new content is proven by the automated test suite and the direct
`default_foundational_mentor_state()` call above instead of a second
live screenshot of a fresh game.

## Addendum — Academy + Skill Progression (CEO directive "Features 26-30," Feature 28)

**Research finding, documented before code was written.** `app/
academy.py` and `app/foundational_mentors.py` are the two closest
existing systems, and neither is a multi-domain per-agent skill score.
`academy.py`'s `AgentKnowledgeState` is a single scalar (`points`/`tier`/
`level`) plus one fixed, static `branch` string per agent — it never
breaks down into domains and never changes what it measures.
`foundational_mentors.py` is a real curriculum/certification delivery
engine (named-educator tracks, real lessons/quizzes, a genuine
active/suspended/revoked `CertificationRecord` lifecycle) — but its
tracks are curricula, not the 11 skill domains the brief names, and
graduating one produces a pass/fail certification, never a 0-100 skill
score with real history. A direct grep for `Skill*`/`SkillDomain`/
`SkillScore` across the whole backend and frontend returned zero hits —
confirmed genuinely new territory, not a rename of something that
already existed.

**What was built:** `app/skill_progression.py`, a third sibling module
(not a merge into either of the two above) defining the skill-domain
taxonomy the brief actually asked for. Each of the 11 named domains
(market structure, risk management, quant research, technical/
fundamental analysis, execution, statistical reasoning, regime
detection, prediction calibration, communication, collaboration,
research quality) was checked individually against real, already-
computed per-agent evidence:

- **5 measurable, real evidence, no new formula invented:**
  `risk_management` reuses `app/performance_review.py`'s
  `_risk_discipline()` (Position Sizing Discipline / Patience Discipline
  Factors); `research_quality` reuses `_decision_accuracy()`
  (`app/analytics.py`'s `research_accuracy()`); `prediction_calibration`
  reuses `_calibration()` (`app/analytics.py`'s `confidence_accuracy()`
  — the literal name in the brief matches a real dimension already);
  `collaboration` reuses `_collaboration()` (Reasoning Lab contributions
  + Reflection Chamber insights). `statistical_reasoning` is a
  **disclosed proxy** — this codebase has no dedicated statistics-
  methodology signal, so it reuses the exact Assumptions Challenged /
  Cross-Examination Discipline Factor average `app/mentor.py`'s
  `ThinkingProfile` "Reasoning" trait already computes (`_factor_
  average()`), stated as a proxy in the assessment's own `evidence`
  string rather than presented as a distinct measurement.
- **6 honestly `NOT_TRACKABLE_YET`, permanently, not a temporary
  evidence shortage:** `market_structure`, `quant_research`,
  `technical_fundamental_analysis`, `execution`, `regime_detection`,
  `communication` have no per-agent attribution mechanism anywhere in
  this codebase — each real company-level computation that's closest
  (`app/market_intelligence.py`'s structure/regime classifiers, `app/
  model_validation.py`'s Model Validator) is cited by name in the
  assessment's `evidence` string, with the specific structural reason it
  doesn't reduce to a per-agent number (e.g. `quant_research`: the Model
  Validator is a company/strategy-level governance seat this directive's
  own rules forbid repurposing into a per-agent skill signal).
  `communication` mirrors this chapter's own `ThinkingProfile`, which
  already reached and documented the identical conclusion for the same
  reason.

**The real closed loop.** `AgentSkillProfile.recommendedDomainId`/
`recommendedMentorId`/`recommendationReason` are set only when all
three hold: the agent's latest `AgentPerformanceReview.weakestDimensionId`
maps to one of the 4 skill domains with a genuine 1:1 Performance-Review
analog (`risk_discipline`→`risk_management`,
`decision_accuracy`→`research_quality`,
`calibration`→`prediction_calibration`,
`collaboration`→`collaboration` — `process_quality`/`learning_trend`/
`recurring_mistakes`/`pnl_attribution` have no single matching domain
and are deliberately left unmapped); a real, **content-backed**
Foundational Mentor track exists for that domain (`SKILL_DOMAIN_
RECOMMENDED_MENTOR`, covering only `tjr`/`mark_douglas`/`linda_raschke`/
`market_intelligence` — the four tracks with real written lessons per
`foundational_mentors.py`'s own `_LESSON_SPECS_BY_MENTOR`; the other
three roadmap tracks are still `"planned"` with zero content, so they
are never recommended); and the agent hasn't already graduated that
track (`FoundationalMentorState.progress`). `collaboration` has no
mapped mentor — Mike Bellafiore's "Trading Team Development" focus area
exists but has zero written lessons, so it is deliberately left
unrecommended rather than pointing the CEO at an empty track. This is
the literal mechanism the CEO's own worked example asked for ("agent
misjudges volatility regime → Performance Review flags it → Academy
recommends training → agent completes it → evaluated on subsequent
decisions → improvement becomes evidence of learning") — implemented
for the 4 domains where every link in that chain is real, rather than
faked for the domain (`regime_detection`) the worked example happened to
name, which remains `NOT_TRACKABLE_YET`.

**Improve/stagnate/regress, real history, no new lifecycle invented.**
`SkillAssessment.trend` compares this period's real value against the
same agent's own previous real assessment of the *same* domain
(`TREND_CHANGE_THRESHOLD_PCT`, reused directly from `app/performance_
review.py` rather than a second, possibly-drifting threshold) —
`improving`/`regressed`/`stagnant`/`not_enough_history`. This is a
measurement-level signal, deliberately separate from `foundational_
mentors.py`'s own certification revoke/suspend lifecycle (which remains
that module's sole authority over active/suspended/revoked status) —
Feature 28 does not duplicate or touch that lifecycle, only reads
`graduationStatus` from it for the recommendation gate above.

**Cadence.** Computed weekly in `app/nexus.py`, on the same real
`WEEKLY_INTERVAL_DAYS` gate as Feature 27's Agent Performance Reviews,
deliberately run immediately after that loop in the same tick so each
skill snapshot reads that week's freshly-computed `weakestDimensionId`
rather than a stale prior-week value.

**Frontend:** extends the existing `TalentPanel.tsx` (`TALENT` tab),
adding a new "Skill Progression" card between the Agent Performance
Review card and the Thinking Profiles card, reusing the panel's existing
employee selector rather than a new one or a new tab — the same
placement precedent Feature 27 established.

**Verified:** 20 new backend tests (`tests/test_skill_progression.py`)
covering the full 11-domain taxonomy on every profile, the 6
`NOT_TRACKABLE_YET` domains staying `null` even against heavy real input
data, each of the 5 measurable domains' real evidence, the
improving/regressed/stagnant/not-enough-history trend cases, the
training-recommendation gate (no review → no recommendation; an
unmapped weak dimension → no recommendation; a mapped weak dimension →
the correct real track; an already-graduated track → no recommendation),
and record/latest capping and filtering. Full backend suite, `mypy
app/`, `ruff check app/ tests/` clean. `tsc -b --noEmit`, `npm run
lint`, `npm run build` clean. Live-verified against the running dev
server: `GET /api/skill-profiles/{agentId}/latest` and a real `POST /api/
time/advance` to two consecutive week boundaries on a fresh save
produced 30 real `AgentSkillProfile` records (15 agents × 2 weeks) with
the exact expected honesty shape — 5 domains carrying real evidence, 6
permanently `null` with their disclosed structural reason — and the new
"Skill Progression" card rendered correctly in the TALENT tab
(`frontend/tests/talent.spec.ts`'s new Feature 28 test, run against the
live stack).

## Addendum — Agent Debate + Failure Review Board (CEO directive "Features 26-30," Feature 30)

The final stage of the 26->27->28->29->30 closed learning loop this
chapter has now documented start to finish. Placed here, continuing
this chapter's own CLSIS/learning-loop narrative, rather than in
`chapter-66-trading-psychology-discipline.md` (Discipline Chamber's own
home) — Feature 30's job is specifically to close the CEO's loop by
feeding real findings back into the other four stages this chapter
already covers, which is this chapter's subject, not Discipline's.

**Research finding, documented before code was written.** The brief
asked this piece to reuse `app/debate.py`/`app/devils_advocate.py`/
`app/discipline.py`'s existing machinery rather than invent a new
debate engine or failure taxonomy. Both `generate_debate()` and
`generate_challenge_report()` are pre-decision-only — post-hoc failure
classification is genuinely out of their scope, not a gap in them.
`app/mistakes.py`'s six `CaseStudyCategory` values already answer a
real, adjacent question — WHAT behavioral/process mistake occurred —
but never WHY the trade's underlying thesis actually failed. A trade
can be process-perfect and still rest on a wrong thesis (a well-run
debate can still misjudge the market), or have a flawless thesis undone
by a real process lapse: this is a genuinely separate axis, confirmed
by direct inspection of both taxonomies side by side, not assumed. A
whole-backend grep for failure_reason/root_cause/post_mortem/
review_board found zero hits — the gap was real.

**What was built:** `app/failure_review.py`'s `classify_failure()`, a
synthesis layer over evidence this codebase had already computed for
other real reasons — `DisciplineReview.factors` (reused from Feature
26's own Discipline Chamber), `app/process_adherence.py`'s
`_trading_mode_check()` (called verbatim), this trade's own already-
filed `CaseStudy` categories (Feature 27's Library of Mistakes), and the
Market Intelligence Learning Loop's `regime_consistent` read — never a
second, independently-computed statistic. Seven named `FailureReason`
values, picked by a fixed, disclosed precedence order (process
violation → risk management failure → information gap → market regime
misread → poor execution → bad thesis → unknown) so a trade matching
more than one real cause still gets exactly one honest classification,
most-objectively-verifiable signal first. An eighth candidate the CEO's
own worked example named, `external_shock` (a Black Swan event), was
researched and explicitly cut: `CrisisBriefing` is "Never persisted as
its own list" and carries no per-trade-linkable event id anywhere in
this codebase — disclosed as a real scope cut rather than shipped as a
permanently-dead enum value no code path could ever produce.

**Closing the loop — real feed-back into all four earlier stages,**
each independently live-verified, not just unit-tested:

- **Feature 26 (Institutional Memory):** a new `"failure_classification"`
  `InstitutionalMemorySource`. `promote_failure_classification()` fires
  for every named reason except `"unknown"`, which has no real lesson
  to file.
- **Feature 28 (Academy + Skill Progression):** this addendum's own
  `regime_detection` domain, above, is permanently `NOT_TRACKABLE_YET`
  because "no per-agent regime-call accuracy record exists anywhere" —
  Feature 30 is exactly the mechanism that changes that. `skill_
  progression.py`'s new `_regime_detection()` reads real, per-agent
  `market_regime_misread` attribution, computing a disclosed
  negative-only proxy (this agent's own real misread rate on classified
  losing trades this period) — never a claim of positive regime-call
  confirmation, which still doesn't exist per-agent anywhere. Flagged by
  the research as the single most valuable integration point, and now
  the first real per-agent regime-call signal this codebase has ever
  had.
- **Feature 29 (Prediction -> Outcome Tracking):** `PredictionRecord`
  gains `failureReason`, filled at `grade_predictions()`'s own
  resolution moment from the matching real `FailureClassification` (by
  `trade_id`) — never a second, independent guess. Required relocating
  `grade_predictions()`'s call site in `app/nexus.py` to run after the
  trade-close loop instead of before it, so a prediction resolved the
  same tick its trade closes still gets a real reason rather than a
  permanently-null one — a real ordering bug caught during
  implementation, not present in the original design, and now
  regression-covered by direct exercise of both call orderings.
- **Feature 27 (Agent Performance Reviews):** `recurring_mistakes`'s
  evidence string (never its underlying value) gains real classification
  specificity — the agent's own most common `FailureReason` among
  attributed, classified losing trades this period.

**Governance boundary**, identical to Feature 29's own precedent:
purely retrospective and promotion-only. Runs only after a trade has
already closed; touches none of `gatekeeper.py`, `risk_engine.py`,
Circuit Breakers, or the Model Validator. Nothing here can block or
alter a future trade.

**Frontend:** extends `DisciplinePanel.tsx`'s existing `DISCIPLINE`
tab with a new "Failure Review Board" card, placed after the existing
Discipline Chamber and Library of Mistakes & Successes cards — a real
reason-distribution filter row plus a per-trade list (symbol, reason
pill, real evidence, real P&L, expandable real attribution).

**Verified:** 20 new backend tests (`tests/test_failure_review.py`)
covering every precedence tier independently, the full precedence order
when a trade matches more than one real signal, real attribution, the
`"unknown"`-never-promoted gate, and the cap. Full backend suite,
`mypy`, `ruff` clean (6 pre-existing, unrelated `test_nexus.py`
failures confirmed via `git stash` against the committed baseline to
predate this feature). `tsc -b --noEmit`, `eslint`, `vite build` clean.
Live-verified against the running dev server: 6 real CEO-decided trades,
fast-forwarded to close, produced 13 real `FailureClassification`
records with real evidence text, real attribution, and real P&L — and
all four feed-back paths above were independently confirmed live
against that same real data (a real `"failure_classification"`
Institutional Memory entry; `GET /api/skill-profiles/atlas/latest`
returning a real, non-`null` `regime_detection` score; `GET /api/
predictions/atlas` returning real `failureReason` values on incorrect
predictions), and the new "Failure Review Board" card rendered
correctly in the DISCIPLINE tab (`frontend/tests/commandCenter.spec.ts`,
run against the live stack).

This closes the CEO's full "Features 26-30: Agent Intelligence,
Learning & Institutional Memory System" directive. All five stages —
26 (Institutional Memory 2.0), 27 (Agent Performance Reviews), 28
(Academy + Skill Progression), 29 (Prediction -> Outcome Tracking), 30
(Agent Debate + Failure Review Board) — are implemented, tested,
documented, and live-verified, with Feature 30's own real outputs
feeding back into the other four exactly as the directive's own
closed-loop framing asked for.
