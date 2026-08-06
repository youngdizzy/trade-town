# Chapter 70 — Executive Board & CEO Intelligence System

**Status:** Three parts. **Part 1** (below) — board roster, meetings,
Decision Center, Company Health Review, Executive Command Center — is
not implemented. **Part 2** (the Executive Consensus Meter addendum) is
real: Modify joins Approve/Reject/Delay/Delegate as a genuine CEO
decision action, and a real Executive Accuracy Score scores each
department's directional stance against actual closed-trade P&L. **Part
3** (further down, the Weighted Executive Decision Engine) is now real
too: a published, per-department weighting layer over the existing
Consensus Meter, honestly scoped to the only two of the brief's eight
named inputs with a real, computable source — Historical Accuracy and
Market Conditions. See each part's own Implementation Notes (Part 2) or
Part 3 Implementation Notes for the exact honest inventory of what's
built and what remains out of scope.
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
| "CEO Decision Support" (Approve/Reject/Modify/Request More Research/Delay Decision/Delegate, permanently recorded) | `ExecutiveVoting.tsx`'s BUY/SELL/WAIT + `hold()` + `modify_proposal()` + `submit_ceo_decision(delegated=True)` | **Now 6 of 6 real.** BUY/SELL/WAIT map to Approve/Reject/Delay; `hold("more_research")`/`hold("delay")` (capped at `MAX_PROPOSAL_HOLDS`, 2) cover Request More Research and Delay Decision. Modify is now a real CEO action — `app/executive.py`'s `modify_proposal()` lets the CEO change position size/entry conditions on a pending proposal before resolving it, recorded via `scribe.py`'s `record_proposal_modify()`. Delegate is now real too — `submit_ceo_decision(..., delegated=True)` resolves the proposal using the network's own recommended action while flagging it as CEO-delegated rather than CEO-chosen, distinctly recorded on `CeoDecisionRecord.resolvedBy` and `ExecutiveMeetingLogEntry.resolvedBy`. Every decision *is* permanently recorded — `ExecutiveMeetingLogEntry`, real. |
| "Disagreement Analysis" (TradeTown automatically explains why executives disagree) | The real per-department summary cards + `ExecutiveRecommendation.reason` | Partially real: the CEO can already see every department's own stance and summary side by side in the real panel (functionally "Risk says X, Research says Y" is already readable, one card at a time), and `reason` is a real, rule-based sentence naming the specific trigger behind the aggregate call (e.g. "{N} departments actively disagree — the company shouldn't force this one"). **Not real:** an auto-synthesized multi-department disagreement paragraph structurally separate from the per-department cards — today the CEO assembles the "who disagrees and why" picture by reading the cards themselves; the system doesn't write that comparison out in prose. |
| "Board History" (Consensus %, Final CEO Decision, Actual Outcome, Prediction/Department/Confidence Accuracy, tracked per decision) | `ExecutiveMeetingLogEntry` | Real and more complete than it first appears: every entry permanently stores the full `opinions` list (so the whole per-department stance/confidence/summary breakdown for that exact decision is recoverable, not just a rolled-up scalar), plus `recommendedAction`, `recommendationReason`, the real `ceoDecision`, and whether the network and CEO `networkAgreed`. **Not real:** a precomputed "Consensus %" scalar stored on the entry itself (recoverable by recomputing from the stored `opinions`, but not stored directly), and — the more significant gap — no "Actual Outcome" field anywhere. `decisionGrade`/`decisionGradeScore` (also on this entry) is explicitly a *process*-quality grade, never the trade's real P&L, matching `app/discipline.py`'s Discipline Score convention exactly. No field anywhere ties a `DepartmentOpinion`'s stance back to what actually happened to the symbol afterward. |
| "Executive Accuracy Score" (Prediction Accuracy, Risk Prevention Accuracy, Profit Contribution, Forecast Reliability, Decision Quality, Consistency; executives gain/lose influence over time) | `compute_executive_accuracy_scores()` (`app/executive_intelligence.py`) + `DepartmentSelfEvaluation` (prior partial precedent) | **Now real, one honest metric of the brief's six — not all six, and deliberately so.** `compute_executive_accuracy_scores()` scores each department only on real, already-closed trades (`CeoDecisionRecord.outcome` of `"correct"`/`"incorrect"`, never a hypothetical): a department's stance counts as a directional prediction only when it's unambiguous (`agree`→predicts profitable, `disagree`/`recommend_rejecting`→predicts unprofitable); hedged stances (`recommend_waiting`, `request_more_research`, `recommend_position_change`) are excluded from the score entirely rather than counted either way, since they never took a clear position on the trade's own success. This resolves the exact counterfactual tension this section originally raised — by scope, not by fabrication: still **not built** are the other five named metrics (Risk Prevention Accuracy, Profit Contribution, Forecast Reliability, Decision Quality, Consistency) and the "executives gain/lose influence" mechanism — no `influence`-weighting code exists anywhere in `backend/app`, and this pass deliberately did not add any, since weighting a department's future opinions by a binary score computed only on the subset of trades it happened to be directional about would itself be a hidden composite, against this codebase's own convention. `DepartmentSelfEvaluation`'s weekly average-confidence self-report remains real and unchanged, still not accuracy against any real outcome. |

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

