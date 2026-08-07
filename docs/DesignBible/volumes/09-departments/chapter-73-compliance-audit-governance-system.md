# Chapter 73 — Compliance, Audit & Governance System (CAGS)

**Status:** Implemented as a real, read-only audit synthesis layer —
backend (`app/audit_log.py`, `app/routers/audit.py`) and frontend (a
real `COMPLIANCE` Command Center tab, `CompliancePanel.tsx`). The brief
asks for per-event fields (Broker, User, Credentials, Software Version)
and mutable incident-management workflows (open/resolved status,
corrective actions, security/encryption) this single-player, single-
broker, no-credential codebase has no real data or mechanism to back.
What shipped is real: every important event this company already
produces — CEO decisions (including real overrides), Gatekeeper/
Opportunity rejections, critical Risk Warnings, Discipline Reviews,
Emergency Stop and Defensive Mode activations, Black Swan Post-Event
records — synthesized into one searchable, chronological Audit Log,
computed fresh from already-real, already-persisted state, exactly the
way Chapter 61's Knowledge Graph and Chapter 65's Regime Reconciliation
already established for this kind of cross-cutting view. The
Institutional Time Machine addendum ships as this same Audit Log's own
chronological, steppable view — see Implementation Notes for why a full
arbitrary-instant state reconstruction ("what did the whole company
know at 3:47pm on Day 12") is explicitly cut.

## Executive Summary

The brief's thesis — "nothing inside TradeTown should happen without
explanation" — is already mostly true. This codebase's real discipline
(established long before this chapter) already records *why* almost
everything happened: every `GatekeeperRejection` carries real `reasons`;
every `CeoDecisionRecord` carries `agreedWithAi`; every
`DisciplineReview` carries real scored `factors`; every
`ExecutiveMeetingLogEntry` carries the real department-by-department
`opinions` that led to a recommendation. What was missing was not the
underlying accountability data — it was one place to search, filter, and
step through all of it together. That is the real, closeable gap CAGS
closes.

## Mission

Give the CEO one honest, searchable answer to "what happened, why, and
who was accountable" — built entirely from real, already-persisted
records this company produces during normal play, never a second,
parallel logging system, and never a fabricated field this codebase has
no data source for.

## Philosophy

Accountability is not a new mechanic bolted onto trading — it is the
trading system's own decision trail, made visible. Every check this
chapter's Audit Log surfaces (Gatekeeper's 9 named checks, Sentinel/
Guardian's risk gates, the Executive Board's department opinions) was
already real and already enforced before this chapter existed. CAGS
does not add new authority, new policies, or new enforcement — it adds
transparency over authority, policy, and enforcement that already runs
every tick.

## Responsibilities

**Owns:** the unified Audit Log (`AuditEntry`, synthesized from ten real
source types), the Incident view (a severity-filtered read of the same
log), the Governance Framework display (a disclosed, real description of
Gatekeeper's actual 9-check order plus where the Institutional Rule
Engine sits relative to it), the Compliance Overview aggregate, and CEO
Override tracking (`CeoOverrideRecord`, reading `CeoDecisionRecord.
agreedWithAi`, real since Chapter 70 Part 2).

**Does NOT own** (see Appendix E): any trade-approval authority
(`app/gatekeeper.py` — CAGS reads its real check results, never adds a
10th check or changes pass/fail logic), Risk Limits enforcement
(`app/risk_engine.py` — read-only), the Institutional Rule Engine's own
evaluation logic (`app/rule_engine.py` — CAGS surfaces its real output,
never recomputes a rule check), and Executive Board voting
(`app/executive_intelligence.py` — read-only). CAGS adds no new
decision-pipeline check anywhere in this pass.

## Ownership

Real code this chapter is authoritative over: `app/audit_log.py` (all
compute functions below), `app/routers/audit.py` (five read-only GET
endpoints). No new `GameSaveState` fields, no WS broadcast changes, no
`app/nexus.py` per-tick wiring — every function here is computed fresh
per request from state the game already persists, the identical
convention `app/knowledge_graph.py`, `app/whatif.py`, and
`app/regime_reconciliation.py` already established for a cross-cutting,
read-only synthesis.

Ten real, already-persisted source types this chapter reads from but
never duplicates or recomputes:

