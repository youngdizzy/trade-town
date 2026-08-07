# Chapter 75 — Company Trading Modes & Institutional Capital Protection

**Status:** Backend implemented. Real overlap found and extended rather
than duplicated: Chapter 65 (Market Regime & Adaptive Strategy) already
established the "recommend-only-until-the-CEO-permits" boundary this
chapter's own Adaptive Mode inherits verbatim; Chapter 66 (Institutional
Safety & Capital Protection) already owns the real daily/weekly/monthly
circuit breakers, the real Trade Gatekeeper veto, and the real Emergency
Stop this chapter's own Daily Circuit Breaker Tiers and Losing Streak
Protection reuse rather than re-invent; Chapter 69 Part 1 (MAFMS) already
gives every `Account` its own isolated capital/risk/performance, but its
own module docstring admits live trade execution is not yet wired
per-account — that gap is real, pre-existing, and this chapter does not
attempt to close it. See the Implementation Notes at the bottom for the
complete honesty boundary.

## Executive Summary

Professional trading firms don't force every opportunity through one
strategy — they select Day Trading, Swing Trading, or a deliberate blend
of both, and they protect capital with graduated, rule-based responses
to loss, not a single all-or-nothing switch. **Researched first:**
neither a trading-style concept (day/swing/holding-period) nor a graduated
daily-loss response existed anywhere in this codebase before this
chapter — both are genuine, buildable gaps. What already existed and is
reused rather than duplicated: two real regime classifiers (Chapter 65),
a real binary daily/weekly/monthly loss halt and a real, unconditional
Trade Gatekeeper veto (Chapter 66), a real manually-triggered Emergency
Stop (Chapter 67), a real per-Strategy Health Score (`app/strategy_lab.py`),
and Chapter 73's real Audit Log, which this chapter's own transition and
tier events now feed.

## Mission

Let the CEO choose how the company trades — Day, Swing, or Hybrid — and
have that choice produce real, checkable behavioral differences in how
positions are held and closed; let the market's real, already-computed
regime read recommend (never silently apply) a trading-style change; and
protect the company's capital with a graduated, disclosed response to
daily losses and consecutive losing trades, escalating only as far as
the CEO's own configured thresholds actually justify.

## Philosophy

A trading style is an operating policy, not a personality — it should
change measurable behavior (when positions close, how new risk is sized,
what evidence bar a trade must clear) or it isn't real. Capital
protection should escalate in steps the CEO can see coming, using
numbers this company already computes, never a fabricated "AI judgment."

## Responsibilities

**Owns:** Trading Mode selection and its real behavioral effects
(day-position flattening, hybrid trade-style tagging), Adaptive Mode's
regime-to-trading-mode recommendation, the Daily Circuit Breaker Tier
ladder, Losing Streak Protection, the post-shutdown Recovery Briefing,
and a Trading-Mode-scoped Health Score.

**Does NOT own** (see Appendix E): Market Regime *detection* itself
(Chapter 65 — this chapter only *consumes* `RegimeReconciliation`, never
computes a third regime classifier), the underlying daily/weekly/monthly
binary loss halt or the Trade Gatekeeper's veto authority (Chapter 66 —
this chapter's tiers tighten the same real `RiskLimits`/confidence levers
those systems already read, never a parallel veto pipeline), Emergency
Stop's own halt/resume mechanics (Chapter 67 — this chapter only
*triggers* the real thing), per-trade root-cause review (Chapter 60's
Discipline Chamber — the Recovery Briefing links to real
`DisciplineReview` records, never regenerates them), true per-account
capital isolation for live execution (Chapter 69 Part 1's own documented,
still-open gap).

## Ownership