**Real, and now genuinely closes one loop:** `compute_executive_accuracy_scores()` ties each department's past directional stance to the real, closed-trade outcome recorded on `CeoDecisionRecord.outcome` — the exact kind of past-stance-to-real-outcome loop this section previously described as unbuilt. `DepartmentSelfEvaluation`'s weekly average-confidence self-report remains a separate, real, if honestly limited, precedent — it still improves nothing automatically (no influence adjustment reads it). **Still not built:** any loop that adjusts a department's future influence from either signal — see the Ownership table's reasoning for why that was deliberately not added this pass.

### KPIs

**Real and computable today:** `compute_executive_recommendation()`'s `confidencePct`; `company_health.py`'s real, separate `department_consensus` metric — a genuinely different number worth distinguishing clearly: it's a *rolling, company-wide* percentage of "agree" stances across the trailing window of real meeting-log entries (`_department_consensus()`), not a per-decision consensus figure; and now `compute_executive_accuracy_scores()`'s per-department `accuracyPct` (`GET /api/executive/accuracy`) — scored only against real, closed-trade outcomes, `0.0` with `decisionsTracked: 0` when a department hasn't yet cast enough directional stances to score. **Not honestly computable:** the other five named accuracy metrics (Risk Prevention Accuracy, Profit Contribution, Forecast Reliability, Decision Quality, Consistency) — same reasoning as the Ownership table above.

### Reports

**Real today:** the live `ExecutiveRecommendation` reading and its permanent `ExecutiveMeetingLogEntry` record, exactly as Part 1 already documents for the Board Meeting Log. **Not built:** a standalone Board History report view surfacing this history back to the CEO outside the per-proposal panel (today it's queryable data, not a presented report).

### Safety Systems

Inherits Chapter 66's real machinery without duplicating it: the same `pause_trading` enforcement Part 1 already cites is driven by this exact Consensus Meter's own real disagreement count (2+ departments opposing). Nothing in this section should build a second, competing safety signal — the Consensus Meter's honest job is explaining a decision that's *already* real and enforced, never gating one on its own.

### Dependencies

Chapter 66 (the real disagreement/pause machinery this section's numbers already drive), Chapter 58 (the Trade Gatekeeper — the real "Compliance"-shaped check this section's 9 departments don't include), Part 1 of this chapter (the general Board/Decision Center gap this section's trade-scoping inherits directly).

### Future Expansion

A distinct Overall Consensus % formula (separate from the current average-confidence number), a real Institutional Risk/Opportunity Score, merging the What-If Simulation Lab's real Probability/Return/Risk numbers into the same panel, and a synthesized disagreement paragraph still require real design decisions not made in this pass. The Executive Accuracy Score itself is now real (see Ownership and Implementation Notes) but deliberately narrow — extending it to the five departments that never cast a directional stance (Coach, Founders, Devil's Advocate, Decision Intelligence, Market Intelligence), or wiring any accuracy signal into a real influence-weighting mechanism, both remain open design decisions, not made unilaterally here.

### Design Bible Integration

