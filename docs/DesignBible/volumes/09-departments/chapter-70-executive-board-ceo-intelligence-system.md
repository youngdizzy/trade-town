# Chapter 70 — Executive Board & CEO Intelligence System

**Status:** Three parts. **Part 1** (below) is now substantially
implemented: a real 11-seat Board Roster, a real Board Report on
Daily/Quarterly/Emergency cadence (composing already-real signals,
never a duplicate computation), and two real Emergency Board Meeting
triggers (Emergency Stop activation, Black Swan tier crossing into
red/critical). Four items are explicitly deferred, not built and not
faked: per-executive scorecards, a CEO Assistant AI, CEO-assignable
Chief titles, and a general-purpose non-trade Decision Center — each
documented in its own **Deferred Features** section below with its
current state, the real missing infrastructure, dependencies, a
recommended future chapter, an estimated complexity, and the risks of
building it prematurely. See this Part's own Implementation Notes for
the full inventory. **Part 2** (the Executive Consensus Meter addendum) is
real: Modify joins Approve/Reject/Delay/Delegate as a genuine CEO
decision action, and a real Executive Accuracy Score scores each
department's directional stance against actual closed-trade P&L. **Part
3** (further down, the Weighted Executive Decision Engine) is now real
too: a published, per-department weighting layer over the existing
Consensus Meter, honestly scoped to the only two of the brief's eight
named inputs with a real, computable source — Historical Accuracy and
Market Conditions. **A follow-up Design Bible addendum then required
WEDE to feed the Trade Gatekeeper directly** ("The Executive Board
recommends. The Trade Gatekeeper decides.") **while remaining
advisory-only — also now real:** `app/gatekeeper.py` gained a 9th
unconditional check reading WEDE's real output, with the exact same
authority as every other check (can contribute to a rejection, can
never force an approval or bypass any other check), wired into both
real paths that can open a position (a manual CEO decision and
Assisted/Executive auto-resolution). See each part's own Implementation
Notes (Part 2) or Part 3 Implementation Notes for the exact honest
inventory of what's built and what remains out of scope.
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
calls the Executive Command Center. **Now real, this pass:** a Board
Roster (`GET /api/board/roster`, computed fresh from the same real
agent identities every other agent-facing UI already uses) covering 11
of the brief's own 12 named seats — the 12th is never named anywhere
in the source brief itself and is deliberately not invented; and a
Board Report (`GET /api/board/reports`) on Daily/Quarterly/Emergency
cadence, composing seven of the brief's nine named Board Report fields
from already-real sources (Department Health, Problems, Recommendations,
a narrative summary, and — new this pass — Risk Assessment, Confidence
Level, and Required CEO Decisions, each reusing an existing real number
rather than inventing one). Two of the brief's own seven named Emergency Board Meeting triggers are
real (Emergency Stop activation — both automatic and CEO-manual — and
Black Swan tier crossing into red/critical); Broker Failure remains
confirmed absent (no real broker exists, Chapter 68), and the brief's
own remaining triggers are not individually named anywhere in this
chapter's Ownership research and are not fabricated here either. What
remains genuinely
deferred — not built, and explicitly not faked to look built — is
narrower still: per-executive scorecards, a CEO Assistant AI,
CEO-assignable Chief titles, and a general-purpose non-trade Decision
Center. See this Part's own **Deferred Features** section for exactly
why each one doesn't fit today's real architecture, and what would need
to change for it to.

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
| "Board Members" (12 named Chief-Officer seats) | **Now real — an 11-seat Board Roster** (`app/board.py::compute_board_roster()`, `GET /api/board/roster`) | 4 real agents already hold a "Chief" title in `AGENT_PROFILES` (agents.py/AgentProfiles.ts, kept in sync): Meridian is literally "Chief Investment Officer" (exact match); Keystone is "Chief Risk Architect," Compass is "Chief Learning Architect," Vector is "Chief Quantitative Strategist" — close to, but not exact matches for, the brief's CRO/Chief Knowledge Officer/CQO, disclosed as such rather than silently relabeled. The roster adds the brief's own 7 other named-but-unfilled titles (Chief Research/Technology/Operations/Compliance/Innovation/Portfolio/Market Intelligence Officer) as real vacant seats. **The brief's own source document names only 11 of its claimed 12 seats anywhere in the file — the 12th is never named and is deliberately not invented; see Implementation Notes.** |
| "Executive Board Meetings" (Daily/Weekly/Monthly/Quarterly/Emergency) | **Now real, all five cadences** — `FounderCouncilSession` + `ExecutiveReview` (Weekly/Monthly) + the new Board Report (`app/board.py`, Daily/Quarterly/Emergency) | `FounderCouncilSession` (`app/founders.py`) — a real monthly Coach+Founders sit-down. `ExecutiveReview` (`app/executive_review.py`) — real, monthly. `CoachReport` — weekly and monthly (`ReflectionCadence`). **New this pass:** the Board Report's Daily cadence (the same `is_evening`-only gate Feature 51's Market Brief already established) and Quarterly cadence (a new `day % 90 == 0` gate, the identical shape Weekly/Monthly already use) — deliberately not duplicating CoachReport/ExecutiveReview's own Weekly/Monthly coverage. Emergency cadence is now real too, on 2 of the brief's 7 named triggers — see the "Emergency Board Meeting" row below. |
| "Board Report Format" (9 named fields) | `ExecutiveReview`'s real fields, plus the new Board Report | Real matches on `ExecutiveReview`: Department Health → `departmentActivity` + `companyHealthTier`; Completed Objectives → `researchCompleted`/`knowledgeGained`/`lessonsCompleted`; Problems → `flags`; Recommendations → `recommendations`; a narrative → `summary`. **New this pass, on the Board Report specifically:** Department Health (reuses the same shared `compute_department_activity()`, moved out of `executive_review.py` so both report types call one real function, never two competing ones), Problems, Recommendations (reused verbatim from `CompanyHealth.recommendations`), a narrative `summary`, Risk Assessment (a real one-line composition of the already-real Black Swan tier + Daily Circuit Breaker tier), Confidence Level (reuses `CompanyHealth.department_consensus` verbatim — a real, already-computed, company-wide agreement-rate KPI, never a new number), and Required CEO Decisions (`len(trade_proposals)`, the same real count Chapter 73.5's Situation Room already uses for its own "Pending CEO Decisions" field). **Still not real, and not fabricated:** Opportunities and Expected Impact — neither has a real computable source anywhere in this codebase. |
| "CEO Decision Center" (Summary/Evidence/Benefits/Risks/Probability/Capital/Time Horizon/Departments/Confidence, Approve/Reject/Delay/Modify/Delegate) | `ExecutiveVoting.tsx` + `TradeDecision` | Real, but scoped only to trade proposals: Summary (symbol + reasoning), Supporting Evidence (agent votes), Probability (confidence score), Affected Departments (supporting/opposing agents) are all real. CEO options are real but narrower: BUY/SELL/WAIT map to Approve/Reject/Delay; Modify and Delegate are now real CEO actions too, per Part 2's own Implementation Notes below. **Deferred, not built this pass:** a general-purpose Decision Center for non-trade decisions — see this Part's own Deferred Features section for exactly why. |
| "Board Discussion System" (evidence-based debate, CEO sees both sides) | `generate_department_opinions()` (`app/executive_intelligence.py`) | Real and genuinely evidence-based: real department stances that can actively oppose each other, feeding `compute_executive_recommendation()`'s real `pause_trading` enforcement (Chapter 66). Scoped to trade proposals only — no general "Risk Officer disagrees with CIO on a non-trade matter" mechanism exists. |
| "Board Voting" (Unanimous/Majority/Split/Tie/CEO Override, recorded in Company Memory) | `AgentVote` on `TradeDecision.votes`, `ExecutiveMeetingLogEntry` | Real: every trade decision already carries individual agent votes, aggregated via `voteDirection()`; `ExecutiveMeetingLogEntry` (`app/schemas.py`) is a real, permanent record of what every department said, what the network recommended, and what the CEO actually decided, generated on every real `resolve_proposal()` call. **Not real:** "Tie" and "CEO Override" as distinctly labeled outcomes (the CEO's decision already always wins; there's no vote-tally state machine naming these cases), and none of this exists for non-trade board proposals. |
| "Company Health Review" (9 named categories) | `CompanyScore` + `CompanyHealth` | Strong real match: `companyScore`'s breakdown (Research/Decisions/Risk/Paper Trading Performance/Teamwork/Simulation, per `OverviewPanel.tsx`) and `CompanyHealth.overall`/`.tier` cover Financial/Portfolio/Risk/Research/Employee-Performance/Automation ground honestly. **Not real:** "Infrastructure" as a tracked dimension — no infrastructure concept exists anywhere in a paper-trading sim with no real broker or server-health signal to report on. |
| "Executive Priorities" (5 separate Top-5 lists) | `computeExecutivePriorities()` (`derive.ts`) | Real, but a different shape, and its own code comment already names this exact tension: it merges and dedupes `CompanyHealth.recommendations`, the latest `CoachReport.recommendations`, and the latest `ExecutiveReview.recommendations` into **one** ranked list, ordered by which real system raised the point first — never split into five separate Opportunities/Risks/Objectives/Bottlenecks/Actions categories, and never capped at exactly 5. |
| "Strategic Roadmap" | Chapter 64's real Goals/Milestones, Chapter 45's Research Sandbox `Strategy` stage history, Hall of Fame | Real, distributed: CEO-authored Goals with real tracked progress and 25/50/75% milestone checkpoints (Current/Long-Term Goals); `Strategy.stageHistory` (Upcoming Features/Research Projects, loosely); Hall of Fame (Completed Milestones, loosely). Never assembled into one named "Strategic Roadmap" view. |
| "Board Memory" | Company Memory (Chapter 61) | Real, permanent, and already the exact shape this brief asks for — decisions, reasoning, evidence, and outcomes are already recorded for every real event category this codebase produces, including trade decisions and Emergency Stop activations. |
| "Emergency Board Meeting" (auto-triggered on 7 named events) | **Now real for 2 of the brief's 7 named triggers** — the Board Report's `"emergency"` cadence (`app/board.py`) | Fires once on a real edge-crossing, never every tick while the condition holds — the identical convention Chapter 72's own Crisis Briefing already established: (1) Emergency Stop activation, from any real source (automatic — Daily Circuit Breaker Tier 4 or a losing-streak suspension, both in `app/nexus.py` — or CEO-manual, in `app/state.py::activate_emergency_stop()`); (2) Black Swan tier crossing into red/critical (`app/nexus.py`, the same crossing that already fires the real Crisis Briefing). Broker Failure remains confirmed absent (no real broker exists, Chapter 68). The brief's other named triggers are not individually specified anywhere in this chapter's own research and are not fabricated here. |
| "Executive Scorecards" (8 named metrics per executive) | `CompanyScore` breakdown, `computeDepartmentHealth()` | Partial real coverage: `computeDepartmentHealth()` already computes real Efficiency/Workload/Morale/Productivity-shaped metrics per real subsystem. **Deferred, not built this pass** — see this Part's own Deferred Features section: the real per-department accuracy/influence numbers (Parts 2/3) are role-keyed, not agent-keyed, and don't map cleanly onto the 4 filled Chief seats without a new, unresolved identity-mapping decision. |
| "CEO Assistant" (summarize meetings, prioritize tasks, prepare agendas) | *(does not exist)* | Sage is a real "Socratic Mentor" (Q&A, never tells the CEO what to think, per its own personality field) — the opposite job from an assistant that prioritizes and summarizes. **Deferred, not built this pass** — see this Part's own Deferred Features section: the brief's own source document names only 3 of its claimed "six named Assistant responsibilities," and the other 3 are not specified anywhere. |
| "Executive Command Center" (10 named live metrics) | `GlobalStatusBar.tsx` + `useDashboardData()` + Executive Alert Center (all Chapter 67) | The strongest real match of any section in this brief: Company Health✓, Market Regime✓, Portfolio Health✓ (Portfolio Heat), Risk Status✓, Major Alerts✓ (the real Alert Center), Executive Recommendations✓ (`computeExecutivePriorities`), Pending CEO Decisions✓ (the real Pending Proposals queue, Chapter 59) are all real today, already live, already CEO-facing — just distributed across Chapter 67's Global Status Bar/Alert Center/Command Palette rather than one consolidated screen. Broker Health is real only as the honest static "SIMULATED" pill; Active Objectives (Chapter 64 Goals) and Capital Allocation (RiskPanel) exist but aren't surfaced on this particular strip today. |

