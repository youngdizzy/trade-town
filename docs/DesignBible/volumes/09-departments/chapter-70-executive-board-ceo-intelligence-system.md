# Chapter 70 — Executive Board & CEO Intelligence System

**Status:** Not implemented, filed here rather than in Volume 10. Two
parts: **Part 1** (below) is the base brief — board roster, meetings,
Decision Center, Company Health Review, Executive Command Center.
**Part 2** (further down) is the Executive Consensus Meter addendum —
per-recommendation department-by-department transparency into how the
board reached its call.
**A placement note:** this brief arrived numbered "Chapter 70," the
same number Volume 10 had briefly used for a since-folded-in chapter —
that number is free again, and this chapter's own subject (executive
governance, not broker/account infrastructure) belongs in Volume 9
alongside Chapters 63/64, not Volume 10. **Researched first, and the
finding here matches Chapters 65/66/67's own pattern exactly:**
substantial real machinery already exists for most of this brief,
under different names, built across nine earlier chapters/features —
this chapter's job is describing it honestly and identifying the
precise, narrower set of genuine gaps, not re-proposing a system that's
already mostly real. See the Implementation Notes at the bottom of each
part for the full inventory.

## Part 1 — Executive Board & CEO Intelligence System

### Executive Summary

The brief asks for one place where "everything important arrives" —
department reports, board debate, CEO decisions, company health, all in
one screen the CEO can read in a minute. **Researched first:** most of
the individual pieces already exist and already work: a real monthly
CIO review (`ExecutiveReview`), a real per-trade "meeting log" recording
what every department said and what the CEO decided
(`ExecutiveMeetingLogEntry`), a real merged priorities list
(`computeExecutivePriorities`), a real Company Health/Score breakdown
matching most of the brief's own Company Health Review categories, and
— as of Chapter 67 — a real Global Status Bar, Executive Alert Center,
and unified dashboard hook already surfacing most of what the brief
calls the Executive Command Center. What's genuinely missing is
narrower: a literal twelve-seat board roster with every named
Chief-Officer title, automatic emergency-meeting triggers, a CEO
Assistant AI, and one unified report object combining all nine of the
brief's own Board Report fields in one place.

### Company Philosophy

"Departments execute, employees specialize, the Executive Board
coordinates" is not a new principle to adopt — Chapter 66's own
Company Philosophy already established that survival-first discipline
flows top-down through real, working machinery (Sentinel, the Trade
Gatekeeper, AI Consensus Safety), and the Executive Intelligence
Network (`app/executive_intelligence.py`) already coordinates real
department opinions into one recommendation before any trade executes.
This chapter's job is naming that coordination layer explicitly and
extending it past trades into general company governance.

### Primary Responsibilities

**Would own:** the Board Members roster, Executive Board Meetings
(scheduled + emergency), the Board Report format, the CEO Decision
Center, Board Discussion/Voting, the Company Health Review, Executive
Priorities, the Strategic Roadmap, Board Memory, Executive Scorecards,
the CEO Assistant, and the Executive Command Center.

