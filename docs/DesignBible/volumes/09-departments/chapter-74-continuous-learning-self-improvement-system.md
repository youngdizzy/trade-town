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