Already wired without this section's own help: `CompanyHealth`'s real `department_consensus` KPI, Chapter 66's real `pause_trading` enforcement, and Chapter 61's Company Memory (via the permanent meeting log) all already consume this exact real machinery — this section's value is naming and explaining it as a first-class "Executive Consensus Meter," not building a new data layer.

### Company Principle

"TradeTown should never simply say 'trust me'" is, narrowly, already true and enforced for every real trade decision this codebase makes — the CEO can already open the Executive Intelligence Network panel on any pending proposal and see exactly which departments agree, which disagree, how confident each one is, and the specific rule that produced the aggregate call. What isn't yet true company-wide: that same standard applied to every *other* significant CEO decision, and a real accounting of whether any of it was actually right.

### Part 2 Implementation Notes

**Pre-existing, found by direct research before this section was
written:** a real, live, per-trade-proposal Executive Consensus Meter —
`DepartmentOpinion` (9 real departments, each with a real stance,
confidence percentage, and free-text reasoning) aggregated by
`compute_executive_recommendation()`'s real, named, priority-ordered
formula into one recommendation, rendered in `ExecutiveVoting.tsx`'s
Executive Intelligence Network panel and permanently recorded on every
real trade decision via `ExecutiveMeetingLogEntry`. A real, separate,
company-wide `department_consensus` KPI already tracked agreement rate
over time.

**Built this pass:**
- **Modify** (`app/executive.py::modify_proposal()`, `POST /api/executive/modify`) — the CEO can adjust a pending proposal's position size or entry conditions before resolving it; recorded via `scribe.py::record_proposal_modify()`.
- **Delegate** (`app/state.py::submit_ceo_decision(..., delegated=True)`, `POST /api/executive/decide` with `delegated: true`) — resolves the proposal using the network's own recommended action while distinctly flagging it as CEO-delegated rather than CEO-chosen, on both `CeoDecisionRecord.resolvedBy` and `ExecutiveMeetingLogEntry.resolvedBy` (`"ceo" | "auto" | "delegated"`).
- **Disagreement Analysis** — `_build_disagreement_summary()` (`app/executive_intelligence.py`) synthesizes the per-department stance/confidence breakdown that previously required reading each card individually into one structured summary, using `EXECUTIVE_STANCE_PHRASING` for consistent, named phrasing per stance (never a hidden weighted blend of the underlying opinions — a direct restatement of what each department already said).
- **Executive Accuracy Score** (`compute_executive_accuracy_scores()`, `GET /api/executive/accuracy`) — scores each department's directional stance (`agree`/`disagree`/`recommend_rejecting` only — hedged stances excluded) against real, already-closed `CeoDecisionRecord.outcome` values. This resolves the counterfactual-outcome tension by scope, not by inventing hypothetical outcomes: a department earns no score on trades it never took a clear directional position on, and 5 of 9 departments (Coach, Founders, Devil's Advocate, Decision Intelligence, Market Intelligence) will show `decisionsTracked: 0` until/unless they're given a directional stance to score, which this pass did not add.
- The What-If Simulation Lab's real Probability/Return/Risk numbers (previously two separate collapsible panels) are now merged into `GET /api/executive/intelligence`'s single response, so the frontend renders them together without a second fetch.

**What's genuinely still unbuilt:** a distinct Consensus % separate
from average confidence; Institutional Risk/Opportunity Scores;
structured per-opinion Evidence/Concerns/Benefits/Risks/Alternatives
fields (still one free-text summary); any influence-weighting mechanism
reading the new Executive Accuracy Score (deliberately not added — see
Ownership); and accuracy scoring for the 5 non-directional departments
named above. Verified: mypy/ruff clean, `tsc --noEmit`/eslint/`npm run
build` clean, and runtime-tested against the real `GameState` singleton
including the Modify/Delegate/accuracy code paths end to end.

## Part 3 — Weighted Executive Decision Engine (WEDE)

