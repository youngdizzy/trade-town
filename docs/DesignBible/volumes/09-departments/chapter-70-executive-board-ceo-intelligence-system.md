# Chapter 70 — Executive Board & CEO Intelligence System

**Status:** Not implemented, filed here rather than in Volume 10.
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
already mostly real. See the Implementation Notes at the bottom for the
full inventory.

## Executive Summary

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

## Company Philosophy

"Departments execute, employees specialize, the Executive Board
coordinates" is not a new principle to adopt — Chapter 66's own
Company Philosophy already established that survival-first discipline
flows top-down through real, working machinery (Sentinel, the Trade
Gatekeeper, AI Consensus Safety), and the Executive Intelligence
Network (`app/executive_intelligence.py`) already coordinates real
department opinions into one recommendation before any trade executes.
This chapter's job is naming that coordination layer explicitly and
extending it past trades into general company governance.

## Primary Responsibilities

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

## Ownership

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

## Inputs

**Real today:** every input this table confirms real above — trade
proposals, department opinions, `CompanyHealth`/`CompanyScore`,
Goals/Milestones, Company Memory. **Would need, once real:** a
non-trade-scoped decision object the CEO Decision Center could present
(does not exist), a Chief-Officer-to-agent mapping for the five unfilled
board seats (does not exist).

## Outputs

**Real today:** `ExecutiveReview`, `ExecutiveMeetingLogEntry`,
`computeExecutivePriorities()`'s merged list, `CompanyHealth`/
`CompanyScore`. **Would produce, once real:** a single Board Report
object combining all nine of the brief's own named fields, five
separate Top-5 priority lists instead of one merged list, and a
Strategic Roadmap view assembling the three real, currently-separate
sources named under Ownership.

## Internal Workflow

**The brief's own implied flow — department reports in, board discusses,
CEO decides, outcome recorded — already exists end to end for trade
proposals specifically:** `generate_department_opinions()` → 
`compute_executive_recommendation()` → CEO resolves via
`ExecutiveVoting.tsx` → `generate_meeting_log_entry()` records the
outcome permanently. A real Executive Board would generalize this exact
pipeline to non-trade decisions, not invent a second one.

## Decision Logic

**Real today, for every trade-scoped piece:** `compute_executive_
recommendation()`'s department-opinion aggregation is a transparent,
named formula, matching this codebase's "no black-box composite"
convention throughout. **Not real:** any formula for ranking or scoring
non-trade board proposals, or for computing the brief's own per-executive
Contribution Score — no composite scoring exists for either.

## Department Cooperation

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

## CEO Controls

| Control | Status |
|---|---|
| Configure meeting cadence (Daily/Weekly/Monthly/Quarterly) | **Partially real** — `CoachReport` already supports weekly/monthly cadence; no CEO-facing toggle exists to choose it, and no daily/quarterly option exists anywhere. |
| Enable Board Voting | **Not built** as a togglable setting — voting is real but always-on for trade decisions specifically, not a feature the CEO can enable/disable. |
| Approve / Reject / Delay / Modify / Delegate a proposal | **3 of 5 real** (Approve/Reject/Delay, via BUY/SELL/WAIT on trade proposals) — Modify and Delegate don't exist as CEO actions anywhere, for any decision type. |
| Assign a Chief Officer title to an agent | **Not built** — the four real "Chief" titles are fixed in `AgentProfiles.ts`, not CEO-assignable. |

## Learning System

**Already real, for the trade-decision-scoped half of this chapter:**
`ExecutiveMeetingLogEntry` already records whether the network's
recommendation and the CEO's actual decision agreed — a real, permanent
input a future learning loop could analyze. **Not built:** any learning
loop over non-trade board decisions, since no non-trade decision object
exists yet to generate history from.

## KPIs

**Real and computable today, narrowly:** whatever `CompanyScore`'s
breakdown and `computeDepartmentHealth()` already track. **Not
honestly computable:** a per-executive Contribution Score, Forecast
Accuracy, or Risk Prevention metric — no composite scoring exists for
any named Chief Officer today, since five of the twelve named seats
have no real occupant to score in the first place.

## Reports

**Real today:** `ExecutiveReview` (the closest real analog to a Board
Report), `ExecutiveMeetingLogEntry` (the closest real analog to Board
Meeting minutes). **Not built:** a single report object combining all
nine of the brief's own named Board Report fields, or any of the eight
Executive Scorecards.

## Safety Systems

This chapter inherits, rather than duplicates, Chapter 66's real
safety machinery — the Board Discussion System's real disagreement
signal already enforces a trading pause (Chapter 66's `pause_trading`),
and nothing in this chapter should build a second, competing
enforcement path. Emergency Board Meetings, if ever built, should
trigger *from* Chapter 66/67's real signals (a critical `RiskWarning`,
Emergency Stop activation), never invent a parallel detection layer.

## Dependencies

Chapters 63 (Executive Performance & Company Health), 64 (Executive
Strategic Planning), 66 (Institutional Safety — the real disagreement/
pause machinery), 67 (TTOS — the real Global Status Bar/Alert Center/
Command Palette this chapter's Executive Command Center substantially
already is). All previous Design Bible chapters, matching this volume's
own established framing.

## Future Expansion

A literal twelve-seat board with every named Chief Officer filled by a
real, distinct agent; automatic Emergency Board Meeting triggers; a CEO
Assistant AI; and a general-purpose (non-trade-scoped) Decision Center
all require real design decisions (new agents? repurposed existing
ones? a new proposal type distinct from `TradeProposal`?) not made
unilaterally in this pass. Matches this volume's own Future Expansion
precedent — named honestly, not stubbed.

## Design Bible Integration

**Real today, and already wired without this chapter's own help:**
Company Memory, the Knowledge Graph, Company Health, Risk Authority,
and the Executive Dashboard (Chapter 67's `useDashboardData()`) all
already consume the real systems this chapter would coordinate — this
chapter's own value is organizing what already flows between them into
one board-shaped view, the same relationship Chapter 67's TTOS has to
the 34 tabs it groups, never a new parallel data layer.

## Company Principle

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

## Implementation Notes

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
