# Chapter 66 — Institutional Safety, Capital Protection & Failsafe Framework

**Status:** One real slice implemented (backend). The finding here
matches Chapter 65's own pattern: real, substantial safety machinery
already existed in this codebase, under different names — this
chapter's job was to describe it honestly rather than re-propose it,
then close the single precise gap its own research found: AI Consensus
Safety's `pause_trading` signal was real and already computed, but
nothing enforced it. That enforcement is now real, in both Assisted and
Executive mode. See [Volume 9's chapter template](README.md) for what
every section below must contain, and the Implementation Notes at the
bottom for exactly what was built.

## Executive Summary

Professional firms survive because they manage risk before pursuing
returns. **Researched first:** TradeTown already has a real, live,
mechanically-enforced daily circuit breaker (Sentinel/Guardian →
RiskWarning → Trade Gatekeeper), a real multi-stage pre-trade veto
pipeline with genuine final-authority-over-high-confidence-trades
behavior, and a real department-disagreement *detection* signal. What
does not exist: the brief's named 5-level Safety Pyramid / Capital
Defense Mode vocabulary and state machine, weekly/monthly-scoped
limits, enforcement of the disagreement signal against actual
execution, any CEO manual override control (pause/resume/lockdown), and
encrypted or CEO-facing backup/restore. This chapter says precisely
which is which.

## Company Philosophy

Survival comes first, profit comes second — already the operating
philosophy of every real safety mechanism found below, none of which
were built to chase upside.

## Primary Responsibilities

**Owns:** Capital Protection (already real, under Chapters 57/58's
names), Emergency Procedures (partially real — the daily halt is a real
emergency procedure, scoped narrowly), Failsafe Systems (the genuine
gap — no broker/API failure mode exists to fail-safe against, see
Ownership), Risk Escalation (partially real — significant-proposal
escalation exists; disagreement-triggered escalation does not),
Trading Suspension (real, daily-scoped only), Circuit Breakers (real,
under different names), Executive Emergency Controls (the genuine
gap — no CEO override control exists anywhere in this codebase today).

**Does NOT own** (see Appendix E): Trade Approval (the CEO's own
decision stays the CEO's), Strategy Development, Research, Position
Sizing's own quantity math (Chapter 57 — this chapter may recommend a
tighter limit, never compute a trade's size itself).

## Ownership

Real, already-shipped safety machinery this chapter must account for
honestly, organized by the brief's own vocabulary:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Circuit Breakers" | Sentinel (`app/risk_engine.py`'s `evaluate_sentinel_risk()`) + `DailyObjectiveStatus` (`compute_daily_objective_status()`) | Checks, in order: equity ≤ 0 → daily loss limit → daily profit target → daily trade count → lifetime drawdown → open-position count → single-position cap. First violation produces a `critical` `RiskWarning`. Real, live, checked every relevant tick. |
| "Trade Quality Override / final veto authority" | Chapter 58's Trade Gatekeeper (`app/gatekeeper.py`'s `evaluate_gatekeeper()`) | Eight checks, ALL must pass, run unconditionally whenever the CEO resolves a proposal: confidence, Sentinel's own risk vote, analyst agreement (&gt;50%), debate outcome, exposure, correlation (`MAX_CORRELATED_POSITIONS = 2`, not yet CEO-configurable), active risk warnings, market quality. A failed check means the order never places — **no CEO override is mechanically possible today**, which is precisely the brief's "Safety Framework always has final authority." |
| "AI Consensus Safety" (execution pauses on department disagreement) | `app/executive_intelligence.py`'s `compute_executive_recommendation()`, enforced by `app/nexus.py`'s `_apply_operating_mode()` | `compute_executive_recommendation()` sets `action = "pause_trading"` when 2+ departments actively oppose a stance, or Market Intelligence reads `avoid_trading`. **Now enforced**: `_apply_operating_mode()` checks this signal before every auto-resolution and keeps the proposal pending if it fires — in both Assisted and Executive mode, the same real safety-constraint precedent the existing cash-reserve check already established. The CEO's own Executive Voting popup already renders the real reason via its existing, generic `ExecutiveIntelligencePanel` — no new UI was needed. |
| "Broker Failsafe" | *(genuinely does not exist)* | `app/broker.py`'s own module docstring: no brokerage SDK import, no API key, no code path reaching a real execution endpoint anywhere in this codebase. `app/market_data.py` confirms the same for the data feed — only a `"mock"` provider is implemented. `Candle.data_status`'s `stale`/`error`/`no_data` literal values exist but are never produced or checked. There is no real broker or data feed to fail, so this cannot be honestly built as "monitoring an unreliable dependency" — it would have to be a structural placeholder against a dependency that doesn't exist yet. |
| "Disaster Recovery" | `app/persistence.py` | Real automatic backup-on-write (`SaveBackup` rows, `reason="periodic"`, capped at `MAX_PERIODIC_BACKUPS = 20`), real automatic recovery-on-corruption (`_migrate_dict()`/`_deep_merge_defaults()`, deep-merges a broken save onto real defaults before ever discarding it), real permanent retention of failure-triggered backups (`reason="pre_fresh_fallback"`, never deleted), real per-module fault isolation (SHA-256-hashed `SaveModule` rows, each in its own SAVEPOINT). **Genuinely missing:** no encryption, no CEO-facing restore/rollback endpoint or UI (a `SaveBackup` row can only be read by a developer querying the DB directly), no versioned "roll back N days" concept. |
| "Recovery Protocol" (root-cause review after a major loss) | Chapter 60's Discipline Chamber (`app/discipline.py`) | Real, permanent, per-trade process review (never outcome-graded) with a genuine `PostDecisionReview` — what went well, mistakes made, information overlooked, which specific dissenting analyst was overridden and turned out right. **Real overlap, different shape:** this is per-trade, not triggered by or scoped to a portfolio-level "major loss" event, and has no effect on subsequent trading behavior — each review is independent. |
| "Manual CEO Override" (pause/resume/lockdown) | *(genuinely does not exist)* | The CEO's Operating Mode selector (learning/assisted/executive) changes auto-resolution behavior, not a pause/resume/lockdown state. Grep-confirmed: no pause/resume/lockdown control anywhere in `NexusManager.ts` or any router. |

