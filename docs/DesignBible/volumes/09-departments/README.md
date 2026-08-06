# Volume 9 — Departments

**Status:** Outline; chapter template defined; no chapters written yet.
See [the master Table of Contents](../../README.md).

Every feature becomes a Design Bible chapter here. A chapter is not a
redesign of the feature — it is the feature's existing systems,
workflows, and philosophy, reorganized into one consistent institutional
format so a new engineer can read any chapter and immediately understand
how that department thinks, what it owns, what it doesn't, and how it
connects to everything else.

## The chapter template

Every chapter in this volume must contain, in this order:

1. **Executive Summary** — why this feature exists, what business
   problem it solves, how it strengthens TradeTown.
2. **Mission** — one clear purpose.
3. **Philosophy** — how this department thinks (mindset, not mechanics).
4. **Responsibilities** — what this feature owns, and, explicitly, what
   it does **not** own (prevents overlap with other departments — cross-
   check against Appendix E, the Decision Authority Matrix).
5. **Ownership** — the real code modules, schemas, and Command Center
   surfaces this chapter is authoritative over.
6. **Inputs** — every real input this feature requires.
7. **Outputs** — everything this feature produces.
8. **Internal Workflow** — Input → Analysis → Decision → Validation →
   Execution → Learning, documented against the real code path, not an
   idealized one.
9. **Decision Logic** — exactly how decisions are made: Evidence,
   Confidence, Probability, Expected Value, Historical Memory, Company
   DNA, Risk, and the priority order between them when they conflict.
10. **Department Cooperation** — how this feature communicates with
    Executive Intelligence, Portfolio Intelligence, the Risk Office, the
    Knowledge Graph, Research, Market Intelligence, and CEO Headquarters.
    No isolated systems.
11. **CEO Controls** — every configurable setting this feature exposes
    (confidence threshold, evidence threshold, automation level,
    research depth, approval requirements, risk limits, simulation
    depth, ...).
12. **Learning System** — how this feature continuously improves itself;
    every completed task should make future decisions better.
13. **KPIs** — measurable performance metrics (decision accuracy,
    research quality, risk reduction, expected value, capital
    efficiency, execution quality, knowledge growth, ...).
14. **Reports** — every report this feature produces: daily, weekly,
    monthly, executive, historical, audit.
15. **Safety Systems** — validation, override authority, failure
    handling, emergency protections, risk controls.
16. **Dependencies** — exactly which other features this one depends on.
17. **Connected Features** — real and planned integrations with other
    chapters, including future Volume 9 chapters not yet written.
18. **Future Expansion** — how this feature scales into v0.9, v1.0, real-
    money trading, multiple brokers, and a much larger AI workforce.
