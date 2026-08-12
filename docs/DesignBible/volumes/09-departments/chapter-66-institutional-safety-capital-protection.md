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

## Addendum — Behavioral Circuit Breaker (Trading Psychology & Discipline, Piece A)

**Status:** Real, implemented as the Gatekeeper's tenth check
(`app/gatekeeper.py::_behavioral_check`, `app/behavioral_risk.py`).

**Origin.** The CEO shared a trading-psychology video's five principles
(consistency over strategy-switching, losses as normal distribution
variance, no revenge trading, emotions-are-normal-but-emotional-action-
is-the-risk, the plan as a capital-protection constraint system) and
asked for the useful principles to be extracted, validated against
TradeTown's existing risk architecture, and implemented only where they
close a real gap — never taken as guaranteed financial truth. Research
found this codebase's own `app/constitution.py` (Article V) had already
named the exact gap this piece closes: *"this codebase has no real
signal for literally re-entering a position out of anger after a loss...
building one would mean inventing behavior-classification infrastructure
this session's whole discipline exists to avoid."* This addendum closes
that named gap without inventing anything unverifiable.

**The honesty boundary — this system detects observable behavioral
risk. It does not claim to detect human emotion.** Every signal is
computed purely from real, already-persisted trade data (symbol,
quantity, price, timestamps, realized P&L) — never an AI judgment of
"is this angry trading."

**The five real signals** (`compute_behavioral_check()`):

1. **Recent loss** — the most recently closed trade in the company's
   real `trade_history` has `pnl < 0`.
2. **Rapid re-entry** — the candidate proposal is being evaluated within
   `behavioral_cooldown_minutes` (CEO-configurable, default 60) of that
   loss closing.
3. **Same/similar instrument** — the candidate's symbol matches the
   loss's symbol.
4. **Loss-driven size increase** — the candidate's dollar size
   (`quantity × price`) exceeds this account's own trailing average
   trade size (the last `SIZE_BASELINE_TRADES` trades, excluding the
   loss itself) by more than `behavioral_size_increase_threshold_pct`
   (CEO-configurable, default 50%). A self-relative baseline, never a
   hard-coded dollar figure — a proposal larger than recent normal but
   within the CEO's own configured risk limits, on a different
   instrument, well outside the cooldown window, is a **legitimate**
   sizing choice, not a behavioral signal.
5. **Repeated rapid re-entry** — a count of how many times signals 1+2
   have already co-occurred across the trailing trade history (reusing
   the same real timestamps every other signal here reads) — real
   corroborating evidence of a pattern, not a new data source.

**Corroboration requirement.** Directly answers the CEO's own review:
*"Do NOT define revenge trading as simply 'loss followed by another
trade.' A legitimate setup immediately following a loss must remain
possible."*

- **`clear`** — no recent loss, enough time has passed, or (loss +
  rapid re-entry) with no corroborating signal.
- **`warning`** — recent loss + rapid re-entry, but no same-instrument
  or loss-driven size-increase signal — informational only, never
  blocks.
- **`triggered`** — recent loss + rapid re-entry + at least one
  corroborating signal — fails this one Gatekeeper check for this one
  proposal.

Timing alone can never reach `triggered`. A differently-symboled,
normally-sized (or larger-but-limit-compliant) trade moments after a
loss is explicitly allowed through untouched — proven by
`tests/test_behavioral_risk.py`'s and `tests/test_gatekeeper.py`'s
false-positive matrix, not just asserted.

**Reuses the existing Gatekeeper — no second, parallel enforcement
path.** `_behavioral_check()` is the tenth entry in
`evaluate_gatekeeper()`'s existing pure-AND `checks` list (composed via
`approved = all(c.passed for c in checks)`, the same structural
guarantee every other check already has). A `triggered` read fails only
this proposal's behavioral check — every other check still runs
independently, and a rejection is automatically recorded as a real,
auditable `GatekeeperRejection` (no new plumbing needed). Because it
rides the Gatekeeper, it inherits the Gatekeeper's own non-bypassable
guarantee: no Trading Mode (Day/Swing/Hybrid) or Operating Mode
(Learning/Assisted/Executive) can skip it — verified directly by
`tests/test_behavioral_circuit_breaker_integration.py`, which resolves
the same revenge-shaped proposal through both real call sites
(`app/nexus.py`'s `_apply_operating_mode` auto-resolution and a real
CEO click via `GameState.submit_ceo_decision`) and confirms an identical
rejection either way.