## Inputs

Every input a real future implementation could honestly use already
exists: `RiskLimits` (every field the brief's "CEO defines" section
asks for, except weekly/monthly-scoped and consecutive-loss fields —
see CEO Controls), `DailyObjectiveStatus`, `RiskWarning`,
`ExecutiveRecommendation.action`, `CompanyHealth.tier`,
`MarketQualityScore.tier`. **Not a real input anywhere:** any broker
connection/API-health signal (none exists to read — see Ownership), any
"cybersecurity" or "fraud detection" signal (named in the brief's
Future Expansion, not this codebase's real scope).

## Outputs

**Real today:** `DailyObjectiveStatus` (halted/haltReason/counts),
`RiskWarning` list, `ExecutiveRecommendation.action`. **Not built:** a
named Safety Level (1–5) or Capital Defense Mode (GREEN–BLACK) state,
an Emergency Event Report, a Circuit Breaker Log distinct from the real
`RiskWarning` history already kept, an Adaptation/Recovery-Protocol
history.

## Internal Workflow

**Real today:** proposal created → `evaluate_sentinel_risk()`/
`evaluate_guardian_exposure()` run every relevant tick → a critical
`RiskWarning` fires on the first real violation → CEO resolves (or, in
Assisted/Executive mode, `_apply_operating_mode()` auto-resolves per
`is_significant_proposal()`, unless the cash reserve or, now, AI
Consensus Safety keeps it pending — see below) →
`evaluate_gatekeeper()`'s eight checks run unconditionally → a failed
check blocks the order regardless of CEO intent. **Now real, closing
this section's own previously-named gap:** before auto-resolving,
`_apply_operating_mode()` computes the same real department opinions
`generate_department_opinions()` already builds and checks
`compute_executive_recommendation(...).action == "pause_trading"` — if
it fires, the proposal stays pending in BOTH modes, the exact same real
safety-constraint branch the cash-reserve check already used as
precedent.

## Decision Logic

**Real today:** every check listed under Ownership is a real, named,
transparent formula — never a hidden weighting, matching this
codebase's "no black-box composite" convention throughout. **Genuinely
not built:** any formula defining what "2+ departments disagree"
should actually do to execution (today it only sets a label nothing
reads), and any formula defining a graduated Capital Defense Mode from
the real signals that already exist (daily halt state, Company Health
tier, Market Quality tier) — today each of those signals is checked
independently, never combined into one company-wide posture.

## Department Cooperation

**Would receive from:** Chapter 58 (Trade Gatekeeper — the real veto
layer this chapter's own "Trade Quality Override" already is),
Chapter 57 (Position Sizing — the real `RiskLimits` fields any Safety
Level would tighten, never duplicate), Chapter 65 (Market Regime
Detection, this same batch — an `avoid_trading`/extreme-panic regime
read is one real signal a future Safety Pyramid would consume),
Chapter 60 (Discipline Chamber — the real per-trade review a
portfolio-level Recovery Protocol would sit above, not replace).
**Would send to:** the CEO (a unified Safety Level read, emergency
alerts), every trade-resolution path (a hard block when
`ExecutiveRecommendation.action == "pause_trading"` and no CEO override
is active).

## CEO Controls

| Control | Status |
|---|---|
| Daily Loss/Trade Limits | **Already real** — `maxDailyLossPct`, `maxTradesPerDay`, `dailyProfitTargetPct`, CEO-configurable today via `POST /api/risk-limits`, surfaced in the RiskPanel's Daily Trading Objectives card. |
| Weekly/Monthly Loss Limits, Max Consecutive Losses | **Not built** — only a daily-scoped loss limit and a lifetime drawdown cap exist; nothing weekly- or monthly-scoped, no consecutive-loss counter. |
| Portfolio Heat Cap | **Already real** — `portfolioHeatCapPct`, CEO-set and CEO-triggered only by design (Chapter 57's own honesty boundary: never system-triggered without the CEO opting in). |
| AI Disagreement Threshold | **Not built** — the underlying signal (`2+ departments opposing`) is hardcoded, not a CEO-configurable count. |
| Manual Override (pause/resume/lockdown/force research mode) | **Not built** — no such control exists anywhere in this codebase today; the closest real thing, Operating Mode, changes auto-resolution behavior, not a hard pause. |
| Automation Disable | **Partially real** — switching Operating Mode to `learning` already means every proposal waits for the CEO; there is no separate "disable automation" toggle distinct from that existing mode selector. |
| Correlation Limit | **Real but not CEO-configurable** — `MAX_CORRELATED_POSITIONS = 2` is hardcoded in `opportunity_gatekeeper.py`, a real, already-flagged gap in that module's own docstring. |

## Learning System

**Real today, at the per-trade level:** the Discipline Chamber's own
Learning System (see Chapter 60) already asks, per closed trade, what
went well and what to never repeat. **Genuinely not built:** any
learning loop over a *safety event* specifically (a halt, a
Gatekeeper rejection, a would-be pause_trading enforcement) — those
events aren't logged as a distinct category today, so there's nothing
to review in aggregate yet.

## KPIs

**Real and computable today:** Risk Limit Compliance (every `RiskWarning`
and halt is a real, checkable fact). **Not honestly computable:**
Maximum Drawdown as a distinct safety KPI (it's a real number already
tracked by `risk_engine.py`, but not surfaced as a dedicated Safety
Framework metric), Emergency Response Time, Circuit Breaker Accuracy,
Recovery Speed, Broker Stability (no real broker exists to measure
stability against), Safety Override Success (nothing to override yet).

## Reports

**Real today:** the RiskPanel's live Active Warnings list and Daily
Trading Objectives card function as an honest, always-current safety
report. **Not built:** a Daily Safety Report, Capital Protection
Report, Emergency Event Report, or Circuit Breaker Log as distinct,
named, persisted report objects — today's real safety state is
computed fresh and shown live, never archived as its own report series
the way `ExecutiveReview`/`CoachReport`/`StrategicReview` already are
for their own domains.

## Safety Systems

This chapter *is* the Safety Systems section for every other chapter in
this volume, so its own honesty here matters most: never claim a
circuit breaker exists where only a label does. `ExecutiveRecommendation.action
== "pause_trading"` (real signal, now real enforcement — see Internal
Workflow) and the Trade Gatekeeper's eight checks (real signal, already
enforced, unconditionally, with no CEO override possible) are now both
genuinely load-bearing, not just one of the two.

## Dependencies

**Every previous Design Bible chapter**, per the brief's own framing —
this framework has authority above every operational department, and
that authority is, today, split across Chapters 57 and 58's real
enforcement rather than centralized under one name. Chapter 65 (Market
Regime Detection, this same batch — a real future input, not yet
consumed). **A note on the brief's own named dependency:** the brief
lists "ALL PREVIOUS DESIGN BIBLE CHAPTERS," which is honest on its face
and needs no correction, unlike Chapter 65's brief.

## Future Expansion

Multi-Broker Failover, Automatic Broker Switching, Cloud Redundancy,
Cybersecurity Monitoring, Fraud Detection, and Institutional Compliance
Systems all require either a real broker/network dependency this
codebase's 100%-simulated broker does not have, or a scope (real money,
real infrastructure) explicitly outside this project's paper-trading
design — not invented or stubbed here, matching Chapter 61 and 65's own
confirmed-absence precedent for capabilities this codebase has no real
foundation for yet.

## Company Principle

TradeTown will always choose disciplined survival over reckless growth
— and, per this chapter's own research, it already mostly does, under
names like Sentinel, Guardian, and the Trade Gatekeeper. Department
disagreement no longer just labels itself: it pauses execution, the
same real discipline every other circuit breaker in this chapter
already respects. What remains is naming that discipline in one place
and giving the CEO a manual override that does not yet exist.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written (not assumed):** a real, live, mechanically-enforced daily
circuit breaker (Sentinel → RiskWarning → Gatekeeper, no CEO override
possible, self-clearing at the next sim day); a real multi-stage
pre-trade veto pipeline (Position Sizing's cash-reserve floor,
Opportunity Gatekeeper's pre-proposal veto, Trade Gatekeeper's
eight-check final authority) that already **is** the brief's "Trade
Quality Override"; a real, working automatic backup/recovery system
with no encryption and no CEO-facing restore; and a real per-trade
root-cause review (Discipline Chamber) that doesn't yet scale to a
portfolio-level event. None of this needed to be rebuilt, and this
chapter does not claim otherwise.

**What was actually built (AI Consensus Safety enforcement — backend
only, this chapter's real slice):** the one precise, high-value gap
this chapter's own research found — a real department-disagreement
*detection* signal (`ExecutiveRecommendation.action == "pause_trading"`)
existed but was completely inert; nothing checked it before a proposal
auto-resolved. `app/nexus.py`'s `_apply_operating_mode()` now computes
the same real department opinions `generate_department_opinions()`
already builds and keeps a proposal pending whenever
`compute_executive_recommendation(...).action == "pause_trading"` fires
— in BOTH Assisted and Executive mode, the same "real safety constraint,
not a mode-dependent judgment call" precedent the existing cash-reserve
check already established (a real, honest change to what Executive
Mode's own docstring used to claim: it no longer auto-resolves
*everything*, only everything not caught by a real safety constraint).
No new frontend code was needed: the CEO's existing Executive Voting
popup already renders any `ExecutiveRecommendation` generically via
`ExecutiveIntelligencePanel`, including `pause_trading`'s own real
action label and reason text, so a now-pending proposal is already
fully explained the moment the CEO opens it. Verified: 3 new backend
tests (an otherwise non-significant proposal stays pending under an
`avoid_trading` regime in Assisted mode, the same proposal stays
pending in Executive mode too — the real behavioral change — and a
normal regime still auto-resolves in Executive mode, confirming the
gate is regime-specific, not a blanket block), `mypy`/`ruff` clean,
full backend suite 1102/1102 passing.

**What's genuinely still not built, and what a real future
implementation would need to design first (per Appendix G's Permanent
Development Policy):** a named Safety Level or Capital Defense Mode
state machine combining the real signals that already exist
independently (daily halt, Company Health tier, Market Quality tier);
weekly/monthly-scoped loss limits and a consecutive-loss counter; a CEO
manual pause/resume/lockdown control (currently absent in both backend
and frontend, and not overlapping with this pass's own work, which
enforces an existing automatic signal rather than adding a manual one);
a CEO-facing backup restore path. Broker/API failsafe monitoring is
explicitly **not** a buildable slice — there is no real broker or data
feed with a failure mode to monitor, and fabricating one would violate
this project's own no-fabrication discipline.