**Researched first, before any of the sections below were written:**
this brief's own central claim — that every department's opinion
should carry a numeric, dynamically-adjusted influence, rather than
counting equally — has **zero real precedent anywhere in this
codebase.** Grep-confirmed: no `influence` or per-department `weight`
concept exists in `backend/app` (the one `influence` hit is prose in
`app/constitution.py`, unrelated; every `weight` hit is a different
system — position sizing, `rule_engine.py`, `confidence.py`'s
single-proposal factor blend — never a cross-department multiplier).
What *does* exist, and is worth naming honestly up front, is a related
but different thing: `compute_executive_recommendation()`'s real
priority-ordered rule chain already lets some departments' stances
outrank others structurally (Market Intelligence's veto-like top slot,
Devil's Advocate/Risk's second slot) — a real precedent for "some
departments matter more in some situations," but expressed as a fixed
if/elif ladder in code, not a numeric weight a CEO could see, adjust,
or switch between named profiles for. This part's job is describing
that gap precisely, not overstating how close today's system already
is.

### Executive Summary

The brief asks that department opinions stop counting equally and
instead carry a Dynamic Influence Score shaped by accuracy, market
conditions, expertise, and rule compliance — visible to the CEO as both
a Raw Vote and a Weighted Recommendation, switchable between named
Weight Profiles. **Researched first:** three of this brief's real
building blocks already exist, built for other purposes: a real,
9-department `DepartmentOpinion` system with real confidence
percentages (Part 2's Executive Consensus Meter); a real, closed-trade-
only per-department accuracy score (`compute_executive_accuracy_scores()`,
built for Part 2 this same run); and two real, separate market-regime
classifiers (Chapter 65) whose own `RegimeReconciliation.posture`
output is explicitly documented as read-only and "never applied to any
[...] field automatically." None of the three is wired to change any
department's say in a decision today. The weighting engine itself, the
market-adaptation rules, the performance-evolution loop, the CEO weight
controls, and every named Weight Profile are all genuinely, entirely
unbuilt.

### Company Philosophy

"Executives prove their expertise through results" would be a new
commitment for this codebase to make, not a restatement of an existing
one — unlike most of this Design Bible's recent chapters, this
philosophy has no real analog to point to today. The closest adjacent
precedent is `DepartmentSelfEvaluation`'s weekly self-report (a
department scoring its own average confidence) and, now,
`compute_executive_accuracy_scores()` (a department scored against real
outcomes) — both real, permanent records a future evolution loop could
read from, but neither one currently changes anything about how much
that department's opinion counts next time.

### Primary Responsibilities

**Would own:** the per-department Dynamic Influence Score, Weighted
Executive Recommendation (alongside the existing Raw Vote), Dynamic
Market Adaptation, Performance-Based Evolution, the Weight Profile
system, and full weighting transparency.

**Does NOT own** (matches this codebase's real division of labor,
restated from Parts 1/2): the underlying department analysis itself
(each department's real opinion is still computed by its own real
system — this engine would only re-weight, never recompute, an
existing `DepartmentOpinion`); the CEO's actual decision (weighting
would advise, never replace, the CEO — the Trade Gatekeeper's real,
unconditional veto pipeline, Chapter 66, stays the only thing that can
block a trade); and — a new, explicit boundary this part must hold —
**Compliance and Innovation as departments with a vote to weight.**
Neither exists as one of the 9 real `DepartmentOpinion` roles today
(see Ownership); this part must not silently invent two new department
opinions just to give the brief's named seats something to weight, since
that would be new decision-logic scope, not a weighting-engine scope.

### Ownership