**Does NOT own** (matches this codebase's real division of labor):
Trade Decisions (the analyst desk — this chapter coordinates and
records them, never makes them), Risk Authority (Chapters 57/58/66's
real veto pipeline stays the only thing that can block a trade), Broker
Communication (Chapter 68), Account Management (Chapter 69's three
parts). This chapter is a coordination and reporting layer over real
systems that already exist, the same relationship Chapter 67's TTOS has
to the 34 real tabs it organizes.

### Ownership

Every brief concept checked against the real codebase before this
chapter was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Board Members" (12 named Chief-Officer seats) | 14 real agents, 4 with "Chief" titles | `AGENT_PROFILES` (frontend/src/game/systems/AgentProfiles.ts): Meridian is literally "Chief Investment Officer" (exact match). Keystone is "Chief Risk Architect," Compass is "Chief Learning Architect," Vector is "Chief Quantitative Strategist" — close to, but not exact matches for, the brief's CRO/Chief Knowledge Officer/CQO. The other 9 real agents (Scout, Atlas, Echo, Nova, Scribe, Coach, Sentinel, Pulse, Guardian, Sage) have real, distinct occupations but no "Chief" title. No Chief Research/Technology/Operations/Compliance/Innovation/Portfolio/Market Intelligence Officer exists by that exact name — five of the brief's twelve named seats have no real occupant. |
| "Executive Board Meetings" (Daily/Weekly/Monthly/Quarterly/Emergency) | `FounderCouncilSession` + `ExecutiveReview`, both real, both monthly | `FounderCouncilSession` (`app/founders.py`) — a real monthly Coach+Founders sit-down, generated alongside the existing `CoachReport`. `ExecutiveReview` (`app/executive_review.py`, "the CIO's Monthly Executive Review") — real, monthly, company-wide. `CoachReport` itself supports weekly *and* monthly cadence (`ReflectionCadence`). **Not real:** Daily or Quarterly cadence for any of these, and no Emergency meeting trigger of any kind. |
| "Board Report Format" (9 named fields) | `ExecutiveReview`'s real fields | Real matches: Department Health → `departmentActivity` + `companyHealthTier`; Completed Objectives → `researchCompleted`/`knowledgeGained`/`lessonsCompleted`; Problems → `flags`; Recommendations → `recommendations`; a narrative → `summary`. **Not real, as named fields:** Opportunities, Risk Assessment, Confidence Level, Required CEO Decisions, Expected Impact — none of these exist on `ExecutiveReview` or any other real report object today. |
| "CEO Decision Center" (Summary/Evidence/Benefits/Risks/Probability/Capital/Time Horizon/Departments/Confidence, Approve/Reject/Delay/Modify/Delegate) | `ExecutiveVoting.tsx` + `TradeDecision` | Real, but scoped only to trade proposals: Summary (symbol + reasoning), Supporting Evidence (agent votes), Probability (confidence score), Affected Departments (supporting/opposing agents) are all real. CEO options are real but narrower: BUY/SELL/WAIT map to Approve/Reject/Delay; **Modify and Delegate do not exist as CEO actions anywhere.** No general-purpose Decision Center exists for non-trade decisions — Strategy promotion, Innovation Lab budget, and every other CEO approval each has its own separate, ad hoc UI, never one unified center. |
| "Board Discussion System" (evidence-based debate, CEO sees both sides) | `generate_department_opinions()` (`app/executive_intelligence.py`) | Real and genuinely evidence-based: real department stances that can actively oppose each other, feeding `compute_executive_recommendation()`'s real `pause_trading` enforcement (Chapter 66). Scoped to trade proposals only — no general "Risk Officer disagrees with CIO on a non-trade matter" mechanism exists. |
| "Board Voting" (Unanimous/Majority/Split/Tie/CEO Override, recorded in Company Memory) | `AgentVote` on `TradeDecision.votes`, `ExecutiveMeetingLogEntry` | Real: every trade decision already carries individual agent votes, aggregated via `voteDirection()`; `ExecutiveMeetingLogEntry` (`app/schemas.py`) is a real, permanent record of what every department said, what the network recommended, and what the CEO actually decided, generated on every real `resolve_proposal()` call. **Not real:** "Tie" and "CEO Override" as distinctly labeled outcomes (the CEO's decision already always wins; there's no vote-tally state machine naming these cases), and none of this exists for non-trade board proposals. |
| "Company Health Review" (9 named categories) | `CompanyScore` + `CompanyHealth` | Strong real match: `companyScore`'s breakdown (Research/Decisions/Risk/Paper Trading Performance/Teamwork/Simulation, per `OverviewPanel.tsx`) and `CompanyHealth.overall`/`.tier` cover Financial/Portfolio/Risk/Research/Employee-Performance/Automation ground honestly. **Not real:** "Infrastructure" as a tracked dimension — no infrastructure concept exists anywhere in a paper-trading sim with no real broker or server-health signal to report on. |
| "Executive Priorities" (5 separate Top-5 lists) | `computeExecutivePriorities()` (`derive.ts`) | Real, but a different shape, and its own code comment already names this exact tension: it merges and dedupes `CompanyHealth.recommendations`, the latest `CoachReport.recommendations`, and the latest `ExecutiveReview.recommendations` into **one** ranked list, ordered by which real system raised the point first — never split into five separate Opportunities/Risks/Objectives/Bottlenecks/Actions categories, and never capped at exactly 5. |
| "Strategic Roadmap" | Chapter 64's real Goals/Milestones, Chapter 45's Research Sandbox `Strategy` stage history, Hall of Fame | Real, distributed: CEO-authored Goals with real tracked progress and 25/50/75% milestone checkpoints (Current/Long-Term Goals); `Strategy.stageHistory` (Upcoming Features/Research Projects, loosely); Hall of Fame (Completed Milestones, loosely). Never assembled into one named "Strategic Roadmap" view. |
| "Board Memory" | Company Memory (Chapter 61) | Real, permanent, and already the exact shape this brief asks for — decisions, reasoning, evidence, and outcomes are already recorded for every real event category this codebase produces, including trade decisions and Emergency Stop activations. |
| "Emergency Board Meeting" (auto-triggered on 7 named events) | *(does not exist)* | No automatic meeting-trigger mechanism exists for any of the seven named events. Two of the seven have no real underlying signal to trigger from at all: Broker Failure (no real broker exists, Chapter 68) and Black Swan Events (confirmed absent, Chapters 66/68). Emergency Stop Activation is real and does produce a sticky critical toast + permanent Company Memory record (Chapter 67) — the closest real analog, but it's a notification, not a meeting. |
| "Executive Scorecards" (8 named metrics per executive) | `CompanyScore` breakdown, `computeDepartmentHealth()` | Partial real coverage: `computeDepartmentHealth()` already computes real Efficiency/Workload/Morale/Productivity-shaped metrics per real subsystem, whichever of those dimensions that subsystem actually has a number for (its own docstring: never a uniform template forced onto systems that don't track all of them). **Not real:** a single scorecard object per named Chief Officer combining Accuracy/Decision Quality/Forecast Accuracy/Capital Efficiency/Risk Prevention/Innovation Success/Contribution Score — no such per-executive composite exists. |
| "CEO Assistant" (summarize meetings, prioritize tasks, prepare agendas) | *(does not exist)* | Sage is a real "Socratic Mentor" (Q&A, never tells the CEO what to think, per its own personality field) — the opposite job from an assistant that prioritizes and summarizes. No agent performs any of the six named Assistant responsibilities today. |
| "Executive Command Center" (10 named live metrics) | `GlobalStatusBar.tsx` + `useDashboardData()` + Executive Alert Center (all Chapter 67) | The strongest real match of any section in this brief: Company Health✓, Market Regime✓, Portfolio Health✓ (Portfolio Heat), Risk Status✓, Major Alerts✓ (the real Alert Center), Executive Recommendations✓ (`computeExecutivePriorities`), Pending CEO Decisions✓ (the real Pending Proposals queue, Chapter 59) are all real today, already live, already CEO-facing — just distributed across Chapter 67's Global Status Bar/Alert Center/Command Palette rather than one consolidated screen. Broker Health is real only as the honest static "SIMULATED" pill; Active Objectives (Chapter 64 Goals) and Capital Allocation (RiskPanel) exist but aren't surfaced on this particular strip today. |

### Inputs

**Real today:** every input this table confirms real above — trade
proposals, department opinions, `CompanyHealth`/`CompanyScore`,
Goals/Milestones, Company Memory. **Would need, once real:** a
non-trade-scoped decision object the CEO Decision Center could present
(does not exist), a Chief-Officer-to-agent mapping for the five unfilled
board seats (does not exist).

### Outputs

**Real today:** `ExecutiveReview`, `ExecutiveMeetingLogEntry`,
`computeExecutivePriorities()`'s merged list, `CompanyHealth`/
`CompanyScore`. **Would produce, once real:** a single Board Report
object combining all nine of the brief's own named fields, five
separate Top-5 priority lists instead of one merged list, and a
Strategic Roadmap view assembling the three real, currently-separate
sources named under Ownership.

### Internal Workflow

**The brief's own implied flow — department reports in, board discusses,
CEO decides, outcome recorded — already exists end to end for trade
proposals specifically:** `generate_department_opinions()` → 
`compute_executive_recommendation()` → CEO resolves via
`ExecutiveVoting.tsx` → `generate_meeting_log_entry()` records the
outcome permanently. A real Executive Board would generalize this exact
pipeline to non-trade decisions, not invent a second one.

### Decision Logic

**Real today, for every trade-scoped piece:** `compute_executive_
recommendation()`'s department-opinion aggregation is a transparent,
named formula, matching this codebase's "no black-box composite"
convention throughout. **Not real:** any formula for ranking or scoring
non-trade board proposals, or for computing the brief's own per-executive
Contribution Score — no composite scoring exists for either.

### Department Cooperation

**Would receive from:** Chapter 63 (Executive Performance & Company
Health — the real `CompanyHealth`/`CompanyScore` this chapter's own
Company Health Review reuses directly), Chapter 64 (Strategic Planning —
the real Goals/Milestones this chapter's Strategic Roadmap reuses),
Chapter 61 (Knowledge Graph/Company Memory — real, this chapter's own
Board Memory), Chapter 66 (the real department-opinion/disagreement
machinery this chapter's Board Discussion System already is, scoped to
trades), Chapter 67 (the real Global Status Bar/Alert Center this
chapter's Executive Command Center already substantially is). **Would
provide:** a unified Board Report, Executive Scorecards, and Strategic
Roadmap to every department that currently produces its own separate
report.

### CEO Controls

| Control | Status |
|---|---|
| Configure meeting cadence (Daily/Weekly/Monthly/Quarterly) | **Partially real** — `CoachReport` already supports weekly/monthly cadence; no CEO-facing toggle exists to choose it, and no daily/quarterly option exists anywhere. |
| Enable Board Voting | **Not built** as a togglable setting — voting is real but always-on for trade decisions specifically, not a feature the CEO can enable/disable. |
| Approve / Reject / Delay / Modify / Delegate a proposal | **3 of 5 real** (Approve/Reject/Delay, via BUY/SELL/WAIT on trade proposals) — Modify and Delegate don't exist as CEO actions anywhere, for any decision type. |
| Assign a Chief Officer title to an agent | **Not built** — the four real "Chief" titles are fixed in `AgentProfiles.ts`, not CEO-assignable. |

### Learning System

**Already real, for the trade-decision-scoped half of this chapter:**
`ExecutiveMeetingLogEntry` already records whether the network's
recommendation and the CEO's actual decision agreed — a real, permanent
input a future learning loop could analyze. **Not built:** any learning
loop over non-trade board decisions, since no non-trade decision object
exists yet to generate history from.

### KPIs

**Real and computable today, narrowly:** whatever `CompanyScore`'s
breakdown and `computeDepartmentHealth()` already track. **Not
honestly computable:** a per-executive Contribution Score, Forecast
Accuracy, or Risk Prevention metric — no composite scoring exists for
any named Chief Officer today, since five of the twelve named seats
have no real occupant to score in the first place.

### Reports

**Real today:** `ExecutiveReview` (the closest real analog to a Board
Report), `ExecutiveMeetingLogEntry` (the closest real analog to Board
Meeting minutes). **Not built:** a single report object combining all
nine of the brief's own named Board Report fields, or any of the eight
Executive Scorecards.

### Safety Systems

This chapter inherits, rather than duplicates, Chapter 66's real
safety machinery — the Board Discussion System's real disagreement
signal already enforces a trading pause (Chapter 66's `pause_trading`),
and nothing in this chapter should build a second, competing
enforcement path. Emergency Board Meetings, if ever built, should
trigger *from* Chapter 66/67's real signals (a critical `RiskWarning`,
Emergency Stop activation), never invent a parallel detection layer.

### Dependencies

Chapters 63 (Executive Performance & Company Health), 64 (Executive
Strategic Planning), 66 (Institutional Safety — the real disagreement/
pause machinery), 67 (TTOS — the real Global Status Bar/Alert Center/
Command Palette this chapter's Executive Command Center substantially
already is). All previous Design Bible chapters, matching this volume's
own established framing.

### Future Expansion

A literal twelve-seat board with every named Chief Officer filled by a
real, distinct agent; automatic Emergency Board Meeting triggers; a CEO
Assistant AI; and a general-purpose (non-trade-scoped) Decision Center
all require real design decisions (new agents? repurposed existing
ones? a new proposal type distinct from `TradeProposal`?) not made
unilaterally in this pass. Matches this volume's own Future Expansion
precedent — named honestly, not stubbed.

### Design Bible Integration

**Real today, and already wired without this chapter's own help:**
Company Memory, the Knowledge Graph, Company Health, Risk Authority,
and the Executive Dashboard (Chapter 67's `useDashboardData()`) all
already consume the real systems this chapter would coordinate — this
chapter's own value is organizing what already flows between them into
one board-shaped view, the same relationship Chapter 67's TTOS has to
the 34 tabs it groups, never a new parallel data layer.

### Company Principle

"TradeTown is not controlled by isolated AI agents; it is governed by
an Executive Board where specialized intelligence collaborates,
challenges assumptions, and provides the CEO with the highest-quality
decisions possible" is, narrowly, already true for every trade this
codebase executes — `generate_department_opinions()` and the Trade
Gatekeeper's eight checks already are real specialized intelligence
challenging a proposal before the CEO ever sees it. The CEO remaining
"the final authority" is also already real and enforced everywhere: no
CEO override is even mechanically possible to bypass in the Trade
Gatekeeper's checks (Chapter 66), and nothing in this chapter should
change that.

### Implementation Notes

**What's real today, found by direct research before this chapter was
written, not assumed — one of the highest real-coverage chapters
written this run, alongside Chapters 66/67:** a real monthly CIO review
(`ExecutiveReview`) with fields matching five of the brief's own nine
Board Report categories; a real, permanent per-decision meeting log
(`ExecutiveMeetingLogEntry`) recording department opinions, the
network's recommendation, and the CEO's actual choice; a real merged
executive-priorities list (`computeExecutivePriorities()`, whose own
code comment already named the "one list vs. five separate lists"
tension this brief raises again); a real Company Health/Score breakdown
covering six of the brief's own nine Company Health Review categories;
real Goals/Milestones (Chapter 64) and Hall of Fame as distributed
Strategic Roadmap material; a real, evidence-based department-
disagreement system already enforcing a trading pause (Chapter 66);
and — the single strongest match in this whole brief — Chapter 67's
Global Status Bar, Executive Alert Center, and `useDashboardData()`
hook already surfacing seven of the brief's own ten Executive Command
Center metrics live, today. Four of the brief's twelve named board
seats are filled by real agents with real, if not exactly matching,
"Chief" titles (CIO exact; Risk/Knowledge/Quantitative close);
eight others are not. **What's genuinely, entirely unbuilt:** the
remaining five named board seats, Daily/Quarterly meeting cadence,
automatic Emergency Board Meeting triggers (two of the seven named
triggers — Broker Failure, Black Swan — have no underlying signal to
trigger from at all, confirmed absent by Chapters 66/68), Modify/
Delegate as CEO decision actions, a general-purpose non-trade Decision
Center, per-executive Contribution/Forecast-Accuracy scorecards, and a
CEO Assistant AI (Sage's real Socratic-mentor role is deliberately the
opposite job). No code was written against this chapter.

## Part 2 — Executive Consensus Meter

### Executive Summary

The brief asks that "every significant recommendation presented to the
CEO" carry a consensus meter — who agrees, who disagrees, why, how
confident each executive is, and one overall institutional read, so the
CEO never has to take the system's word for it. **Researched first, and
the finding is unusually direct:** this already exists, close to
verbatim, for trade proposals specifically. `DepartmentOpinion` (`app/
schemas.py`) and `compute_executive_recommendation()` (`app/
executive_intelligence.py`) are the real Executive Consensus Meter —
nine real departments, each returning a real stance, a real confidence
percentage, and a real reason, combined by a transparent, named,
priority-ordered formula into one recommendation the CEO sees live in
`ExecutiveVoting.tsx`'s "Executive Intelligence Network" panel before
every trade decision. What's genuinely narrower than the brief: it's
trade-scoped only (Part 1's already-documented gap — no non-trade
Decision Center exists to attach a consensus meter to), several of the
brief's structured per-executive fields collapse into one free-text
summary in the real system, and nothing tracks whether any department's
opinion was actually *right* after the fact — a gap this section argues
is not an oversight so much as a direct consequence of a design
principle this codebase already holds elsewhere (see Board History &
Executive Accuracy below).

### Company Philosophy

"TradeTown should never behave like a black box" is not a new
commitment for this codebase — it's the same "no black-box composite"
convention already named in Part 1 and enforced everywhere a real
score exists (`CompanyHealth.overall`, `compute_executive_
recommendation()` itself). The Executive Consensus Meter's job is
narrower than inventing new transparency: it's naming and packaging the
transparency this codebase's real trade-decision pipeline already has,
and being honest about where that transparency currently stops (at the
trade-decision boundary).

### Primary Responsibilities

**Would own:** the Individual Executive Opinion format, the Consensus
Calculation, the Consensus Display panel, Disagreement Analysis, Board
History, and the Executive Accuracy Score.

**Does NOT own** (same real division of labor as Part 1): the
underlying department analysis itself (each department's real opinion
is computed by that department's own real system — research.py,
risk_engine.py, the What-If Simulation Lab, etc. — the Consensus Meter
only aggregates and displays what those systems already concluded, it
never recomputes their judgment); the CEO's actual decision (the
consensus meter informs, the Trade Gatekeeper still has final,
unbypassable veto authority per Chapter 66).

### Ownership

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Individual Executive Opinions" (Approve/Reject/Modify/Delay/Abstain + Confidence + Evidence + Concerns + Benefits + Risks + Alternatives) | `DepartmentOpinion` (`app/schemas.py`) | Real, close but narrower: `role`, `departmentLabel`, an optional `agentId` (only Risk, Simulation, Founders, and Devil's Advocate map to one specific named agent today — Research/Quant/Decision Intelligence/Coach/Market Intelligence speak as a department, not a named individual), a real `stance` (one of 6 real values: `agree`/`disagree`/`request_more_research`/`recommend_waiting`/`recommend_position_change`/`recommend_rejecting` — a reasonable but inexact map to the brief's Approve/Reject/Modify/Delay; there is no `abstain` value, because every real department always renders an opinion — abstention isn't a state the real system models), and a real `confidencePct`. **Not real:** Supporting Evidence, Primary Concerns, Expected Benefits, Potential Risks, and Alternative Recommendations as separate structured fields — the real object has exactly one free-text `summary` string carrying all of that at once (contrast with the separate, real `AnalystVote.evidence` list on the six-analyst pre-trade vote, a different, earlier stage in the same pipeline that *does* carry a structured evidence list). |
| "Consensus Calculation" (Overall Consensus %, Overall Confidence %, Institutional Risk Score, Institutional Opportunity Score, Probability of Success, Estimated Drawdown Risk, Expected Return) | `compute_executive_recommendation()` | Real, but only 2 of the brief's 7 numbers exist, and they're not quite the two the brief names: the function computes one real `confidencePct` (the plain average of every department's `confidencePct`) and a real `action` (the aggregate recommendation), via a transparent, priority-ordered, fully-named rule chain — never a black-box weighted blend. **Not real:** a distinct "Overall Consensus %" number separate from confidence (the brief's own example shows these as two different figures, 91% vs 93%; the real system only produces one). No Institutional Risk Score or Institutional Opportunity Score exists by that name anywhere. Probability of Success, Estimated Drawdown Risk, and Expected Return *do* exist as real numbers (`WhatIfSimulation.baseline.probabilityOfProfitPct`, `.typicalDrawdownPct`, `.mostLikelyPct`) — but they're computed by a genuinely separate real system (the What-If Simulation Lab, Feature 16, a bootstrap price-scenario engine) that the Consensus Meter never reads from. `ExecutiveVoting.tsx` renders them as two separate collapsible panels in the same modal today ("OPEN WHAT-IF SIMULATION LAB" and "OPEN EXECUTIVE INTELLIGENCE NETWORK") — real proof both exist, and real proof they've never been merged into the one 7-number summary strip the brief's mockup shows. |
| "Consensus Display" (headline card: Overall Recommendation / Consensus % / Confidence % / Probability / Return / Risk, then one card per named Chief Officer) | `ExecutiveIntelligencePanel` (`ExecutiveVoting.tsx`) | Real and close in spirit, narrower in exact shape: a real headline row (action pill + `confidencePct`), a real reason sentence, a real supporting/opposing department list, then one real card per department (label, agent name if one exists, stance pill, summary, confidence %) — everything the brief's mockup shows except the brief's own extra Consensus %/Probability/Return/Risk row (see Consensus Calculation above) and the brief's 6 named "Chief Officer" seats specifically. The real 9 departments are research/quant/risk/simulation/decision_intelligence/coach/founders/devils_advocate/market_intelligence — only 3 recognizably match the brief's 6 example seats (research↔Chief Research Officer, quant↔Chief Quantitative Officer, risk↔Chief Risk Officer); there is no Chief Compliance Officer or Chief Innovation Officer department opinion (the closest real analog to "Compliance" is the Trade Gatekeeper, Chapter 58 — a completely separate real pass/fail system, not one of the 9 department opinions). One real information-hierarchy difference worth naming: the brief presents this as the headline of the trade proposal; the real panel is one of several collapsible sections inside the Executive Voting modal, opened on request, not shown by default. |
| "CEO Decision Support" (Approve/Reject/Modify/Request More Research/Delay Decision/Delegate, permanently recorded) | `ExecutiveVoting.tsx`'s BUY/SELL/WAIT + `hold()` | 4 of 6 real, exactly matching Part 1's own already-documented finding — nothing new here: BUY/SELL/WAIT map to Approve/Reject/Delay, and the real `hold("more_research")`/`hold("delay")` actions (capped at `MAX_PROPOSAL_HOLDS`, 2) are genuinely real matches for Request More Research and Delay Decision specifically. Modify and Delegate remain entirely unbuilt as CEO actions, for any decision type. Every decision *is* permanently recorded — `ExecutiveMeetingLogEntry`, real. |
| "Disagreement Analysis" (TradeTown automatically explains why executives disagree) | The real per-department summary cards + `ExecutiveRecommendation.reason` | Partially real: the CEO can already see every department's own stance and summary side by side in the real panel (functionally "Risk says X, Research says Y" is already readable, one card at a time), and `reason` is a real, rule-based sentence naming the specific trigger behind the aggregate call (e.g. "{N} departments actively disagree — the company shouldn't force this one"). **Not real:** an auto-synthesized multi-department disagreement paragraph structurally separate from the per-department cards — today the CEO assembles the "who disagrees and why" picture by reading the cards themselves; the system doesn't write that comparison out in prose. |
| "Board History" (Consensus %, Final CEO Decision, Actual Outcome, Prediction/Department/Confidence Accuracy, tracked per decision) | `ExecutiveMeetingLogEntry` | Real and more complete than it first appears: every entry permanently stores the full `opinions` list (so the whole per-department stance/confidence/summary breakdown for that exact decision is recoverable, not just a rolled-up scalar), plus `recommendedAction`, `recommendationReason`, the real `ceoDecision`, and whether the network and CEO `networkAgreed`. **Not real:** a precomputed "Consensus %" scalar stored on the entry itself (recoverable by recomputing from the stored `opinions`, but not stored directly), and — the more significant gap — no "Actual Outcome" field anywhere. `decisionGrade`/`decisionGradeScore` (also on this entry) is explicitly a *process*-quality grade, never the trade's real P&L, matching `app/discipline.py`'s Discipline Score convention exactly. No field anywhere ties a `DepartmentOpinion`'s stance back to what actually happened to the symbol afterward. |
| "Executive Accuracy Score" (Prediction Accuracy, Risk Prevention Accuracy, Profit Contribution, Forecast Reliability, Decision Quality, Consistency; executives gain/lose influence over time) | `DepartmentSelfEvaluation` (partial precedent) | One real, partial precedent: a real weekly per-department self-evaluation (`generate_weekly_self_evaluations()`) with a real `score`, real `strengths`, and real `improvementAreas` — but `score` is grep-confirmed to be the plain average of that department's own `confidencePct` values over the week, not accuracy against any real outcome. **Entirely unbuilt:** every one of the brief's 6 named accuracy metrics, and the "executives gain/lose influence" mechanism itself — grep-confirmed zero `influence`-weighting code exists anywhere in `backend/app`. This isn't a simple oversight to fill in later: building real outcome-linked accuracy for the 5 of 9 departments that don't cast a direct buy/sell signal (Coach, Founders, Devil's Advocate, Decision Intelligence, Market Intelligence) would require judging what a *hypothetical* trade "would have" done — exactly the kind of counterfactual this codebase's own `app/coach.py` and `app/player_vs_ai.py` explicitly and deliberately decline to fabricate today ("we truly don't know what would have [happened]"). Any real Executive Accuracy Score has to resolve that tension honestly, not route around it. |

### Inputs

**Real today:** every real `TradeProposal`, `ChallengeReport`, `CoachReport`, and `MarketIntelligenceState` that already feeds `generate_department_opinions()`. **Would need, once real:** a non-trade-scoped decision object for the Consensus Meter to attach to outside trading (the same gap Part 1 already names for the CEO Decision Center), and a real trade-outcome signal if Board History's "Actual Outcome"/accuracy fields are ever built honestly.

### Outputs

**Real today:** `ExecutiveRecommendation` (the live, ephemeral, per-open Consensus Meter reading) and `ExecutiveMeetingLogEntry` (its permanent record). **Would produce, once real:** a stored per-decision consensus scalar, a synthesized disagreement paragraph, and a real Executive Accuracy Score per department.

### Internal Workflow

Identical real pipeline to the one Part 1 already documented, because it's the same one system: `generate_department_opinions()` → `compute_executive_recommendation()` → the CEO reviews `ExecutiveIntelligencePanel` inside `ExecutiveVoting.tsx` → `generate_meeting_log_entry()` records the outcome permanently on `resolve_proposal()`. The Executive Consensus Meter isn't a new pipeline layered on top of Part 1's Board Discussion System — it's the existing pipeline's own live-rendered output, named and inspected on its own terms.

### Decision Logic

Real and already transparent: `compute_executive_recommendation()`'s priority-ordered rule chain (checked in `executive_intelligence.py`, in order — Market Intelligence's `avoid_trading` read outranks everything, then Risk/Devil's Advocate position-change concerns, then Simulation's missing stress test, then a 2+-department disagreement count, then Research's own low-confidence flag, then a 3+-department "wait" majority, defaulting to `trade_normally`) is exactly the kind of named, inspectable formula the brief's own Design Principle asks for. Nothing about the Consensus Meter's real math is hidden from a reader of the code — it just isn't currently surfaced to the CEO as an explicit "here is the exact rule that fired" explanation, only as the resulting `reason` sentence.

### Department Cooperation

Reuses Part 1's Department Cooperation relationships exactly — this section is that same real Executive Intelligence Network, viewed through its own consensus-transparency lens rather than as a new coordination layer.

### CEO Controls

| Control | Status |
|---|---|
| Require a Consensus Meter before every significant CEO decision | **Not built** as a toggle — the real panel exists but is trade-scoped and opened on request (`OPEN EXECUTIVE INTELLIGENCE NETWORK ▼`), never mandatory or shown by default. |
| Set a minimum consensus threshold before auto-flagging a decision | **Not built** — no consensus-specific threshold exists; the closest real analog (`DecisionConfidence`'s general confidence threshold) is a different real system scoped to the pre-trade analyst vote, not this consensus layer. |
| Adjust department influence/weighting | **Not built** — matches the Ownership table's finding exactly: no influence-weighting mechanism exists to adjust. |

### Learning System

**Already real, narrowly:** `DepartmentSelfEvaluation`'s weekly average-confidence self-report is a real, if honestly limited, precedent — it improves nothing automatically today (no influence adjustment reads it), but it is a real historical record a future learning loop could start from. **Not built:** any loop that ties a department's past stance to a real subsequent outcome, for the reason named above (this codebase's own explicit stance against fabricating counterfactual "would have" outcomes).

### KPIs

**Real and computable today:** `compute_executive_recommendation()`'s `confidencePct`, and `company_health.py`'s real, separate `department_consensus` metric — a genuinely different number worth distinguishing clearly: it's a *rolling, company-wide* percentage of "agree" stances across the trailing window of real meeting-log entries (`_department_consensus()`), not a per-decision consensus figure. It already answers a real, useful, differently-scoped question ("how often do departments agree with each other lately, company-wide") — not the brief's per-recommendation number, but a real precedent worth citing rather than ignoring. **Not honestly computable:** any of the brief's named accuracy KPIs, for the same reason as above.

### Reports

**Real today:** the live `ExecutiveRecommendation` reading and its permanent `ExecutiveMeetingLogEntry` record, exactly as Part 1 already documents for the Board Meeting Log. **Not built:** a standalone Board History report view surfacing this history back to the CEO outside the per-proposal panel (today it's queryable data, not a presented report).

### Safety Systems

Inherits Chapter 66's real machinery without duplicating it: the same `pause_trading` enforcement Part 1 already cites is driven by this exact Consensus Meter's own real disagreement count (2+ departments opposing). Nothing in this section should build a second, competing safety signal — the Consensus Meter's honest job is explaining a decision that's *already* real and enforced, never gating one on its own.

### Dependencies

Chapter 66 (the real disagreement/pause machinery this section's numbers already drive), Chapter 58 (the Trade Gatekeeper — the real "Compliance"-shaped check this section's 9 departments don't include), Part 1 of this chapter (the general Board/Decision Center gap this section's trade-scoping inherits directly).

### Future Expansion

A distinct Overall Consensus % formula (separate from the current average-confidence number), a real Institutional Risk/Opportunity Score, merging the What-If Simulation Lab's real Probability/Return/Risk numbers into the same panel, a synthesized disagreement paragraph, and any real outcome-linked Executive Accuracy Score all require real design decisions — most pointedly, how (or whether) to resolve the counterfactual-outcome tension named in the Ownership table — not made unilaterally in this pass.

### Design Bible Integration

Already wired without this section's own help: `CompanyHealth`'s real `department_consensus` KPI, Chapter 66's real `pause_trading` enforcement, and Chapter 61's Company Memory (via the permanent meeting log) all already consume this exact real machinery — this section's value is naming and explaining it as a first-class "Executive Consensus Meter," not building a new data layer.

### Company Principle

"TradeTown should never simply say 'trust me'" is, narrowly, already true and enforced for every real trade decision this codebase makes — the CEO can already open the Executive Intelligence Network panel on any pending proposal and see exactly which departments agree, which disagree, how confident each one is, and the specific rule that produced the aggregate call. What isn't yet true company-wide: that same standard applied to every *other* significant CEO decision, and a real accounting of whether any of it was actually right.

### Part 2 Implementation Notes

**What's real today, found by direct research before this section was
written:** a real, live, per-trade-proposal Executive Consensus Meter —
`DepartmentOpinion` (9 real departments, each with a real stance,
confidence percentage, and free-text reasoning) aggregated by
`compute_executive_recommendation()`'s real, named, priority-ordered
formula into one recommendation, rendered today in `ExecutiveVoting.
tsx`'s Executive Intelligence Network panel and permanently recorded on
every real trade decision via `ExecutiveMeetingLogEntry` (which stores
the full opinion breakdown, not just a summary). A real, separate,
company-wide `department_consensus` KPI already tracks agreement rate
over time. **What's genuinely unbuilt:** a distinct Consensus %
separate from average confidence; Institutional Risk/Opportunity
Scores; merging the What-If Simulation Lab's real Probability/Return/
Risk numbers into this same panel; structured per-opinion Evidence/
Concerns/Benefits/Risks/Alternatives fields (today one free-text
summary carries all of it); an auto-synthesized disagreement paragraph;
Modify/Delegate as CEO actions; and any real Executive Accuracy Score —
the last of which runs into a genuine, pre-existing design tension with
this codebase's own explicit refusal to fabricate counterfactual trade
outcomes, not just a missing feature. No code was written against this
section.
