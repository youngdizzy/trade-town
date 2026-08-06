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
| 67 | [TradeTown Operating System (TTOS)](chapter-67-tradetown-operating-system.md) | Phase 1 + Part 3's primary objective + Safety Settings core + Global Status Bar + Quick Action Dock + Command Palette implemented — a UX-architecture chapter, not a trading department. The Command Center's 34 tabs are grouped into 7 permanent TTOS sections (additive, no tab renames); a real, permanent, always-visible Global Emergency Stop now halts all new trading (including the CEO's own manual calls) behind a real confirmation dialog; two more real loss-limit circuit breakers (weekly/monthly, beyond the pre-existing daily one) are CEO-editable in the RISK tab; a real Global Status Bar (Risk/Company Health/Portfolio/Market/Automation/Deployed/Broker) is visible from every scene; a real Quick Action Dock lets the CEO cycle Automation Mode and jump straight to RISK/COMPANY/PORTFOLIO/EXECUTIVE from anywhere; a real Command Palette (Ctrl/Cmd+K) offers every real global action plus a "Go to X" jump for all 34 tabs, keyboard-driven, without duplicating the Pause/Resume/Emergency Stop controls that are already global elsewhere. Universal search, dashboard consolidation, and dockable/saved workspaces remain target design — several confirmed to have zero real backing feature anywhere in this codebase today (no broker integration, no Swing/Day Trading Mode, no Black Swan Protection, no Emergency Contacts) |

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