Every brief concept checked against the real codebase before this part
was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Dynamic Influence Score" (per-executive weight) | **Now real** — `DepartmentInfluence` + `compute_department_influence()` (`app/weighted_decisions.py`) | A real, per-department, per-decision weight — the product of small, named, published multipliers (accuracy × market × preset/custom), never a hidden blend. Honestly narrower than the brief's own eight-factor vision: only Historical Accuracy and Market Conditions feed the default formula; the other six factors have no real source and are not fabricated. |
| "Raw Executive Votes vs. Weighted Executive Recommendation" | **Now both real, side by side** | The pre-existing 9 real `DepartmentOpinion` objects remain the Raw Vote, unchanged. `WeightedExecutiveRecommendation` (`GET /api/executive/weighted-decision`) is now a real, separate computation — `rawAction` and `weightedAction` are both present on the same object so the CEO always sees both, exactly as the brief asks. |
| Named executive seats (CIO/CRO/CQO/Research/Compliance/Innovation) with context-specific higher influence | Still 4 of 6 seats real; still no Compliance/Innovation seat — **deliberately not invented** | Unchanged from Part 2's own finding: Meridian, Keystone, Vector, and the real `research` role cover four of six. **This pass explicitly did not invent Chief Compliance/Chief Innovation department opinions** — see Primary Responsibilities above: doing so would be new decision-logic scope (a new vote), not a weighting-engine scope (re-weighting existing votes), and risked quietly diluting the Trade Gatekeeper's real veto into "one more weighted opinion." |
| "Compliance has veto authority" | **Confirmed untouched and still absolute** | `app/gatekeeper.py`'s real, unconditional veto pipeline is not read, called, or modified anywhere in `app/weighted_decisions.py` — grep-confirmed. WEDE is purely advisory (stated in its own module docstring) and never gates a trade; Compliance's real veto authority remains exactly as strong as before this pass, never diluted into a weighted vote. |
| "Dynamic Market Adaptation" (Bull/Bear/High-Vol/Low-Vol boosts named departments) | **Now real** — `MARKET_CONDITION_BOOSTS` (`app/weighted_decisions.py`) | A real, published table mapping each of Chapter 65's 5 real `MarketEnvironmentRegime` values to per-department multipliers (e.g. bear → Risk 1.4×, Devil's Advocate 1.3×; bull → Research 1.3×, Market Intelligence 1.2×) — read live from `state.market_environment.current` on every request, applied automatically under the default Balanced Institutional profile. `RegimeReconciliation.posture` itself remains untouched and still read-only, per its own module docstring — this pass reads the underlying regime classifier directly, not that posture field. |
| "Performance-Based Evolution" (gain/lose influence over time via 7 named metrics) | Still 1 of 7 metrics real; **deliberately not wired into any persisted evolution** | `compute_executive_accuracy_scores()` is now read directly by `compute_department_influence()` under Performance Weighted and Balanced Institutional profiles — a real, live input, computed fresh every request (`compute_accuracy_multiplier()`), never a stored, decaying, or accumulating "influence" value. This is a deliberate scope decision: this codebase's own "no fake progression" rule (CLAUDE.md) rules out inventing a persisted gain/lose-influence-over-time mechanic without a resolved design for what "losing influence" durably means; a department with `decisionsTracked: 0` gets the neutral 1.0×, never penalized for a track record that doesn't exist yet. |
| "Transparency" (Raw Vote, Weighted Vote, Influence Score, Reasoning, Confidence, Supporting Evidence) | **Now 5 of 6 real** | Raw Vote, Weighted Vote, Influence Score (`finalWeight`), and Reasoning (a real, generated per-department string spelling out every multiplier that produced the weight) are all real and rendered together in `ExecutiveVoting.tsx`'s new panel. Confidence remains real, unchanged. **Still not real:** Supporting Evidence as a separate structured field (same Part 2 finding — collapses into `summary`). |
| "CEO Authority" (Ignore weighting / Equalize / Prioritize / Override / Lock custom weights / Create custom profiles) | **Now 5 of 6 real** | Equalize (the real `equal_voting` profile), Prioritize specific executives (the four "First" presets, or Custom), and Create custom weighting profiles (the real `custom` profile with a per-department editor in `ExecutiveVoting.tsx`) are all real. Override remains real and unchanged (pre-existing, unrelated to weighting). **Not built:** "Lock" as a distinct locking mechanism separate from simply leaving a profile set — there's no lock/unlock state, just whichever profile is currently active. |
| "Weight Profiles" (Equal Voting / Performance Weighted / Risk First / Growth First / Research First / Capital Preservation / Balanced Institutional / Custom CEO Profile) | **Now real — all 8, by name** | `WeightProfile` (`app/schemas.py`) is a real 8-value enum matching the brief's own list exactly; `WEIGHT_PROFILE_STATIC_PRESETS` publishes the four "emphasis" profiles' exact multipliers, `equal_voting`/`performance_weighted`/`balanced_institutional`/`custom` each have their own named formula in `compute_department_influence()`. Persisted via `SettingsState.activeWeightProfile`/`customDepartmentWeights` — the same client-authoritative mechanism `operatingMode` already uses, not a new persistence endpoint. The CEO can preview any profile instantly (`GET .../weighted-decision?profile=...`) without persisting it. |

### Inputs