**Ambient dashboard read.** The same signal logic runs once per tick
with no candidate proposal (`candidate=None`), reporting whether the
account is currently inside a post-loss cooldown window — capped at
`warning`, since the two corroborating signals need a real candidate to
compare against and can never reach `triggered` without one. Persisted
on `GameSaveState.behavioral_circuit_breaker`, broadcast over the WS
tick, and shown in the Command Center's TRADINGMODES tab next to Losing
Streak Protection — the same convention `daily_circuit_breaker`/
`losing_streak` already established, no new dashboard surface.

**Account-Awareness.** The CEO's review raised a real concern: a loss in
one Account should not silently influence unrelated Accounts unless a
company-wide rule says so. Checked against Chapter 69 Part 1's own
confirmed finding: live trade execution today only ever touches the
single primary company `PaperPortfolio` — no secondary Account
(IRA/Business/Prop Firm/Family) has live-execution routing to cross-
contaminate. This check reads that one real portfolio by construction,
not by new design choice, and adds no new Account-scoping plumbing. If
per-Account live execution is ever built, this check must be re-scoped
to run per-Account — tracked as a V2 follow-up, not assumed away.

**Deferred (named, not silently skipped):** repeated-rejected-setups-
retried, repeated trading-mode-switching, and "recover the exact dollar
amount lost" — each needs either data this codebase doesn't capture
per-proposal today or materially more design work.

**What remains `NOT_TRACKABLE_YET`:** nothing here claims to solve Plan
Adherence (stop-loss/take-profit/entry-condition/exit-condition/
confluence tracking) — that honest boundary stays entirely with the
separately-scoped Process Adherence Score piece, not touched here.

**Verified:** `tests/test_behavioral_risk.py` (19 pure-function cases —
the full false-positive/true-positive matrix, boundary conditions,
degenerate inputs, ambient-mode-never-triggers), `tests/test_gatekeeper.py`
(extended — the tenth check composes correctly into the pure-AND, a
triggered read fails the whole verdict while every other check still
passes independently), `tests/test_behavioral_circuit_breaker_integration.py`
(3 real `GameState`-level cases proving both real call sites end-to-end,
using a loss seeded via `app/portfolio.py`'s own real
`open_position()`/`close_position()`, not a fabricated record), full
backend suite (1496/1496 passing, zero regressions to Daily Circuit
Breaker/Emergency Stop/Losing Streak/the other nine Gatekeeper checks),
`mypy`/`ruff` clean, `tsc -b --noEmit`/`npm run lint` clean.

## Addendum — Process Adherence Score (Trading Psychology & Discipline, Piece C)

**Status:** Real, implemented (`app/process_adherence.py`, `GET
/api/executive/decisions/{decisionId}/process-adherence`).

**Origin and honesty boundary.** The third piece of the CEO-requested
trading-psychology roadmap (see this chapter's own Piece A addendum
above for the roadmap's origin). The CEO's own request named a literal
"Plan Adherence Engine" — comparing PLANNED vs. ACTUAL entry/exit
conditions, stop-loss/take-profit placement, position size, and
confluence requirements. Checked directly against this codebase before
any code was written: none of that exists. `app/gatekeeper.py`'s own
module docstring already names the exact gap — no stop-loss/take-profit
order concept, no entry/exit condition model, no confluence checklist
anywhere in this paper-trading engine. Building a literal Plan Adherence
Engine would mean fabricating data this architecture has no real source
for. The CEO's own review, given this exact constraint up front, asked
for a narrower, honestly-bounded **Process Adherence Score** instead —
scored ONLY from information this architecture can actually verify,
with every unbuildable component reported as `NOT_TRACKABLE_YET`, never
scored as pass, never as fail, never silently omitted.

**The real, verifiable checks** (`compute_process_adherence()`), every
one reusing data this codebase already computes for a different real
reason — never a second, parallel computation:

1. **Gatekeeper checks** — every real `GatekeeperCheck` on the
   decision's own `TradeDecision.gatekeeper_verdict.checks` (Chapter
   66's own Trade Gatekeeper, now ten checks after Piece A's Behavioral
   Circuit Breaker), surfaced exactly as produced — one row per real
   check, so a rejected decision honestly shows which specific check(s)
   failed (Decision Confidence, Risk Manager Alignment, Portfolio
   Exposure, Correlated Positions, Active Risk Warnings, and so on).
   This is where "risk compliance" from the CEO's own request lives —
   the Gatekeeper's own risk-related checks are the real, already-
   computed risk-compliance signal; a second, independently-derived
   "risk %" would only ever restate what these checks already say,
   since every executed position is structurally sized at or under the
   CEO's configured risk ceiling by construction (`app/executive.py`'s
   `resolve_proposal()` always clamps to
   `min(risk_per_trade_pct, max_position_pct)` of equity before a
   position can open) — a real, verified, always-true fact for anything
   that actually executed, not a fabricated discriminator.