### Inputs

**Real today:** every input this table confirms real above — trade
proposals, department opinions, `CompanyHealth`/`CompanyScore`,
Goals/Milestones, Company Memory, `AGENT_PROFILES` (the Board Roster's
own real input). **Deferred, would need once built:** a non-trade-scoped
decision object the CEO Decision Center could present, and a real
role↔agent identity mapping for per-executive scorecards — see this
Part's own Deferred Features section for both.

### Outputs

**Real today:** `ExecutiveReview`, `ExecutiveMeetingLogEntry`,
`computeExecutivePriorities()`'s merged list, `CompanyHealth`/
`CompanyScore`, and — new this pass — `BoardRoster` and `BoardReport`
(7 of the brief's own 9 named Board Report fields, composed from
already-real sources, never a duplicate computation). **Deferred, would
produce once built:** five separate Top-5 priority lists instead of the
current one merged list, and a Strategic Roadmap view assembling the
three real, currently-separate sources named under Ownership — neither
was in scope for this pass.

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
convention throughout. The Board Report's own Risk Assessment/
Confidence Level/Required CEO Decisions fields are each a direct reuse
of an existing real number, never a new formula. **Deferred:** any
formula for ranking or scoring non-trade board proposals, or for
computing the brief's own per-executive Contribution Score — see this
Part's own Deferred Features section for why the latter isn't a simple
formula gap but an unresolved identity-mapping question.