**Real today:** every real `DepartmentOpinion` (stance, confidence,
summary), `compute_executive_accuracy_scores()`'s real per-department
accuracy read, and Chapter 65's real `MarketEnvironmentRegime` classifier
(`state.market_environment.current`) — the simpler 5-way one, not the
richer 13-way `market_intelligence.py` read, since `MARKET_CONDITION_
BOOSTS`'s table is keyed on the former. **Still not real, and not
fabricated:** the brief's other five named factors (Prediction Quality,
Current Expertise, Department Performance, Recent Reliability, Rule
Compliance, Specialization) — none feed any real formula in this pass.

### Outputs

**Now real:** `WeightedExecutiveRecommendation` — `departmentInfluences`
(a real, published weight + reasoning per department), `weightedAction`
distinct from `rawAction`, and `scoreByAction` (a normalized 0-100
breakdown of every action bucket, the exact numbers `weightedAction` was
chosen from). Computed fresh on every request, same convention as
`ExecutiveRecommendation` itself — never persisted, never a second
source of truth.

### Internal Workflow

**Now real, and deliberately not a replacement for the brief's own
implied flow.** `compute_weighted_recommendation()` (`app/weighted_
decisions.py`) runs department opinions in, computes a real weight per
department, maps each department's stance onto the same six-value
`ExecutiveAction` space `compute_executive_recommendation()` already
uses (`STANCE_TO_ACTION`), and picks the action with the highest
weight-times-confidence score (ties broken by a published, survival-
first `ACTION_TIE_BREAK_ORDER`). `compute_executive_recommendation()`'s
own priority-ordered rule chain is untouched — the two run in parallel,
never merged, so Raw and Weighted can genuinely disagree and both stay
visible.

### Decision Logic

**Now real, for the two inputs that have one.** `compute_department_
influence()`'s formula is fully published, per profile: Equal Voting =
1.0 always; Performance Weighted = the real accuracy multiplier only;
the four "First" profiles = a static, published preset multiplier;
Custom = the CEO's own per-department value; Balanced Institutional
(the default) = accuracy multiplier × market multiplier, both real and
shown separately in the reasoning string. Matches this Design Bible's
"no black-box composite" convention exactly — every multiplier is its
own field on `DepartmentInfluence`, never collapsed into an opaque
number. **Still not real:** any formula incorporating the six
unimplemented factors, since none has a real source.

### Department Cooperation

**Receives from:** Part 2 of this chapter (the real 9-department
`DepartmentOpinion`/`ExecutiveRecommendation` system this part re-weighs,
never recomputes), Chapter 65 (the real market-regime read this part's
Dynamic Market Adaptation now actually reads from). **Explicitly does
NOT receive from, by design:** Chapters 57/58/66's Trade Gatekeeper —
this part reads nothing from it and writes nothing to it, keeping its
real, absolute veto completely untouched (see Ownership's Compliance-
veto finding). **Provides:** a real Weighted Executive Recommendation
and per-department Influence Scores to `ExecutiveVoting.tsx`'s new
panel, alongside the real Raw Vote it already shows.

### CEO Controls

| Control | Status |
|---|---|
| Ignore weighting / view raw votes | **Real** — the Raw Vote (`rawAction`) is always present on `WeightedExecutiveRecommendation` alongside the weighted one; the CEO can also just leave the profile on `equal_voting`. |
| Equalize all votes | **Real** — the `equal_voting` profile, giving every department a flat 1.0× weight. |
| Prioritize specific executives | **Real** — `risk_first`/`growth_first`/`research_first`/`capital_preservation` (published presets) or `custom` (CEO-set per department). |
| Override any recommendation | **Already real**, for the underlying trade decision (unchanged from Parts 1/2) — the CEO's decision always wins; this predates and is unrelated to any weighting concept. |
| Lock custom executive weights | **Not built as a distinct lock/unlock state** — the `custom` profile's weights simply persist until edited again; there's no separate "locked" flag. |
| Create custom weighting profiles | **Real** — the `custom` `WeightProfile` + `SettingsState.customDepartmentWeights`, edited via `ExecutiveVoting.tsx`'s per-department number inputs. |

### Weight Profiles