19. **Company Principle** — the one-sentence principle this department
    would state as its own creed (see e.g. the Executive Decision
    Simulator's "TradeTown never trades because it hopes...").
20. **Implementation Notes** — the real honesty boundary: what's
    genuinely built, what's deliberately cut and why, and where the real
    code lives.

## Chapters

| Feature | Title | Status |
|---|---|---|
| 54 | Decision Memory System (Decision Vault) | Pending — real backend + frontend already shipped, chapter not yet written |
| 55 | Executive Decision Simulator (War Room) | Pending — real backend + frontend already shipped, chapter not yet written |
| 56 | Enterprise Portfolio Intelligence | Pending — real backend + frontend already shipped, chapter not yet written |
| 57 | [Institutional Position Sizing & Capital Deployment Engine](chapter-57-position-sizing-capital-deployment.md) | Fully implemented (backend `app/position_sizing.py` + frontend WARROOM/RISK surfacing) |
| 58 | [Institutional Trade Filter & Opportunity Gatekeeper](chapter-58-trade-filter-opportunity-gatekeeper.md) | Fully implemented (backend `app/opportunity_gatekeeper.py` + frontend EXECUTIVE/RISK surfacing) |
| 59 | [Capital Priority & Opportunity Cost Engine](chapter-59-capital-priority-opportunity-cost.md) | Fully implemented (backend `app/capital_priority.py` + frontend EXECUTIVE/RISK surfacing) |
| 60 | [Institutional Portfolio Rebalancing & Adaptive Capital Rotation](chapter-60-portfolio-rebalancing-capital-rotation.md) | Chapter written — target design; no implementation yet |
| 61 | [Institutional Knowledge Graph & Company Memory Engine](chapter-61-knowledge-graph-company-memory.md) | Substantially implemented — Knowledge Graph extension, Pattern Detection Sensitivity, both Knowledge Retention Rules slices, and the Knowledge Quality Score all shipped backend + frontend; 5 minor CEO Controls rows (Archive Policies, Learning Sensitivity, Memory Weighting, Historical Search Depth, Knowledge Validation Rules) remain target design |
| 62 | [Institutional Innovation Lab & Continuous Improvement Engine](chapter-62-innovation-lab-continuous-improvement.md) | Partially implemented — Knowledge Integration, Innovation Budget CEO control, and Experiment Tiering all shipped backend + frontend; Pilot Duration and Automatic Promotion Rules remain target design |
| 63 | [Executive Performance & Company Health Engine](chapter-63-executive-performance-company-health.md) | Substantially implemented — Company Health Score, Company Score, Department Scorecards, and the monthly Executive Review predate this chapter; Company Health tier thresholds (CEO control) and multi-period Benchmarking now shipped backend + frontend; Early Warning consolidation remains target design |
| 64 | [Executive Strategic Planning & Goal Management Engine](chapter-64-executive-strategic-planning-goal-management.md) | Fully implemented — CEO-authored Goals against one of four real metrics with real progress tracked every tick, Milestone Tracking (25/50/75% checkpoints), the Executive Priority Engine (real urgency ranking), Resource Allocation (a recommend-only attention share normalized from those same scores), and the Strategic Review Cycle (a real monthly report over goal progress), all shipped backend + frontend |
| 65 | [Market Regime Detection & Adaptive Strategy Engine](chapter-65-market-regime-adaptive-strategy.md) | One real slice implemented (backend + Company tab card) — real regime detection already substantially built (twice over, under `app/market_environment.py` and `app/market_intelligence.py`, the latter with a real Regime Confidence Score); the two are now reconciled into one CEO-facing aligned/diverging read plus a read-only cautious/normal/opportunistic posture recommendation; Adaptive Strategy Profiles and Automatic Adaptation remain target design |
| 66 | [Institutional Safety, Capital Protection & Failsafe Framework](chapter-66-institutional-safety-capital-protection.md) | One real slice implemented (backend) — real circuit-breaker and veto machinery already substantially built (Sentinel/Guardian, Position Sizing, the Trade Gatekeeper); AI Consensus Safety's real but previously-inert pause_trading signal is now enforced in both Assisted and Executive mode; the named Safety Pyramid vocabulary and CEO manual override controls remain target design |
| 67 | [TradeTown Operating System (TTOS)](chapter-67-tradetown-operating-system.md) | Phase 1 + all of Part 3's buildable scope implemented — a UX-architecture chapter, not a trading department. The Command Center's 34 tabs are grouped into 7 permanent TTOS sections (additive, no tab renames); a real, permanent, always-visible Global Emergency Stop now halts all new trading (including the CEO's own manual calls) behind a real confirmation dialog; two more real loss-limit circuit breakers (weekly/monthly, beyond the pre-existing daily one) are CEO-editable in the RISK tab; a real Global Status Bar (Risk/Company Health/Portfolio/Market/Automation/Deployed/Broker) is visible from every scene; a real Quick Action Dock lets the CEO cycle Automation Mode and jump straight to RISK/COMPANY/PORTFOLIO/EXECUTIVE from anywhere; a real Command Palette (Ctrl/Cmd+K) offers every real global action, a "Go to X" jump for all 34 tabs, and real search across employees/trades/research/Company Memory (Universal Search, built into the same overlay rather than a second one); every toast now carries a real priority tier (critical/high/normal), with critical Risk Warnings and Emergency Stop activation now producing sticky, non-auto-dismissing interrupts previously missing entirely; and a real Executive Alert Center (opened from the Command Palette) lets the CEO browse every recorded toast by tier — without duplicating the Pause/Resume/Emergency Stop controls that are already global elsewhere. QuickView and OverviewPanel (two of the three independently-built "company overview" dashboards) now share one canonical `useDashboardData()` hook instead of independently recomputing the same real risk/decision derivations, with zero data points lost either direction — a data-layer consolidation, not a visual merge, since a compact glance and a full landing tab serve genuinely different real contexts. The Command Palette now reaches all 6 of this app's real standalone overlays (added Newspaper and Campus Map, previously unreachable from it), and a real "AI Academy" vs. "ACADEMY" tab naming collision in OverviewPanel is resolved by relabeling, not by renaming any tab identifier (which stays deferred — it would ripple `clickTab()`'s exact-name lookups across the whole Playwright suite). Full dashboard consolidation (folding in BrainRoomHud's own pull-up), folding all 6 overlays into TTOS's own 7-section structure, the OPS tab's own section-placement collision, and dockable/saved workspaces remain target design — several confirmed to have zero real backing feature anywhere in this codebase today (no broker integration, no Swing/Day Trading Mode, no Black Swan Protection, no Emergency Contacts) |
| 70 | [Executive Board & CEO Intelligence System](chapter-70-executive-board-ceo-intelligence-system.md) | Chapter written in three parts. **Part 1** remains not implemented: a real monthly CIO review (`ExecutiveReview`), a real permanent per-decision meeting log (`ExecutiveMeetingLogEntry`), a real merged executive-priorities list, a real Company Health/Score breakdown covering 6 of the brief's own 9 Company Health Review categories, and Chapter 67's Global Status Bar/Alert Center/`useDashboardData()` already surfacing 7 of the brief's own 10 Executive Command Center metrics live today. 4 of 12 named board seats are filled by real agents with real (if not exactly matching) "Chief" titles. Genuinely unbuilt: the other 8 board seats, Daily/Quarterly meeting cadence, automatic Emergency Board Meeting triggers, a general-purpose non-trade Decision Center, per-executive scorecards, and a CEO Assistant AI. **Part 2 (Executive Consensus Meter) is now implemented:** on top of the pre-existing `DepartmentOpinion` + `compute_executive_recommendation()` live consensus meter, Modify and Delegate are now real CEO decision actions (`app/executive.py::modify_proposal()`, `submit_ceo_decision(delegated=True)`), a real synthesized Disagreement Analysis (`_build_disagreement_summary()`) and an Executive Accuracy Score (`compute_executive_accuracy_scores()`, scored only against real closed-trade outcomes, never a hypothetical) were added, and the What-If Simulation Lab's numbers now merge into one API response. Still genuinely unbuilt: a distinct Consensus % apart from average confidence, Institutional Risk/Opportunity Scores, structured per-opinion Evidence/Concerns/Benefits/Risks fields, and accuracy scoring for the 5 departments that never cast a directional stance. **Part 3 (Weighted Executive Decision Engine) is now implemented, and now feeds the Trade Gatekeeper while remaining advisory only:** `app/weighted_decisions.py` (new) computes a real, published per-department `DepartmentInfluence` (accuracy × market × preset/custom multipliers, each shown in a generated reasoning string) and a `WeightedExecutiveRecommendation` distinct from the pre-existing Raw Vote, across all 8 named Weight Profiles. Honestly scoped to the only two of the brief's eight named inputs with a real source — Historical Accuracy and Market Conditions — the other six are not fabricated. A follow-up Design Bible addendum ("The Executive Board recommends. The Trade Gatekeeper decides.") required WEDE to feed the Gatekeeper directly: `app/gatekeeper.py` gained a real 9th unconditional check (`_weighted_executive_check()`) with the exact same authority as every other check — can contribute to a rejection, can never force an approval or override any other check — wired into both real paths that can open a position (`app/state.py::submit_ceo_decision()` for a manual CEO decision, `app/nexus.py::_apply_operating_mode()` for Assisted/Executive auto-resolution). Verified: a favorable WEDE read cannot rescue a trade a failing Decision Confidence check would otherwise reject. Chief Compliance/Innovation Officer were deliberately not invented as new department-opinion roles, and no Performance-Based Evolution loop persists or decays influence over time. The Institutional Rule Engine (Chapter 69 Part 3) remains deliberately unwired into this pipeline — its Custom Rules attach to secondary Accounts that live trade execution doesn't route through yet. |
| 71 | [Economic Intelligence Center](chapter-71-economic-intelligence-center.md) | Implemented as a real cross-signal synthesis layer, backend only. This codebase has no real macroeconomic data source anywhere (no API keys, no live feed), so the brief's Central Bank Intelligence, real Economic Calendar, Global Event Intelligence, real macro indicators/forecasts, named-sector Impact Engine, and Scenario Planning are all explicit, documented cuts — not fabricated. What's real: a new `EconomicHealthScore` (five named, published factors — Regime Favorability, Market Quality, News Risk, Correlation Clustering, Concentration — reused from Chapter 65/Market Intelligence/Chapter 56, never recomputed), an `EconomicConfidenceRead` (confidence, evidence quality, named supporting/contradicting evidence, a computed alternative-outcome statement), and a Market Narrative Engine that diffs each day's real read against the last stored report and cites only real, computed deltas — never invented causality like "the Fed cut rates." A Daily Economic Intelligence Brief records once per real in-game evening (`app/economic_intelligence.py`, `GET /api/market/economic-intelligence` + `.../reports`). Deliberately not a 10th Executive Board vote and not wired into the Trade Gatekeeper this pass — see the chapter's own Implementation Notes for why and for the Chapter 70 Part 3 precedent that would govern doing so later. |
| 72 | [Black Swan Intelligence & Resilience System](chapter-72-black-swan-intelligence-resilience-system.md) | Implemented as a real stress-and-resilience synthesis layer, backend only, in two parts. **Part 1:** this codebase has no historical black-swan dataset, no real broker connection, and no macro/sector/credit data (Chapters 68/71 already established this), so the brief's named historical scenarios (2008, 2020, 1987, Dot-Com), Banking Failure/Pandemic/Cyberattack scenario types, a calibrated "probability," live Broker Resilience monitoring, and 8 distinct named Playbooks are all explicit, documented cuts. What's real: a new `EarlyWarningScore` (eight named, published factors — Active Risk Warnings, Market Stress, Volatility, Liquidity, Correlation Breakdown, Regime Divergence, News Severity, Macro Instability — reused from Risk Engine/Market Intelligence/Portfolio Intelligence/Chapter 65/Chapter 71, never recomputed) driving a new named `BlackSwanRiskTier` (GREEN→CRITICAL — the exact gap Chapters 66 and 70 each already flagged and left unbuilt); portfolio-wide Stress Tests (-10/-20/-35/-50/-70%, against any real Account) and four mechanically-named Scenario Simulations extending `app/whatif.py`'s own real volatility-scaled shock convention from one trade to the whole book; a CEO-controllable Defensive Mode that tightens real `RiskLimits` and pauses new trade generation but never auto-closes a position (`app/portfolio_intelligence.py`'s own "never auto-corrected without the player" principle, upheld exactly); a real Elevated Risk Response Playbook; and Crisis Briefing / Post-Event Analysis records that write real, permanent Company Memory and Knowledge Graph entries. **Part 2 (Institutional Survival Score)** adds a real 0-100 score with a published A+–F grade, reusing three of Part 1's own Early Warning factors (Correlation Breakdown, Liquidity, Active Risk Warnings, inverted) plus five new real factors (Cash Reserves, Concentration Risk, Drawdown Exposure, Black Swan Readiness, Stress Test Survival); "Leverage" and "Counterparty Risk" are cut outright (no margin or broker-counterparty concept exists anywhere), and no "Estimated Survival Probability" is fabricated. Both parts: `app/black_swan.py`, `GET/POST /api/black-swan/*`. Deliberately not wired into the Trade Gatekeeper this pass — see the chapter's own Implementation Notes. |

Every other real, shipped system in this codebase (Executive Intelligence
Network, Trade Gatekeeper, Discipline Chamber, Reasoning Lab, Reflection
Chamber, Company Constitution, CEO Treasury, AI Academy, and the rest —
see `CHANGELOG.md` for the full list) is a pending chapter here too, not
yet listed individually. This table grows one row at a time as each
chapter is actually written — it is not a claim that only three features
exist.

## Note on Features 54–56 specifically

An earlier request asked these three chapters be written to match "the
same documentation style used by Features 57–67." No Feature 57–67
chapters exist anywhere in this codebase or its git history — this was
checked directly (a full-text search for "Feature 57" through "Feature
67" across every `.md`/`.py`/`.ts`/`.tsx` file, and a check of every
branch on the remote) before writing this note, rather than assumed.
Features 54–56 will instead be the **first three chapters written**
under this volume's template above, once volume-by-volume writing
reaches Volume 9 — there is no existing higher bar to match yet; these
three chapters set it.