- **CEO Decisions** (`CeoDecisionRecord`, `app/executive.py`) — real
  `agreedWithAi` flag is the honest CEO Override signal (Chapter 70
  Part 2's own accuracy-tracking field, reused here for the identical
  meaning the brief asks for).
- **Executive Meeting Log** (`ExecutiveMeetingLogEntry`) — the real
  department-by-department `opinions` behind a recommendation.
- **Gatekeeper Rejections** / **Opportunity Rejections** — real blocked
  trades, with real `reasons`.
- **Risk Warnings** (critical severity only) — Sentinel/Guardian's real
  gates (`app/risk_engine.py`).
- **Discipline Reviews** (`app/discipline.py`) — real scored process
  reviews, `weak`/`reckless` tiers surfaced as incidents.
- **Emergency Stop** activation/resume (`app/emergency_stop.py`, via its
  real `CompanyMemory` record).
- **Defensive Mode** activation/deactivation (Chapter 72,
  `BlackSwanEventRecord`).
- **Crisis Briefings** (Chapter 72, via their real `CompanyMemory`
  record).
- **Rule Evaluations** (`app/rule_engine.py`'s `RuleCheckResult`, across
  every Account with enabled custom rules) — real `correctiveAction`
  text, reused verbatim, never invented.

## Inputs

`ceo_decisions`, `executive_meeting_log`, `gatekeeper_rejections`,
`opportunity_rejections`, `risk_warnings`, `discipline_reviews`,
`memory` (filtered to `alert`-category records for Emergency Stop/Crisis
Briefing), `black_swan_events`, `accounts` (for live Rule Engine
evaluation) — all already on `GameSaveState`, already capped by their
own existing `MAX_*` constants, so this chapter adds no new unbounded
growth anywhere.

## Outputs

- `GET /api/audit/log?category=&severity=&search=&limit=` — the
  unified, filterable, keyword-searchable Audit Log, newest first.
- `GET /api/audit/incidents` — the same log, filtered to
  `warning`/`critical` severity only.
- `GET /api/audit/governance` — the real, disclosed 9-layer Gatekeeper
  check order plus the Institutional Rule Engine's real (disconnected)
  position.
- `GET /api/audit/overview` — the Compliance Dashboard aggregate: open
  incident count, Executive Accuracy (reused from Chapter 70 Part 2,
  never recomputed), CEO Override count/rate, automation status (reused
  from the real Company Operating Mode), Defensive Mode status (Chapter
  72).
- `GET /api/audit/overrides` — every `CeoOverrideRecord`, the CEO's
  real disagreements with the AI's recommendation and their real
  resolved outcome once known.

## Internal Workflow

1. On request, `compute_audit_log()` walks the ten real source lists
   above, converts each real record into one `AuditEntry` (a real
   summary/detail string built from that record's own real fields,
   never templated filler), and sorts newest-first.
2. Query params (`category`, `severity`, `search`, `limit`) filter the
   already-built list server-side — a real, working search, not a UI
   placeholder over an unfiltered dump.
3. `compute_incidents()` is a pure filter over the same list
   (`severity != "info"`) — never a second, independently-built list
   that could drift from the Audit Log.
4. `compute_compliance_overview()` counts the filtered results and reads
   two already-real computed values (`compute_executive_accuracy_scores()`
   from Chapter 70 Part 2, `state.defensive_mode.active` from Chapter
   72) rather than inventing a new "compliance score" formula from
   scratch — see Decision Logic for the one genuinely new number this
   chapter does compute.

## Decision Logic

**AuditEntry severity** — reused directly where the source record
already has one (`RiskWarning.severity`, `Rule` corrective actions →
`warning`), or mapped from a real, disclosed table where it doesn't
(Gatekeeper/Opportunity rejections → `warning`; Emergency Stop/Crisis
Briefing/`reckless`-tier Discipline Reviews → `critical`; everything
else → `info`). Never a fabricated numeric risk score per event.

**Compliance Score** — the one new number this chapter computes: `100 -
min(60, 5 × open_incident_count)`, where `open_incident_count` is the
real count of `warning`/`critical` entries in the current Audit Log.
Disclosed and simple on purpose — this is a real, checkable formula over
a real count, not a fitted or backtested model, the same "conservative
but arbitrary, no real regulatory requirement behind it" honesty note
`RiskLimits` itself already carries. There is no separate "resolved
incidents" count — see Implementation Notes for why incident
*resolution* is not a real workflow in this codebase.