Real, already-shipped systems this chapter accounts for honestly before
adding anything new:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Market Condition Analysis" | `app/regime_reconciliation.py`'s `RegimeReconciliation` (Chapter 65) | Real `environmentRegime` (5-way), `intelligenceRegime` (13-way), `qualityTier`, `confidencePct`, `agreement`, `posture` (cautious/normal/opportunistic). This chapter's Adaptive Mode reads it directly — never a new classifier. |
| "Daily Loss Circuit Breakers" | `app/risk_engine.py`'s `evaluate_sentinel_risk()` (Chapter 66) | A real, binary daily/weekly/monthly halt at CEO-configured `max_daily_loss_pct`/`max_weekly_loss_pct`/`max_monthly_loss_pct` — no graduated response before the hard halt. This chapter adds three graduated tiers *before* that same real daily threshold, and reuses it unmodified as the final tier. |
| "Emergency Shutdown" | `app/emergency_stop.py` (Chapter 67) | Real, CEO-manually-triggered full halt requiring manual resume. This chapter's Tier 4 and 5-consecutive-loss escalation now *also* trigger it programmatically — the same real mechanic, a second real caller, never a duplicate halt state. |
| "Strategy Health Score" | `app/strategy_lab.py`'s `compute_strategy_health()` (v0.7 Feature 52 Part 2) | A real 7-value health read (`excellent`…`retire_candidate`) over a *backtested Strategy's* `SimulationResult` history. This chapter reuses the exact same `StrategyHealthStatus`/`StrategyHealthTrend` vocabulary and threshold shape for a *live Trading Mode's* real closed-trade history — never a second, differently-worded scale. |
| "Capital Allocation" (independent capital/buying power per strategy) | `app/accounts.py` (Chapter 69 Part 1, MAFMS) | Real per-`Account` isolated `PaperPortfolio`/`RiskLimits` — but its own module docstring confirms live execution is not wired to route a trade into a specific non-primary account. **Genuinely not fixable in this chapter** without rebuilding trade execution's account routing, a separate, much larger, unrequested project. |
| "Recovery Protocol" (root-cause review after a major loss) | Chapter 60's Discipline Chamber (`app/discipline.py`) | Real, permanent, per-trade `PostDecisionReview`. No portfolio-level event exists to trigger a summary above the per-trade layer — the genuine gap this chapter's Recovery Briefing closes. |
| "Institutional Rule Engine" `max_consecutive_losses` rule type | `app/rule_engine.py`'s `RuleType` | Confirmed closed enum, no such value. Losing Streak Protection in this chapter is a **company-wide, always-on check** (like Sentinel), not a per-Account opt-in custom rule, so it is not added to `RuleType` — adding it there would inherit the Rule Engine's own documented "not wired into live execution for non-primary accounts" gap for no reason. |

## Inputs