### Department Cooperation

**Would receive from:** Chapter 63 (Executive Performance & Company
Health — the real `CompanyHealth`/`CompanyScore` this chapter's own
Company Health Review reuses directly), Chapter 64 (Strategic Planning —
the real Goals/Milestones this chapter's Strategic Roadmap reuses),
Chapter 61 (Knowledge Graph/Company Memory — real, this chapter's own
Board Memory), Chapter 66 (the real department-opinion/disagreement
machinery this chapter's Board Discussion System already is, scoped to
trades), Chapter 67 (the real Global Status Bar/Alert Center this
chapter's Executive Command Center already substantially is), Chapter
73 (the Audit Log, which now picks up every real emergency Board Report
via the new `board_report` category). **Provides, now real:** the Board
Roster and Board Report to any department that wants a real, composed
read of company-wide state. **Deferred:** Executive Scorecards and a
Strategic Roadmap view — see the Deferred Features section.

### CEO Controls

| Control | Status |
|---|---|
| Configure meeting cadence (Daily/Weekly/Monthly/Quarterly) | **All four cadences are now real** (CoachReport/ExecutiveReview for Weekly/Monthly, the Board Report for Daily/Quarterly) — no CEO-facing toggle exists to choose *which* cadences run; all real cadences fire unconditionally, matching every other periodic report in this codebase (none of which are individually togglable either). |
| Enable Board Voting | **Not built** as a togglable setting — voting is real but always-on for trade decisions specifically, not a feature the CEO can enable/disable. |
| Approve / Reject / Delay / Modify / Delegate a proposal | **Now 5 of 5 real** — Modify and Delegate are real CEO actions per Part 2's own Implementation Notes below (built for that section, reused here rather than duplicated). |
| Assign a Chief Officer title to an agent | **Deferred, not built this pass** — see this Part's own Deferred Features section. The Board Roster (this pass) is real and read-only; the four real "Chief" titles remain fixed in `AGENT_PROFILES`, not CEO-assignable. |

### Learning System

**Already real, for the trade-decision-scoped half of this chapter:**
`ExecutiveMeetingLogEntry` already records whether the network's
recommendation and the CEO's actual decision agreed — a real, permanent
input a future learning loop could analyze. **Not built:** any learning
loop over non-trade board decisions, since no non-trade decision object
exists yet to generate history from.

### KPIs

**Real and computable today:** whatever `CompanyScore`'s breakdown and
`computeDepartmentHealth()` already track, plus — new this pass — the
Board Report's own Confidence Level (`CompanyHealth.department_
consensus`, reused verbatim) and Required CEO Decisions
(`len(trade_proposals)`). **Not honestly computable:** a per-executive
Contribution Score, Forecast Accuracy, or Risk Prevention metric — see
the Deferred Features section for exactly why this is an identity-
mapping gap, not a missing formula.

### Reports

**Real today:** `ExecutiveReview`, `ExecutiveMeetingLogEntry`, and — new
this pass — the Board Report (`app/board.py`, 7 of the brief's own 9
named fields, Daily/Quarterly/Emergency cadence, capped and
WS-broadcast). **Deferred:** any of the brief's named Executive
Scorecards — see the Deferred Features section.

### Safety Systems

This chapter inherits, rather than duplicates, Chapter 66's real
safety machinery — the Board Discussion System's real disagreement
signal already enforces a trading pause (Chapter 66's `pause_trading`),
and nothing in this chapter should build a second, competing
enforcement path. Emergency Board Meetings are now real, and trigger
*from* Chapter 66/67/72's own real signals exactly as this section
originally specified — Emergency Stop activation and a Black Swan tier
crossing into red/critical — never a parallel detection layer of their
own; see this Part's own Implementation Notes for the exact trigger
points in `app/nexus.py`/`app/state.py`.

### Dependencies

Chapters 63 (Executive Performance & Company Health), 64 (Executive
Strategic Planning), 66 (Institutional Safety — the real disagreement/
pause machinery), 67 (TTOS — the real Global Status Bar/Alert Center/
Command Palette this chapter's Executive Command Center substantially
already is). All previous Design Bible chapters, matching this volume's
own established framing.

### Deferred Features

Four items from this Part's own brief are explicitly deferred — not
built, and not faked to look built. Each is documented here in full so
a future session can pick it up without re-deriving this research: what
exists today, exactly what real infrastructure is missing, what this
depends on, which future chapter should own it, a rough complexity
estimate, and the concrete risk of building it prematurely.

#### Per-executive scorecards

- **Current state:** `compute_executive_accuracy_scores()` (Part 2) and
  `DepartmentInfluence` (Part 3) are both keyed on the 9-value
  `ExecutiveDepartmentRole` enum (research/quant/risk/simulation/
  decision_intelligence/coach/founders/devils_advocate/market_
  intelligence), not on `AgentId`. Only 4 of those 9 roles carry a real
  `agentId` on their `DepartmentOpinion` today (risk, simulation,
  founders, devils_advocate), and none of the 4 map to this Part's own
  4 filled Chief seats (cio/keystone/compass/quant) — Meridian (CIO)
  never casts a `DepartmentOpinion` at all; she authors `ExecutiveReview`
  separately. The one genuinely per-agent-id real number,
  `DepartmentActivity` (research/decisions counts, now shared via
  `compute_department_activity()`), is an activity-volume count, not a
  quality or accuracy score.
- **Missing infrastructure:** a real role↔agent identity mapping for
  the 4 filled Chief seats into the 9-role `DepartmentOpinion` system
  (or a wholly separate per-agent accuracy computation) does not exist
  anywhere in this codebase.
- **Dependencies:** Part 2 (Executive Accuracy Score), Part 3
  (Department Influence), and this Part's own Board Roster (the seat
  list a scorecard would attach to).
- **Recommended future chapter:** a Chapter 70 Part 4 addendum, once a
  real agent↔role identity mapping has an actual resolved design — not
  a standalone new chapter, since it's a direct extension of Parts 2/3's
  own real machinery.
- **Estimated implementation complexity:** Medium. The accuracy/
  influence math already exists and is real; the entire remaining cost
  is resolving identity mapping and deciding what a scorecard shows for
  the 7 vacant seats that have no agent at all.
- **Risks of implementing prematurely:** silently declaring, e.g.,
  "Keystone is the risk vote" when Sentinel is the agent who actually
  casts it today would misattribute real trade outcomes to the wrong
  agent's track record — corrupting the Executive Accuracy Score's own
  real accountability, not just this feature. Inventing placeholder
  "N/A" scorecards for the 7 vacant seats would be exactly the fake-
  progression UI this project's engineering discipline forbids.

#### CEO Assistant AI

- **Current state:** zero existing "assistant" agent or mechanism
  anywhere in `backend/app` (grep-confirmed). This chapter's own source
  brief names only 3 of its claimed "six named Assistant
  responsibilities" anywhere in the document — summarize meetings,
  prioritize tasks, prepare agendas — the other 3 are not specified.
- **Missing infrastructure:** no conversational or summarization
  pipeline exists in this codebase at all — every "AI" output today
  (Sage's Q&A, `ExecutiveReview.summary`, `CoachReport`) is deterministic
  template/string generation over real state, never a generative model
  call (this codebase has zero LLM calls anywhere). Building even the 3
  named responsibilities honestly requires first deciding whether they
  stay in that same deterministic-narrative convention or introduce this
  codebase's first real generative-text mechanism — a real architectural
  fork, not a detail.
- **Dependencies:** `computeExecutivePriorities()` ("prioritize tasks")
  and `ExecutiveMeetingLogEntry` ("summarize meetings") already exist as
  real raw ingredients; "prepare agendas" has no real analog anywhere in
  this codebase today.
- **Recommended future chapter:** its own explicitly-scoped chapter,
  written only once the source brief's other 3 responsibilities are
  actually specified — they cannot be honestly scoped from what exists
  today without inventing them.
- **Estimated implementation complexity:** Medium if kept deterministic
  (assembling already-real data into a narrative, matching
  `ExecutiveReview`'s own precedent exactly); High if it introduces a
  first generative mechanism, since that carries cost/latency/
  determinism tradeoffs this codebase's engineering discipline has never
  had to weigh before.
- **Risks of implementing prematurely:** naming only 3 of the brief's 6
  claimed responsibilities and inventing the other 3 to "complete" the
  feature is exactly the fabrication this project's discipline forbids.
  Treating Sage as this Assistant would silently overload an existing
  agent's identity — Sage's own `personality` field states its job is
  the opposite one (never telling the CEO what to think).

#### CEO-assignable Chief titles

- **Current state:** the 4 filled seats are hardcoded, static data in
  `AGENT_PROFILES` (`agents.py`/`AgentProfiles.ts`, kept in sync) as
  each agent's own `occupation` string. This Part's new Board Roster
  reads them read-only; nothing persists a CEO-chosen assignment.
- **Missing infrastructure:** no persisted "who holds which seat" state
  distinct from the static agent profile; no CEO-facing assignment
  endpoint or control; and, most importantly, no resolved rule for what
  happens to an agent's existing `occupation` display everywhere else in
  this codebase (NPC labels, dialogue, Command Center panels) if a seat
  becomes independently reassignable.
- **Dependencies:** this Part's own Board Roster (`app/board.py`) as
  the read surface a real assignment control would attach to;
  `AGENT_PROFILES`'s own static-data architecture, which is read from
  in many places well outside this chapter.
- **Recommended future chapter:** a Chapter 70 Part 1 addendum, written
  only once the Board Roster has been live for a real pass and there is
  an observed need to reassign seats — not built speculatively ahead of
  that need.
- **Estimated implementation complexity:** Low-Medium in isolation (a
  new persisted `dict[seat_title, AgentId | None]` plus one CEO
  endpoint), but the blast radius of getting the override layer wrong
  is wider than the feature itself, since `AGENT_PROFILES.occupation` is
  read pervasively across NPC rendering, dialogue, and the Command
  Center.
- **Risks of implementing prematurely:** without a resolved design for
  whether/how a reassigned title propagates to every other place
  `occupation` is displayed, this creates exactly the kind of partially
  duplicated architecture this chapter's own workflow was told to avoid
  — two competing sources of truth for "what is this agent's title."

#### General-purpose non-trade Decision Center

- **Current state:** every non-trade CEO approval this codebase has
  today (Strategy Lab promotion, Innovation Lab budget, Goal creation,
  Constitution amendments, Treasury savings rules, and more) has its
  own separate, ad hoc UI and its own decision-recording shape —
  confirmed directly against the code before this chapter's Ownership
  table was written. No shared `Decision` object, no shared Approve/
  Reject/Delay/Modify/Delegate action set, and no shared decision log
  spans across any of them.
- **Missing infrastructure:** a real, generalized `Decision` schema
  abstract enough to cover trade proposals and every one of those ad
  hoc approvals without forcing an awkward fit; a migration plan for
  each existing flow to either move onto it or stay explicitly separate;
  and a single log/history view spanning all of them — the closest real
  analog, `ExecutiveMeetingLogEntry`, is trade-only.
- **Dependencies:** every existing CEO-approval flow this codebase has
  — a change of this scope touches most of the department chapters
  already written, not just this one.
- **Recommended future chapter:** its own dedicated Design Bible
  chapter, never a Chapter 70 Part — scoped only after an explicit audit
  of every existing ad hoc approval flow's real shape. Folding a change
  this size into Part 1 here would itself be exactly the vague,
  underscoped general-purpose Decision Center this chapter was told not
  to build.
- **Estimated implementation complexity:** High. This is a cross-cutting
  architectural change touching most department chapters' own CEO
  Controls, not a contained feature addition.
- **Risks of implementing prematurely:** a hastily generalized
  `Decision` object risks becoming exactly the kind of duplicate,
  parallel system Appendix G forbids — competing with each department's
  own real, working approval flow rather than replacing it cleanly. A
  vague, half-migrated Decision Center would leave this codebase with
  two competing approval architectures at once, the specific failure
  mode this chapter was explicitly told to avoid.

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

**Pre-existing, found by direct research before this pass began:** a
real monthly CIO review (`ExecutiveReview`); a real, permanent
per-decision meeting log (`ExecutiveMeetingLogEntry`); a real merged
executive-priorities list (`computeExecutivePriorities()`); a real
Company Health/Score breakdown; real Goals/Milestones (Chapter 64) and
Hall of Fame as distributed Strategic Roadmap material; a real,
evidence-based department-disagreement system enforcing a trading pause
(Chapter 66); Chapter 67's Global Status Bar/Executive Alert
Center/`useDashboardData()`; and, from Part 2 below, Modify/Delegate as
real CEO decision actions.

**Built this pass:**
- **Board Roster** (`app/board.py::compute_board_roster()`,
  `GET /api/board/roster`) — 11 of the brief's own 12 named seats
  (4 filled by real agents, 7 named-vacant, all titles copied verbatim
  from the brief, never invented). Computed fresh, never persisted —
  agent identity rarely changes and there is nothing here worth
  snapshotting.
- **Board Report** (`app/board.py::generate_board_report()`,
  `GET /api/board/reports`, persisted, capped at `MAX_BOARD_REPORTS`
  (60), broadcast over WS) — composes already-real signals into 7 of
  the brief's own 9 named Board Report fields (Department Health,
  Problems, Recommendations, a narrative Summary, Risk Assessment,
  Confidence Level, Required CEO Decisions); Opportunities and Expected
  Impact remain uncomputable and are not fabricated. `compute_
  department_activity()` was promoted out of `app/executive_review.py`
  (was `_department_activity()`, module-private) into a shared function
  both `ExecutiveReview` and the Board Report now call — one real
  computation, never two.
- **Daily and Quarterly cadence** — the two genuinely missing cadences
  this chapter's own research confirmed (Weekly/Monthly were already
  real via CoachReport/ExecutiveReview). Daily reuses Feature 51's
  `is_evening`-only gate; Quarterly adds one new `QUARTERLY_INTERVAL_
  DAYS = 90` constant, the identical `day % N` shape Weekly/Monthly
  already use.
- **Two real Emergency Board Meeting triggers**, both firing once on a
  real edge-crossing — never every tick while the condition holds, the
  same convention Chapter 72's Crisis Briefing already established:
  Emergency Stop activation (from any real source — automatic Circuit
  Breaker Tier 4/losing-streak in `app/nexus.py`, or CEO-manual in
  `app/state.py::activate_emergency_stop()`) and a Black Swan tier
  crossing into red/critical (the same crossing that already fires the
  real Crisis Briefing). Each emergency report also writes a real,
  permanent `MemoryRecord`, picked up by Chapter 73's Audit Log via a
  new `board_report` category.

**What's genuinely, entirely deferred — not built, and not faked to
look built:** per-executive scorecards, a CEO Assistant AI,
CEO-assignable Chief titles, and a general-purpose non-trade Decision
Center. Each is documented in full in this Part's own **Deferred
Features** section above — current state, missing infrastructure,
dependencies, a recommended future chapter, an estimated complexity,
and the risk of building it prematurely. Also genuinely unbuilt: the
brief's own 12th board seat (never named anywhere in the source
document — not invented here), and 5 of the brief's 7 named Emergency
Board Meeting triggers (only Broker Failure is individually confirmed
absent, per Chapter 68; the others are not individually specified
anywhere in this chapter's own research and are not fabricated).
Verified: `mypy app/` clean, `ruff check app/` clean, 18 new tests
(`tests/test_board.py`) passing alongside the full existing suite
(1321/1321). **Frontend:** the Board Roster and Board Reports were
added to the existing `EXECINTEL` tab (`ExecutiveIntelPanel.tsx`)
rather than a new tab, extending its established UI surface. Verified:
`tsc --noEmit`/`eslint`/`vite build` clean, a live dev-stack walkthrough
confirming both sections render real data with no console errors, and
the full Playwright regression suite (40 tabs, unchanged this pass; 31
passed, 1 skipped, 1 failed — the same pre-existing movement-hold
timing flake, untouched by this change).

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
| "Compliance has veto authority" | **Confirmed still absolute — and WEDE now feeds the Gatekeeper as one more input, per the Design Bible's own follow-up addendum** | `app/gatekeeper.py::_weighted_executive_check()` is a real 9th check in `evaluate_gatekeeper()`'s unconditional `all(checks)` list — the exact same authority as Decision Confidence or Portfolio Exposure: it can contribute to a REJECTION, never force an approval, and cannot override or skip any other check. `app/weighted_decisions.py` itself still touches nothing in the Gatekeeper/Risk Authority pipeline (verified — see Safety Systems below); the caller (`app/state.py`'s `submit_ceo_decision`, `app/nexus.py`'s auto-resolve path) computes the real `WeightedExecutiveRecommendation` and passes it in as data, the same way every other check's real input already flows in. Compliance's real veto authority is undiminished — a favorable WEDE read cannot rescue a trade any other real check would still reject. |
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

**A follow-up Design Bible addendum asked explicitly that WEDE "feed
recommendations into the Trade Gatekeeper, while remaining advisory
only" — implemented, and the exact authority boundary verified, not
just stated:** `app/gatekeeper.py::_weighted_executive_check()` is a
9th check in the same unconditional `all(checks)` list every other real
Gatekeeper check already lives in. It can contribute to a rejection
exactly like Decision Confidence or Portfolio Exposure; it cannot
approve a trade on its own, and it cannot skip, weaken, or override any
of the other eight checks — proven by a real test
(`test_a_favorable_weighted_recommendation_cannot_rescue_a_failing_
confidence_check`) confirming a favorable WEDE read does nothing when
Decision Confidence still fails. `app/weighted_decisions.py` itself
still imports nothing from `app/gatekeeper.py` or `app/risk_engine.py`
— the computation and the enforcement stay separate modules; only the
already-computed result crosses the boundary, as plain data, the same
way every other check's real input already does. Both real production
paths that can open a position — a manual CEO click
(`app/state.py::submit_ceo_decision`) and Assisted/Executive-mode
auto-resolution (`app/nexus.py::_apply_operating_mode`) — now compute
and pass a real `WeightedExecutiveRecommendation`; the stale-proposal
expiry path is untouched since it always resolves "wait," which never
reaches the Gatekeeper at all. Chapter 66's Trade Gatekeeper remains
exactly as absolute as before this pass; Compliance's real veto
authority was never diluted into "one more weighted vote" — it's still
the Gatekeeper, not WEDE, that decides.

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
only, meaning it can never approve a trade or override another check on
its own, not that it's disconnected from the Gatekeeper (see the
Gatekeeper wiring bullet below, and Safety Systems above for the exact
verified boundary):**
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

**Built in a follow-up pass, per a Design Bible addendum requiring WEDE
to "feed recommendations into the Trade Gatekeeper, while remaining
advisory only":**
- **`app/gatekeeper.py::_weighted_executive_check()`** — a real 9th
  check in `evaluate_gatekeeper()`'s existing unconditional
  `all(checks)` list, the same authority as every other check: it can
  contribute to a rejection, never force an approval, never override or
  skip any of the other eight. Vacuously passes when no recommendation
  is supplied, the same honest pattern `_debate_check` already uses for
  a missing debate.
- **`app/executive.py::resolve_proposal()`** gained an optional
  `weighted_recommendation` parameter, passed straight through to
  `evaluate_gatekeeper()` — this function still never computes WEDE
  itself.
- **`app/state.py::submit_ceo_decision()`** and **`app/nexus.py::
  _apply_operating_mode()`** (the Assisted/Executive auto-resolve path)
  both now compute the real `WeightedExecutiveRecommendation`
  immediately before calling `resolve_proposal()`, so a manual CEO
  decision and an auto-resolution are gated by the identical advisory
  check — no safety signal that applies to a CEO click silently skips
  an auto-resolution. The auto-resolve path reuses the department
  opinions it already computed for the pre-existing `pause_trading`
  safety check (Chapter 66) rather than a second, redundant pass. The
  stale-proposal expiry path is untouched — it always resolves "wait,"
  which never reaches the Gatekeeper.

**Deliberate scope decisions, not gaps to silently fill later:**
Compliance and Innovation were not added as new `DepartmentOpinion`
roles just to give the brief's named seats something to weight (see
Primary Responsibilities); no Performance-Based Evolution loop persists
or decays influence over time (accuracy is read live, every request,
never accumulated — this codebase's own "no fake progression" rule);
the Institutional Rule Engine (Chapter 69 Part 3) is not wired into
this same pipeline — its Custom Rules attach to Part 1's secondary
`Account` objects, and live trade execution against those accounts
remains explicitly unwired (Part 1's own documented scope), so there is
no real trade flowing through an Account for IRE to evaluate against
yet; wiring it in would be architecturally hollow until account-scoped
execution exists.

**What's genuinely still unbuilt:** real sources for the six weighting
factors this pass couldn't honestly compute (Prediction Quality,
Current Expertise, Department Performance, Recent Reliability, Rule
Compliance, Specialization); a persisted evolution loop; recording the
Weighted Recommendation on `ExecutiveMeetingLogEntry` alongside the Raw
one it already stores permanently; and Institutional Rule Engine
enforcement in this same execution hierarchy (see the scope decision
above). Verified: mypy + ruff clean; the full backend suite (1138
tests, including 4 new real tests for the Gatekeeper check's pass/fail/
vacuous/non-overriding behavior) passing; two direct runtime smoke
tests against the real `GameState` singleton and `_apply_operating_
mode` confirming both production call sites produce a real, non-vacuous
WEDE evaluation as the Gatekeeper's 9th check; FastAPI `TestClient`
route registration + 404 handling; full save-module persistence
round-trip for the two new `SettingsState` fields; `tsc --noEmit`/
eslint/`npm run build` all clean; and a real Playwright test against
the live dev stack that boosts a research item to a genuine trade
proposal, opens the new panel, confirms all 9 departments render with
real influence data, and confirms switching the Weight Profile dropdown
live-previews a different published formula.