**Now real, all eight, by name** — `WeightProfile` (`app/schemas.py`).
Each has its own real formula in `compute_department_influence()`:
`equal_voting` (flat 1.0×), `performance_weighted` (accuracy multiplier
only), the four "First" profiles (`WEIGHT_PROFILE_STATIC_PRESETS`, a
published emphasis table — e.g. `risk_first`: Risk 2.0×, Devil's
Advocate 1.5×, Simulation 1.3×), `balanced_institutional` (the default —
accuracy × market, both real and dynamic), and `custom` (CEO-set,
persisted). The CEO switches profiles via a dropdown in `ExecutiveVoting.
tsx`'s new panel, previewing any profile's effect on the currently open
proposal live before committing to it as the active one — matching the
brief's own "switch profiles instantly" ask.

### Learning System

**Still not built, for a persisted evolution loop** — and, this pass,
deliberately not attempted: see Ownership's "Performance-Based
Evolution" row. `compute_executive_accuracy_scores()` and
`DepartmentSelfEvaluation` both remain real, permanent records a future
evolution loop could read from; this pass reads the former live, every
request, rather than inventing a stored, decaying influence value with
no resolved design for what "losing influence" durably means.

### KPIs

**Real and computable today:** `compute_executive_accuracy_scores()`'s
per-department `accuracyPct` (unchanged from Part 2), and now
`DepartmentInfluence.finalWeight` — a real, live, per-decision weight,
computed fresh, never stored as a KPI series. **Still not honestly
computable:** any KPI over the six unimplemented weighting factors.

### Reports

**Still not built** as a named, persisted WEDE report. `WeightedExecutiveRecommendation`
is real but ephemeral (computed fresh per request, same convention as
`ExecutiveRecommendation`) — `ExecutiveMeetingLogEntry` remains the
closest permanent analog, and does not yet record which Weight Profile
was active or what the weighted call would have been for a given
historical decision.

### Safety Systems

**Verified held, not just stated as a constraint.** Grep-confirmed:
`app/weighted_decisions.py` imports nothing from `app/gatekeeper.py` or
`app/risk_engine.py`, and nothing in `app/routers/executive.py`'s new
`weighted-decision` endpoint touches `state.trade_proposals`,
`state.decisions`, or any resolution path — it's read-only, computed
fresh, and never called from anywhere that could gate a trade. Chapter
66's Trade Gatekeeper remains exactly as absolute as before this pass;
Compliance's real veto authority was never diluted into "one more
weighted vote."

### Dependencies

Part 2 of this chapter (the real 9-department opinion system and
Executive Accuracy Score this part re-weighs), Chapter 65 (Market
Regime & Adaptive Strategy — the real regime read this part's Dynamic
Market Adaptation now consumes). Chapters 57/58/66 (Risk Authority) is
a dependency in the sense that this part must never touch it, not that
it consumes anything from it. All previous Design Bible chapters,
matching this volume's own established framing.

### Future Expansion

Extending the weighting formula with real sources for the six
unimplemented factors (Prediction Quality, Current Expertise,
Department Performance, Recent Reliability, Rule Compliance,
Specialization) if and when this codebase gains a real per-department
measure for any of them; a real Performance-Based Evolution loop that
persists and decays influence over time (deliberately not built this
pass — see Ownership); recording which Weight Profile was active on a
given historical decision (`ExecutiveMeetingLogEntry` doesn't yet carry
this); and — should this codebase ever decide to give Compliance/
Innovation a real department-opinion seat — deciding explicitly whether
and how they'd enter the weighting system without diluting the Trade
Gatekeeper's absolute veto. None of these were attempted unilaterally in
this pass.

### Design Bible Integration

**Real today:** the 9 real `DepartmentOpinion`s, `compute_executive_
accuracy_scores()`, and Chapter 65's real regime read are all now real
inputs to `app/weighted_decisions.py`, with zero changes required to
any of them. **Still not built:** any write path connecting Company
Memory or the Knowledge Graph to a department weight, and
`ExecutiveMeetingLogEntry` doesn't yet record the Weighted
Recommendation alongside the Raw one it already permanently stores.

### Company Principle