**Governance Framework** — not a new authority chain. It is the real,
disclosed order `app/gatekeeper.py::evaluate_gatekeeper()` already
checks in (confidence → risk manager alignment → CEO/AI agreement → AI
debate outcome → portfolio exposure → correlation → active risk
warnings → market intelligence quality → weighted executive
recommendation), displayed as a real governance layer list, plus one
honest disclosure: the Institutional Rule Engine (Chapter 69 Part 3) is
real but **not wired into this live chain** — its Custom Rules attach to
secondary Accounts that live trade execution doesn't route through yet
(Chapter 70 Part 3's own documented gap, unchanged by this chapter).

## Department Cooperation

**Receives (read-only):** Executive Board, Trade Gatekeeper, Risk
Engine, Discipline Chamber, Institutional Rule Engine, Emergency Stop,
Black Swan Intelligence.

**Provides:** the Audit Log, Incident view, Governance display,
Compliance Overview, and CEO Override history to the CEO-facing
dashboard. Provides nothing back into any decision pipeline — CAGS
cannot block, delay, or approve anything; it is a read-only observer,
the same standing Chapter 71's Economic Intelligence Center and Chapter
72's Black Swan Intelligence both hold before any future Gatekeeper
wiring.

## CEO Controls

None. CAGS is entirely read-only in this pass — no configurable
retention window (every source list already caps itself), no
CEO-editable incident status (see Implementation Notes for why a
mutable incident workflow isn't built), no audit-log weight profile.
Filtering (`category`/`severity`/`search`) is a query-time read
parameter, not a persisted setting.

## Learning System

None built this pass. The Audit Log is a real historical record, not a
grading loop — nothing here scores whether an incident "should have"
happened differently. Discipline Reviews (a real source this chapter
reads) already own that grading function; CAGS does not duplicate it.

## KPIs

The real Compliance Score (Decision Logic above) and the real CEO
Override rate (`overrideCount / totalDecisions` from
`CeoDecisionRecord`) are the only two published numbers. No fabricated
"transparency score" or "accountability index" — see the brief's own
Success Metrics list, most of which (Transparency, Traceability,
Decision Quality, Operational Integrity) already have a real analog
elsewhere in this codebase (Decision Grade, Executive Accuracy,
Discipline Tier) that this chapter reuses rather than re-deriving.

## Reports

None new. The Audit Log itself, freshly queryable at any time, is this
chapter's report — a fixed cadence (Daily/Weekly Compliance Brief) was
considered and cut: nothing about compliance state in this codebase
changes meaningfully faster than the CEO can just open the tab and look,
unlike Market/Economic/Black Swan Intelligence's real tick-driven
signals.

## Safety Systems

CAGS has no safety authority. It cannot activate Emergency Stop, cannot
override a Gatekeeper check, and cannot mutate any real risk/rule state.
It only ever reads.

## Dependencies

`app/executive.py`, `app/executive_intelligence.py`,
`app/gatekeeper.py` (read-only, for its real check *order*, not its
per-proposal results), `app/risk_engine.py`, `app/discipline.py`,
`app/emergency_stop.py`, `app/black_swan.py`, `app/rule_engine.py`,
`app/accounts.py`, `app/memory.py` — all read-only. No new external
dependency.

## Connected Features

`GET /api/audit/*` sits alongside `GET /api/knowledge-graph` and `GET
/api/market/regime-reconciliation` in the same "cross-cutting,
computed-fresh, read-only synthesis over real state" family. The
Institutional Time Machine (below) is this same family's chronological
presentation, not a separate data model.

## Future Expansion

A CEO-editable incident status workflow (open/acknowledged/resolved),
if this codebase ever gains a reason to distinguish "the CEO looked at
this" from "the CEO didn't" — not built here since no such distinction
exists anywhere else in this codebase today (the pattern established by
Chapter 67's Alert Center is "view, don't triage"). Wiring the
Compliance Score into the Trade Gatekeeper as an advisory-only check,
following the Chapter 70 Part 3 / Chapter 71 precedent, if a future
addendum explicitly asks for it.

## Company Principle

Every real decision this company makes already has a reason attached to
it somewhere in this codebase. CAGS's only job is to make sure the CEO
never has to go looking for it.

## Implementation Notes

**The honesty boundary, explicit and complete.** This codebase has one
player (no "User" identity distinct from "CEO"), one broker
(`PaperBroker`, 100% simulated, confirmed by Chapter 68's own
architecture doc), no credentials of any kind to protect, and no
per-event historical version tag. Given that, the brief's sections below
are cut outright rather than half-built:

- **Per-event Broker/User/Software Version fields** — cut from
  `AuditEntry` entirely rather than populated with a repeated constant
  ("SIMULATED" on every single row) or a fabricated identity. `Account`
  is a real per-entry field where the underlying record actually has
  one (a `CeoDecisionRecord`/`GatekeeperRejection` always trades the
  primary portfolio today — see Chapter 69 Part 1's own documented gap,
  "live trading execution in a chosen non-primary account is not wired
  here" — so this field would currently always read "Primary Portfolio"
  too; included anyway since it is at least real and non-constant once
  that gap closes).
- **Encrypted credentials / access permissions / Security section** —
  cut entirely. There is nothing to encrypt: no API keys, no stored
  password, no multi-user access-control model anywhere in this
  codebase (confirmed repeatedly across Chapters 68/71/72's own honesty
  boundaries).
- **A mutable Incident workflow** (open → acknowledged → resolved,
  corrective-action tracking as a CEO-editable field, "Lessons Learned"
  authored after the fact) — cut. Every incident this chapter surfaces
  is already fully resolved by construction the instant it's recorded
  (a blocked trade never executed; a Discipline Review is filed only
  after the trade already closed) — there is no real pending state to
  triage, so building a fake "mark as resolved" button would be
  decorative, not functional.
- **In-game Version History / searchable release notes** — cut. This
  codebase's real version history already lives in `CHANGELOG.md` and
  git history, both already the authoritative record of every Design
  Bible chapter, feature, and bug fix. Building a second, in-game copy
  risks exactly the kind of silent drift this Design Bible forbids
  elsewhere (see Chapter 61's own refusal to duplicate the Knowledge
  Graph's source data). Not surfaced in this pass.
- **The Institutional Time Machine's full point-in-time state
  reconstruction** ("what did the whole company know at any arbitrary
  instant" — market data, portfolio, positions, news, Knowledge Graph
  state, Company Memory, all simultaneously, for any moment in
  history) — this codebase takes no periodic full-state snapshots; only
  specific subsystems snapshot themselves on their own real cadence
  (`EconomicIntelligenceReport`/`BlackSwanReport`/
  `MarketIntelligenceReport`, once per real in-game evening;
  `DecisionVaultEntry`/`ExecutiveMeetingLogEntry`, once per real
  decision). Reconstructing "the exact state at 3:47pm on Day 12" for
  an arbitrary instant with no report or decision on file at that
  moment is not possible without inventing data. What ships instead is
  real: the Audit Log's own chronological order, already covering every
  timestamped moment this codebase actually recorded — a real history
  browser, honestly scoped to real recorded moments, not a claim of
  omniscient rewind. The CEO can step through it exactly as the brief
  asks ("chronologically... read-only... for Learning, Auditing,
  Debugging, Incident Investigation") — just never for a moment this
  codebase never actually captured.

**What IS real:** the ten-source Audit Log, keyword/category/severity
filtering, the Incident view, the disclosed real Governance Framework
order, the Compliance Score formula, and CEO Override tracking off the
real `agreedWithAi` field — all described in full under Decision Logic
above.

**Files changed this pass:** `app/schemas.py` (new
`AuditEventCategory`/`AuditEntry`/`GovernanceLayer`/
`ComplianceOverview`/`CeoOverrideRecord`); `app/audit_log.py` (new
module); `app/routers/audit.py` (new router, 5 endpoints); `app/main.py`
(router registration); `tests/test_audit_log.py`. Verification: `mypy
app/` clean, `ruff check app/ tests/` clean, full `pytest -q` passing,
zero regressions. No `app/state.py`/`app/nexus.py`/`app/ws_manager.py`/
`app/save_modules.py` changes — this chapter adds no persisted state.

**What's genuinely still unbuilt:** every item in the honesty-boundary
list above, plus a Trade Gatekeeper wiring for the Compliance Score —
all deliberate, all documented, none silently dropped.