2. **Discipline Process Quality** — reuses the Discipline Chamber's own
   real `DisciplineReview.tier` (`app/discipline.py`) by `decision_id`,
   never re-scored: `exemplary`/`sound`/`adequate` passes,
   `weak`/`reckless` fails. `NOT_TRACKABLE_YET` until the position
   closes (the Discipline Chamber only ever reviews a finished trade).
3. **Trading Mode Compliance** — reuses the trade's own real
   `trading_style` tag (Chapter 75's `assign_trading_style()`, the
   single real assignment point). A genuine, checkable violation exists
   here: a `"day"`-tagged position held past
   `DAY_TRADING_MAX_HOLD_MINUTES` (1440 — the same same-day bar
   `flatten_day_positions()` enforces) is real evidence the Day Trading
   discipline was not honored for that specific trade. Every other
   tagged case passes by construction; an untagged (pre-Chapter-75)
   trade is `NOT_TRACKABLE_YET`.
4. **Stop-Loss Placement, Take-Profit Placement, Entry Condition Match,
   Exit Condition Match, Confluence Requirements** — always, honestly,
   `NOT_TRACKABLE_YET` for every decision, with the required disclosure
   verbatim: *"Full plan adherence requires future execution/order-plan
   infrastructure this paper-trading engine does not have yet."*

**Scoring.** `score_pct` = `passed_count / verified_count * 100`, where
`verified_count = passed_count + failed_count` — `not_trackable_count`
is disclosed separately and never folded into either side. `score_pct`
is `None` (never 0%, never omitted) whenever `verified_count` is 0 — a
real case that occurs for a WAIT decision (nothing ever reached the
Gatekeeper) or a decision predating this feature. Computed fresh on
every real request (`GET /api/executive/decisions/{decisionId}/process-
adherence`), never persisted — the same convention Chapter 62's
Certification and this chapter's own What-If Simulation already
established, so a Discipline Review filed after this was first read
automatically shows up the next time it's read.

**Future TradeProposal/execution-layer fields a real Plan Adherence
Engine would need (documented, explicitly NOT built here):**

- `TradeProposal.plannedStopLossPrice` / `plannedTakeProfitPrice` — the
  price levels the setup actually called for at proposal time.
- `TradeProposal.plannedEntryConditions` / `plannedExitConditions` —
  the specific technical/fundamental conditions the setup required,
  structured enough to compare against what actually happened.
- `TradeProposal.requiredConfluences` — which independent signals had
  to align before this setup qualified at all.
- A real broker-level OCO (stop + target) order pair attached to every
  open position, plus an execution-event log recording exactly which
  order actually closed it (stop hit / target hit / manual close /
  time-based) — without this, "did the actual exit match the planned
  exit" has no real event to compare against.
- A `PaperTrade.actualExitReason` field populated from that same real
  execution-event log, so a closed trade's plan-vs-actual comparison is
  a real diff, not an inference.

None of the above is invented or stubbed in this pass — building it
would mean adding real order-management infrastructure this codebase's
100%-simulated `PaperBroker` does not have (see `app/broker.py`'s own
module docstring), a materially larger change than this piece's scope,
and exactly the kind of fabricated-precision trap this project's
engineering discipline exists to prevent.

**Verified:** `tests/test_process_adherence.py` (17 pure-function cases
covering the full required matrix — all-pass, one-fails, multiple-fail,
the five NOT_TRACKABLE_YET checks always present, mixed pass/fail/not-
trackable, a Trading-Mode mismatch that genuinely fails, a Trading Mode
compliance pass for both day-within-bar and swing trades, an untagged
trade reported not-trackable, a risk-limit violation surfaced as failed
Gatekeeper checks, a rejected decision's specific failed check(s), a
WAIT decision scoring `None` with zero verified checks, confirmation the
score never folds not-trackable into either side, and Discipline tier
boundary cases), full backend suite green (1525/1525), `mypy`/`ruff`
clean, `tsc -b --noEmit`/`npm run lint` clean.

---

## Addendum — Probability-First Language Audit (Trading Psychology & Discipline, Piece E)

**Origin.** The fifth piece of the CEO's trading-psychology roadmap
(Pieces A/C above and Piece D in Chapter 74 Part 1). Piece E's brief:
"Probability-first language audit."