`RegimeReconciliation` (Chapter 65), `RiskLimits` (Chapter 57/66,
including the already-real `max_weekly_loss_pct`/`max_monthly_loss_pct`),
`PaperPortfolio.trade_history` (real closed trades, source for
trading-style performance splits, consecutive-loss counts, and Trading
Mode Health), `DailyObjectiveStatus`/Sentinel's own daily P&L%
computation, `EmergencyStopState`. **Not a real input anywhere:**
multi-timeframe price data (only one timeframe is ever fetched — see
`app/gatekeeper.py`'s own docstring), a sector-rotation feed, an economic
calendar distinct from Chapter 71's own already-general Economic
Intelligence Center.

## Outputs

`TradingModeState` (`mode`, `hybridDayAllocationPct`, `changedAt`,
`previousMode`, `changeReason`), `AdaptiveModeRecommendation`
(`recommendedMode`, `reasoning`, `confidencePct`, `basedOnPosture`,
`note`), `DailyCircuitBreakerState` (`tier`, `dailyPnlPct`,
`tier1Pct`/`tier2Pct`/`tier3Pct` thresholds, CEO-configurable,
`activeSinceSimDay`), `LosingStreakState` (`consecutiveLosses`,
`pauseActive`, `pauseThreshold`, `suspendThreshold`),
`TradingModePerformanceSplit` (per-style real win rate/P&L/trade count),
`TradingModeHealthAssessment` (per-style, reusing `StrategyHealthStatus`),
`RecoveryBriefing` (generated once per Emergency Stop activation that
this chapter's own tiers/streak triggered — never for a CEO-manual stop,
which already has its own real reason).

## Internal Workflow

1. **Trading Mode selection** (`POST /api/trading-mode`): CEO picks
   `day_trading`/`swing_trading`/`hybrid` (+ `hybridDayAllocationPct` if
   hybrid). Blocked while Emergency Stop is active (a mode change mid-halt
   has nothing real to act on). Records a `MemoryRecord` (category
   `alert`, title `"Trading Mode changed: X → Y"`) — picked up by Chapter
   73's Audit Log via a new `trading_mode_change` category.
2. **Per-proposal tagging**: every new `TradeProposal` gets a
   `tradingStyle: "day" | "swing"` field, assigned deterministically —
   `day_trading` → always `"day"`; `swing_trading` → always `"swing"`;
   `hybrid` → a running weighted-rotation counter matching
   `hybridDayAllocationPct` (e.g. a 70% split assigns 7 of every 10
   proposals `"day"`, in order — a real, disclosed formula, never a coin
   flip dressed up as AI judgment). The tag threads through
   `TradeDecision` → `PaperOrder` → `PaperPosition` → `PaperTrade`
   unchanged once assigned, even if the CEO switches modes mid-hold.
3. **Day-position flattening**: at every sim-day rollover,
   `tick_trading_modes()` force-closes (via the real `close_position()`)
   any open `PaperPosition` tagged `"day"`, reason "Day Trading Mode —
   flattened at day-end." `"swing"`-tagged positions are never touched by
   this check.
4. **Daily Circuit Breaker**: each tick, `compute_daily_circuit_breaker()`
   reads the same real daily P&L% `evaluate_sentinel_risk()` already
   computes and maps it against three new CEO-configurable thresholds
   (default 1%/2%/3%) plus the *existing* `max_daily_loss_pct` (default
   5%) as the fourth and final tier. A tier change writes a real
   `MemoryRecord` and applies its real lever (see Decision Logic) for the
   remainder of the sim day, self-clearing at the next day rollover
   exactly like Sentinel's own existing daily halt already does (Chapter
   66's own documented precedent).
5. **Losing Streak Protection**: each tick, `compute_consecutive_losses()`
   walks `trade_history` backward from the most recent closed trade,
   counting consecutive `pnl < 0` entries. At the CEO-configured pause
   threshold (default 3), new proposal generation pauses until the CEO
   explicitly acknowledges (`POST /api/losing-streak/acknowledge`) — a
   real, CEO-driven clear, never a silent timer. At the suspend threshold
   (default 5), the real Emergency Stop triggers.
6. **Recovery Briefing**: the moment Emergency Stop transitions to active
   *because* of Tier 4 or a losing-streak suspension (never for a
   CEO-manual stop), `generate_recovery_briefing()` synthesizes real
   recent stats (win rate, average loss, largest loss, days since the
   last profitable day) and links to the real `DisciplineReview` records
   for the trades involved — modeled on Chapter 72's own
   `generate_crisis_briefing()` pattern, one new `MemoryRecord`, no new
   report series.
7. **Adaptive Mode** (recommendation only): when
   `adaptiveRecommendationsEnabled` is true,
   `compute_adaptive_mode_recommendation()` reads the real
   `RegimeReconciliation` and maps it to a recommended `TradingMode` (see
   Decision Logic) — read-only, exactly like Chapter 65's own `posture`
   field. The CEO applies it (or not) via the same `POST
   /api/trading-mode` endpoint everything else in this chapter uses —
   never a separate write path.

## Decision Logic

**Trading-style rotation (hybrid):** a running integer counter `n`
increments per proposal; a proposal is tagged `"day"` when
`floor(n × hybridDayAllocationPct / 100) > floor((n-1) × hybridDayAllocationPct / 100)`,
otherwise `"swing"` — a disclosed, deterministic largest-remainder-style
rotation that converges on the configured split over any real run of
proposals, never a probability draw.

**Daily Circuit Breaker levers**, each layered on the last while its tier
is active, all released together at the next sim-day rollover:
- **Tier 1** (daily loss ≥ configured `tier1Pct`, default 1%): position
  sizing tightened via a *derived, non-persisted* copy of `RiskLimits`
  (`risk_per_trade_pct`/`max_position_pct` × 0.75) — the exact same
  "derived copy, never mutates the CEO's own saved limits" pattern
  `nexus.py`'s existing `_effective_risk_limits()` already uses for
  Company Priority. Gatekeeper's minimum confidence threshold raised
  +10 points via a new optional override parameter on
  `evaluate_gatekeeper()`.
- **Tier 2** (≥ `tier2Pct`, default 2%): the same 0.75× tightening
  compounds again, confidence raised +20 points total, and every new
  proposal is forced to wait for manual CEO resolution regardless of
  Operating Mode — the identical real branch `_apply_operating_mode()`
  already uses for Chapter 66's `pause_trading` enforcement, now also
  checking this tier.
- **Tier 3** (≥ `tier3Pct`, default 3%): new proposal generation is
  blocked entirely (existing open positions still managed/closeable
  normally) — "Research mode" is not a separate mechanic; it is simply
  the honest description of what the company does while proposal
  generation is paused.
- **Tier 4** (≥ the existing `max_daily_loss_pct`, default 5%): triggers
  the real `activate_emergency_stop()` — full halt, manual CEO resume
  required, and (new) a Recovery Briefing generated.

**Trading Mode Health**: mirrors `compute_strategy_health()`'s exact
threshold shape (recent vs. lifetime win rate/return/drawdown deltas →
the same `StrategyHealthStatus` seven values) over a trading style's own
`PaperTrade` history instead of `SimulationResult` history — a genuine
adaptation of the real formula to a real, different input shape, not a
duplicate scoring model.

**Adaptive Mode recommendation table** (read-only, never applied
automatically):

| Real signal | Recommendation | Reasoning cited |
|---|---|---|
| `posture == "opportunistic"` and `agreement == "aligned"` | `swing_trading` | Sustained directional confidence — matches the brief's "strong trending market favors swing." |
| `environmentRegime == "sideways"` and `qualityTier` not in (`poor`, `avoid_trading`) | `day_trading` | Range-bound conditions favor shorter holding periods over sustained directional bets. |
| `agreement == "diverging"` | `hybrid` | The two real regime engines disagree — diversifying across both holding-period disciplines hedges that real uncertainty. |
| `qualityTier in ("poor", "avoid_trading")` | *(no trading-mode change recommended)* | The brief itself routes extreme/avoid-trading conditions to Defensive Mode (Chapter 72), not a trading-style pick — the recommendation's `note` field points the CEO there instead of picking a mode a bad market doesn't actually call for. |
| none of the above | *(no recommendation)* | Not every tick has a strong enough real signal to recommend a change — silence is more honest than a low-confidence guess. |

**Automatic Mode (the brief's own second Adaptive configuration) is not
built.** Only Recommendation Mode exists this pass — the same
recommend-only-until-the-CEO-permits boundary Chapter 65's own
Implementation Notes already established as this codebase's deliberate,
conservative default for anything that would auto-adjust a real trading
lever. Building a genuinely safe Automatic Mode needs its own design
pass (reversibility guarantees, an audit trail distinct from a manual
change, interaction rules with an active circuit breaker tier) per
Appendix G's Permanent Development Policy — design before code.

## Department Cooperation

**Receives from:** Chapter 65 (Market Regime Reconciliation — Adaptive
Mode's only real input), Chapter 57 (Position Sizing — the real
`RiskLimits` fields circuit breaker tiers tighten), Chapter 58 (Trade
Gatekeeper — the real confidence check this chapter's tiers raise),
Chapter 60 (Discipline Chamber — real per-trade reviews the Recovery
Briefing links to), Chapter 66 (Sentinel's real daily P&L% — the Circuit
Breaker's only real input), Chapter 67 (Emergency Stop — the real halt
Tier 4 and losing-streak suspension trigger).

**Sends to:** the CEO (Trading Mode state, Adaptive recommendation,
Circuit Breaker/Losing Streak status, Trading Mode performance
split/health), Chapter 73's Audit Log (a new `trading_mode_change`
category and circuit-breaker/losing-streak `MemoryRecord`s, both picked
up the same way Chapter 72's Crisis Briefings already are).

## CEO Controls

| Control | Status |
|---|---|
| Trading Mode (day/swing/hybrid) | **Real** — `POST /api/trading-mode`. |
| Hybrid allocation split | **Real** — `hybridDayAllocationPct`, 0–100, CEO-set. |
| Adaptive Recommendations (on/off) | **Real** — `adaptiveRecommendationsEnabled` toggle; when off, no recommendation is computed. |
| Automatic Mode | **Not built** — see Decision Logic. |
| Circuit Breaker Tier 1/2/3 thresholds | **Real** — CEO-configurable, defaults 1%/2%/3%; Tier 4 reuses the existing `max_daily_loss_pct`. |
| Losing Streak pause/suspend thresholds | **Real** — CEO-configurable, defaults 3/5. |
| Acknowledge a losing-streak pause | **Real** — `POST /api/losing-streak/acknowledge`. |
| Lock a preferred mode | **Already real in spirit** — simply never enabling Adaptive Recommendations, the same "manual control always wins" precedent every other chapter in this Design Bible already follows. |
| Create custom switching rules | **Not built** — the only real "rule" surface, `app/rule_engine.py`'s `RuleType`, is deliberately not extended here (see Ownership) since it would inherit that engine's own unrelated, pre-existing non-primary-account execution gap for no benefit. |

## Learning System

**Not built this pass.** A real learning loop over "which Trading Mode
performs best under which regime" needs a meaningful amount of real
tagged trade history to exist first (this chapter is what starts
producing that history via `tradingStyle`) — building the loop before
any real data exists to learn from would mean either an empty stub or an
invented result, both against this project's own no-fabrication
discipline. A future pass can add it once live play has accumulated real
tagged trades across multiple real regimes.

## KPIs

**Real and computable today:** Trading Mode Performance Split (win
rate/P&L/trade count per style, straight from real `trade_history`),
Circuit Breaker Tier frequency (a real count of tier changes), Losing
Streak occurrences. **Not honestly computable:** Adaptation Success Rate
(nothing auto-adapts), a cross-regime "which mode wins" KPI (see Learning
System — not enough real history yet).

## Reports

**Real, new this chapter:** the Recovery Briefing (Circuit-Breaker/
Losing-Streak-triggered Emergency Stops only). **Not built:** a
recurring Daily/Weekly Trading Mode Report — nothing about Trading Mode
state changes fast enough to need one distinct from the CEO simply
opening the tab, the same "no fixed-cadence report where nothing new
would be in it" reasoning Chapter 73 already used for its own Compliance
Brief.

## Safety Systems

This chapter *is* a Safety System for every trade this company places
once Trading Mode is live: the Circuit Breaker tiers never bypass the
Trade Gatekeeper's own unconditional veto (Chapter 66) — a tightened
`RiskLimits` copy and a raised confidence bar still have to clear the
same real checks every other proposal does. Emergency Stop, once
triggered by Tier 4 or a losing streak, behaves identically to a
CEO-manual stop in every way except its logged reason — no special
"softer" halt exists.

## Dependencies

Chapter 57 (Position Sizing), Chapter 58 (Trade Gatekeeper), Chapter 60
(Discipline Chamber), Chapter 65 (Market Regime & Adaptive Strategy —
this chapter's Adaptive Mode is the "genuine new work" that chapter's own
Implementation Notes named as not yet built), Chapter 66 (Institutional
Safety & Capital Protection — this chapter's Circuit Breaker ladder and
Losing Streak Protection are two of the exact gaps that chapter's own CEO
Controls table named as "Not built"), Chapter 67 (Emergency Stop),
Chapter 69 Part 1 (MAFMS — the real account isolation this chapter's
Capital Allocation section explicitly does not extend to live execution),
Chapter 73 (Audit Log — this chapter's transition/tier/streak events
extend it with one new category, never a parallel log).

## Connected Features

`app/strategy_lab.py`'s `compute_strategy_health()` (the real formula
this chapter's Trading Mode Health mirrors), `app/nexus.py`'s
`_effective_risk_limits()` (the real derived-RiskLimits-copy pattern this
chapter's Circuit Breaker tiers extend), `app/audit_log.py` (Chapter 73 —
gains one new `AuditEventCategory`).

## Future Expansion

Automatic Adaptive Mode (see Decision Logic), a true per-account
capital-isolated Hybrid mode (blocked on Chapter 69 Part 1's own
execution-routing gap), weekly/monthly graduated (rather than binary)
circuit breaker tiers (the brief's daily example is what this pass
builds; weekly/monthly stay the existing real binary halt), a
cross-regime Trading Mode learning loop (see Learning System) — none
invented or stubbed here.

## Company Principle

TradeTown adapts its trading style to real, computed market conditions
and protects its capital with graduated, disclosed responses — never a
fabricated AI judgment standing in for a formula, and never past the
CEO's own configured limits.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written:** two independent regime classifiers reconciled into one
read-only posture (Chapter 65), a real binary daily/weekly/monthly loss
halt and unconditional Trade Gatekeeper veto (Chapter 66), a real
manually-triggered Emergency Stop (Chapter 67), a real per-Strategy
Health Score (`strategy_lab.py`), real per-`Account` capital isolation
with an admitted execution-routing gap (Chapter 69 Part 1), and
`nexus.py`'s own `_effective_risk_limits()` precedent for a
derived-never-persisted `RiskLimits` tightening. None of this needed to
be rebuilt.

**What was built:** `app/trading_modes.py` — Trading Mode selection with
real day-position flattening and hybrid trade-style rotation; a Daily
Circuit Breaker Tier ladder layered in front of the existing real daily
halt, reusing `_effective_risk_limits()`'s own pattern and a new optional
Gatekeeper confidence override; Losing Streak Protection triggering the
same real Emergency Stop; a Recovery Briefing generated only for
tier/streak-triggered stops; a Trading Mode Performance Split and Health
Score reusing `StrategyHealthStatus`; an Adaptive Mode recommendation
reading Chapter 65's real `RegimeReconciliation`. Explicitly cut: true
per-account capital isolation, Automatic Adaptive Mode, custom
switching rules via the Rule Engine, weekly/monthly graduated tiers, and
a cross-regime learning loop — all listed above with the real reason
each was cut.