"Executives prove their expertise through results" and "the CEO always
remains the final decision-maker" — both now genuinely, mechanically
true, each in its own honest scope. The second remains absolute
(Chapter 66's Gatekeeper, verified untouched by this part's own Safety
Systems section above). The first is now real for the one factor this
pass gave a computable source to: a department's live accuracy score
now directly changes its weight under Performance Weighted and Balanced
Institutional — not a persisted "reputation" that grows over a career,
but a real, live consequence of real performance on real, closed
trades, recomputed honestly every time rather than accumulated.

### Part 3 Implementation Notes

**Pre-existing, found by direct research before this part was written:**
the 9 real `DepartmentOpinion` roles and `compute_executive_
recommendation()`'s real priority-ordered rule chain (Part 2,
unchanged); a real per-department accuracy score
(`compute_executive_accuracy_scores()`, built for Part 2 this same
run); Chapter 65's real, live 5-way `MarketEnvironmentRegime`
classifier; and a real, unconditional Trade Gatekeeper veto (Chapters
58/66).

**Built this pass, in `app/weighted_decisions.py` (new) — advisory
only, never gating a trade (verified — see Safety Systems above):**
- **Dynamic Influence Score** — `compute_department_influence()`,
  returning a real `DepartmentInfluence` per department: `accuracy
  Multiplier` (from the real accuracy score, neutral 1.0 when
  untracked), `marketMultiplier` (from `MARKET_CONDITION_BOOSTS`, a
  published regime → department table), `presetMultiplier` (from
  `WEIGHT_PROFILE_STATIC_PRESETS`), `finalWeight`, and a real,
  generated `reasoning` string spelling out exactly which components
  produced it.
- **Raw Vote vs. Weighted Recommendation** — `compute_weighted_
  recommendation()` maps every department's real stance onto the same
  six-value `ExecutiveAction` space the Raw Vote already uses
  (`STANCE_TO_ACTION`), tallies weight × confidence per action bucket,
  and picks the highest (ties broken by a published, survival-first
  `ACTION_TIE_BREAK_ORDER`). Both `rawAction` and `weightedAction` are
  always present together on `WeightedExecutiveRecommendation`.
- **Dynamic Market Adaptation** — `MARKET_CONDITION_BOOSTS`, applied
  live from `state.market_environment.current` under the default
  Balanced Institutional profile.
- **Eight Weight Profiles** — `WeightProfile` (`app/schemas.py`), each
  with its own named formula; persisted via `SettingsState.
  activeWeightProfile`/`customDepartmentWeights`, the same client-
  authoritative mechanism `operatingMode` already uses (no new
  persistence endpoint).
- `GET /api/executive/weighted-decision` (`proposalId`, optional
  `profile` override for previewing without persisting).
- Frontend: `ExecutiveVoting.tsx`'s new panel — Raw vs. Weighted vote
  pills, published score-by-action breakdown, per-department influence
  cards with their reasoning, a profile dropdown with live preview, and
  a Custom CEO Profile per-department weight editor.

**Deliberate scope decisions, not gaps to silently fill later:**
Compliance and Innovation were not added as new `DepartmentOpinion`
roles just to give the brief's named seats something to weight (see
Primary Responsibilities); no Performance-Based Evolution loop persists
or decays influence over time (accuracy is read live, every request,
never accumulated — this codebase's own "no fake progression" rule);
the Trade Gatekeeper was not touched in any way.

**What's genuinely still unbuilt:** real sources for the six weighting
factors this pass couldn't honestly compute (Prediction Quality,
Current Expertise, Department Performance, Recent Reliability, Rule
Compliance, Specialization); a persisted evolution loop; and recording
the Weighted Recommendation on `ExecutiveMeetingLogEntry` alongside the
Raw one it already stores permanently. Verified: mypy + ruff clean;
runtime-tested against the real `GameState` singleton across all 8
profiles (equal-voting neutrality, custom-weight override, preset
multipliers, the balanced-institutional blended formula); FastAPI
`TestClient` route registration + 404 handling; full save-module
persistence round-trip for the two new `SettingsState` fields; `tsc
--noEmit`/eslint/`npm run build` all clean; and a real Playwright test
against the live dev stack that boosts a research item to a genuine
trade proposal, opens the new panel, confirms all 9 departments render
with real influence data, and confirms switching the Weight Profile
dropdown live-previews a different published formula.