**The audit itself, done first.** This codebase has no LLM anywhere
(confirmed: no such dependency in `requirements.txt`) — every player-
facing string is deterministic f-string/template generation, never
freeform prose, so a real audit is genuinely tractable: read every
generation module rather than sample it. 22 real backend text-
generation modules were checked (the Decision Confidence Engine, the
Discipline Chamber, the AI Debate, the Library of Mistakes/Successes,
the Coach, the Academy, market/economic intelligence, and every other
module that produces player-facing prose), plus the frontend files a
keyword sweep flagged for manual review. **Zero genuine violations
found.** Every hit from a certainty-language sweep (`will win/rise/
fall/rally/crash`, `guaranteed`, `sure thing`, `always wins`, `never
loses`, `can't lose`, `100% certain`, `surefire`, `slam dunk`, and more)
resolved to one of: a code comment/docstring describing a structural
code guarantee (never a market-outcome claim), an Academy quiz's
wrong-answer distractor (confirmed via each lesson's own
`correct_index` — these exist specifically to be marked incorrect,
teaching against overconfidence rather than modeling it), or text that
actively negates certainty ("an estimate, not a guarantee" —
`app/calendar.py`; "a probable zone is not a guarantee price ever
reaches it" — `app/market_debate.py`). This is a legitimate zero-finding
result, not a failed search — `app/confidence.py`'s own module
docstring already states the design principle this codebase was built
under: *"Never predicts whether a trade will win. It scores the quality
of the evidence behind the current setup."* The Decision Confidence
Engine (Feature 15), the Discipline Chamber (Feature 26), and the
Library of Mistakes/Successes (Features 27/42) were all already
architecturally probability-first before this piece touched anything.

**Turning the finding into a permanent guarantee, not a report that
goes stale.** New `app/probability_language.py`:
`BANNED_CERTAINTY_PHRASES` — a **phrase**-level list ("is guaranteed
to", "sure thing", "always wins", "100% certain," 23 phrases total),
deliberately never a bare-word ban on "guarantee"/"certain"/"sure",
because this codebase's own *correct* usage already contains those
words inside hedged, negated sentences ("not a guarantee") — a
bare-word ban would flag exactly the probability-first phrasing this
module exists to protect, the same false-positive trap a naive
first-pass grep sweep during this audit itself walked into and had to
correct for. `find_certainty_violations(text)` and `audit_model(model)`
(a generic recursive walker over any pydantic model's string fields,
via `model.model_dump()` — no per-schema field enumeration needed) are
the reusable checker functions.

**The regression guard.** `tests/test_probability_language_audit.py`
runs `audit_model()` against **real generated output** — not synthetic
text — from `generate_discipline_review()`, `generate_case_studies()`,
`generate_success_studies()`, and `generate_debate()` (the AI Debate),
covering the highest-value trade-thesis/analyst-reasoning/post-trade-
review surfaces a future template is most likely to drift on. A planted-
violation test (`test_audit_model_actually_catches_a_planted_
violation`) proves the checker itself works end-to-end against a real
schema object, not just against bare strings, so a silently-broken
checker can't hide behind passing "is clean" assertions. This is
intentionally a representative sample of the highest-value surfaces,
not every one of the 22 modules audited manually — extending fixture
coverage to additional modules is a straightforward, low-risk future
addition using the exact same `audit_model()` call against any other
generator's real output, not a redesign.

**What this addendum explicitly does not do.** It does not add a
frontend surface — this is an internal regression guard for the
CEO/developers, not new information the player needs to see (the
player already sees only clean, probability-first text, confirmed by
the audit). It does not touch any of the 22 audited modules' actual
generation logic, since none needed a fix. It does not claim to have
audited the frontend as exhaustively as the backend — TSX/JSX copy was
checked via keyword sweep and manual review of the flagged files, not
read module-by-module the way the backend's 22 generation modules were.

**Verified:** 10 new tests (`TestFindCertaintyViolations`,
`TestAuditModelAgainstRealGeneratedOutput`) covering clean text, hedged/
negated non-violations, individual phrase detection, real generated
`DisciplineReview`/`CaseStudy` (mistake and success)/`Debate` output all
auditing clean, and the planted-violation proof. Full backend suite
green (1550/1550), `mypy app/` and `ruff check app/ tests/` clean. No
frontend changes in this piece, so no `tsc -b --noEmit`/`npm run lint`
re-verification was needed beyond the audit's own manual review.
