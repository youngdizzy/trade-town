# Chapter 70 — Prop Firm Rule Engine

**Status:** Pure architecture, not yet implemented — same posture as
[Chapters 68](chapter-68-institutional-broker-management-system.md)/
[69](chapter-69-multi-account-fund-management-system.md). **A numbering
note:** this brief arrived without an explicit chapter number (unlike
67/68/69's own headers); it's filed here as Chapter 70, the next
sequential number in Volume 10, since it's substantial enough to be its
own chapter and depends directly on Chapter 69's own Prop Firm account
type. Flagged explicitly, not silently assumed, in case a different
number was intended. **Researched first:** this is the one chapter in
this run with the *strongest* real backing found so far — nearly every
"Supported Rule" the brief lists either already exists as real,
enforced machinery under a different scope (daily, not challenge/
trailing), or maps directly onto `DailyObjectiveStatus`, a real,
already-live, per-day compliance readout. What's missing is narrower
and more precise than Chapters 68/69's near-total gaps: trailing
drawdown, consistency rules, leverage, scaling milestones, and
challenge-scoped (rather than daily-scoped) tracking. See the
Implementation Notes at the bottom for the exact split.

**Addendum (received as "Addendum to Chapter 69," applied here):** a
follow-up brief arrived labeled "Addendum to Chapter 69," but its
content — Trailing Drawdown Engine, Consistency Rule Engine, Leverage
System, Scaling Milestones, Challenge Windows, Weekday-Aware Time
System, Prop Firm Calendar, Compliance Score — is a direct, detailed
specification of the gaps *this* chapter's own Implementation Notes
already named as genuinely unbuilt, not Chapter 69's own (Multi-Account
& Fund Management). Applied here rather than to Chapter 69, flagged
explicitly rather than silently reconciled, in case a literal Chapter
69 placement was intended. See "Implementation Requirements Addendum"
below. **The same addendum also introduced a real architectural
correction, covered in full in [Chapter
71](chapter-71-institutional-rule-engine.md):** this chapter's own
rules must never become a standalone, independent enforcement system —
they become one Rule Profile loaded into a single centralized
Institutional Rule Engine every account type shares. This chapter
still owns *which* rules a Prop Firm account needs; Chapter 71 owns
*how* any account's rules get enforced.

## Executive Summary

A Prop Firm Rule Engine's job is to protect a funded account by
blocking any trade that would violate the firm's own rules — before it
happens, not after. **Researched first:** TradeTown already has exactly
this shape of machinery, built for a different reason. Chapter 57's
Position Sizing and Chapter 66's enforcement already run an
unconditional, real, pre-trade check-and-block pipeline
(`evaluate_sentinel_risk()` → a critical `RiskWarning` → the Trade
Gatekeeper's eight checks, no CEO override possible), and
`DailyObjectiveStatus` already tracks trades-today, realized P&L
today, profit-target-reached, max-loss-reached, and a halt reason —
live, every tick. None of it is prop-firm-branded or challenge-scoped
today, but the enforcement shape this chapter asks for already exists
and already works.

## Company Philosophy

"Passing and protecting funded accounts always takes priority over
maximizing profit" is not a new posture for this codebase to adopt —
it's the same posture Chapter 66's own Company Philosophy already
states ("survival comes first, profit comes second") for the one
account that exists today. A Prop Firm account would inherit that
same discipline, scoped tighter.

## Primary Responsibilities

**Would own:** the fifteen supported prop firm rules, pre-trade
validation against all of them, live account monitoring, proactive
warnings, account-protection recommendations, and the Prop Firm
Dashboard.

**Does NOT own** (matches this codebase's real division of labor):
Trade Decisions (the analyst desk), Trade Approval (the CEO, or
auto-resolution per Operating Mode), general Risk Authority (Chapters
57/58/66 — this chapter would sit *inside* that same pipeline as one
more account-type-specific check, never a second, parallel veto
system), Broker Communication (Chapter 68), Account Management
(Chapter 69 owns the account type itself; this chapter owns only the
rule set a Prop Firm-typed account would carry), **and, per the
addendum's own correction, rule *enforcement* itself** — this chapter
defines which rules a Prop Firm account needs (the fifteen supported
rules plus the eight addendum systems below); [Chapter
71](chapter-71-institutional-rule-engine.md)'s centralized Institutional
Rule Engine is the only system that ever actually enforces any rule,
for any account type. This chapter must never grow its own independent
enforcement path.

## Implementation Requirements Addendum

Eight systems named as "mandatory for a complete institutional-grade
Prop Firm Rule Engine," each checked against the real codebase before
being added here — every one of them lands on the "genuinely unbuilt"
side of this chapter's own Ownership table above, so this section adds
detail to already-identified gaps rather than discovering new ones:

**1. Trailing Drawdown Engine.** Requires tracking the highest
historical equity ever reached (a peak-equity/high-water-mark value)
and continuously recomputing drawdown from that moving peak, not a
fixed floor. Grep-confirmed: no peak-equity or high-water-mark field
exists anywhere in this codebase's schemas. `RiskLimits.maxDrawdownPct`
only ever compares current equity against the account's *starting*
balance — the "support both static and trailing drawdown models"
requirement means keeping today's real static check exactly as-is and
adding a second, genuinely new computation alongside it, never
replacing one with the other.

**2. Consistency Rule Engine.** Requires comparing one day's P&L
against a challenge's running cumulative total (the "no single day
&gt;X% of total profit" shape most real prop firms use). No such
comparison exists anywhere — `DailyObjectiveStatus` tracks *today's*
realized P&L in isolation, never against an accumulating challenge-
window total, because no challenge window is tracked at all (see
Challenge Windows below).

**3. Leverage System.** Requires a margin/leverage concept this
codebase has never had at any ratio — Chapter 68's own research already
confirmed a 100%-cash, long-only account with no margin field, no
buying-power-beyond-cash-balance concept, and no liquidation logic of
any kind. This is the single largest structural gap of the eight: every
other item on this list extends an existing real number; this one has
no real foundation to extend at all.

**4. Scaling Milestones.** Requires both a funded-account growth-stage
concept (does not exist) and Chapter 69's own account model (does not
exist, since a milestone is meaningless without a specific account to
track it against).

**5. Challenge Windows.** Requires a bounded time window (30/60/90-day
or unlimited) distinct from the sim's own unbounded day counter, plus
daily-pace-required math derived from days remaining and progress so
far. Neither exists — `TimeState.day` counts up forever with no
concept of "this challenge started on day N and must finish by day
N+30."

**6. Weekday-Aware Time System.** The addendum's own comparison is
accurate and confirmed by direct inspection: `TimeState` (`app/schemas.py`)
is exactly `{day: int, hour: int, minute: int}` — no weekday, week
number, month, quarter, year, market session, or holiday field exists
anywhere. This is real, load-bearing infrastructure work, not a Prop
Firm-specific add-on — Weekend Holding Rules, Minimum Trading Days,
News Blackout Days, and Challenge Windows above all depend on it
directly, and it would be a real, honest, standalone backend slice
(extending `TimeState` and whatever derives sim days into weekdays) if
this chapter's architecture is ever implemented.

**7. Prop Firm Calendar.** A presentation layer over Trading Days
Completed/Remaining, Challenge Deadline, Weekend Countdown, Holiday
Schedule, and News Blackout Days — every one of those inputs depends on
the Weekday-Aware Time System and Challenge Windows above, neither of
which exists. Nothing to build here until both exist.

**8. Risk Score (Prop Firm Compliance Score).** Requires combining
Drawdown Safety, Consistency, Rule Compliance, Risk Exposure, Capital
Preservation, and Account Health into one composite number. Every
individual input already has *some* real analog (Drawdown Safety →
`maxDrawdownPct` proximity; Risk Exposure → open-position exposure
already computed for `maxPositionPct`; Account Health → Chapter 63's
real `CompanyHealth.overall`, company-wide not account-scoped) but no
formula anywhere combines multiple risk signals into one composite
score — this codebase's own "no black-box composite" convention
(Chapter 66's own Decision Logic section states it explicitly) means
any real implementation of this score must publish its own weighting
formula in the open, the same way `CompanyHealth.overall`'s own real
formula already is, never a hidden blend.

## Ownership

Every one of the brief's fifteen "Supported Rules," checked against
the real codebase before this chapter was written:

| Supported rule | Real system today | What it actually does |
|---|---|---|
| Daily Loss Limit | `RiskLimits.maxDailyLossPct` (Ch57), enforced in `evaluate_sentinel_risk()` | Real, live, checked every relevant tick — the strongest real match in this whole chapter. |
| Maximum Overall Drawdown | `RiskLimits.maxDrawdownPct` | Real, but a fixed lifetime ceiling from starting balance, not scoped to a specific challenge window. |
| Trailing Drawdown | *(does not exist)* | `maxDrawdownPct` is a fixed floor, never recalculated from a rolling peak-equity high — the defining feature of a real trailing-drawdown rule. No peak-equity tracking exists to trail from. |
| Maximum Position Size | `RiskLimits.maxPositionPct` | Real, enforced. |
| Maximum Risk Per Trade | `RiskLimits.riskPerTradePct` | Real, enforced. |
| Maximum Open Positions | `RiskLimits.maxOpenPositions` | Real, enforced. |
| News Trading Restrictions | *(does not exist)* | `ScannerAlert` has news-adjacent alert types (`gap_up`/`gap_down`/etc.) but no blackout-window or trade-blocking logic tied to them. |
| Minimum Trading Days | *(does not exist)* | No "days actually traded" counter distinct from total sim days elapsed — `DailyObjectiveStatus.simDay` tracks the calendar, not trading-day participation. |
| Consistency Rules (no single day &gt; X% of total profit) | *(does not exist)* | No formula anywhere compares one day's P&L against a challenge's cumulative total. |
| Maximum Leverage | *(does not exist — confirmed by Chapter 68's own research)* | 100% cash-account, long-only paper trading; no margin or leverage concept exists anywhere in this codebase. |
| Profit Targets | `RiskLimits.dailyProfitTargetPct` (Ch67) | Real, but **daily**-scoped, not the brief's own challenge-scoped target (e.g., "8% over 30 days") — a different shape serving a related purpose. |
| Account Scaling Milestones | *(does not exist)* | No account-growth-triggers-a-new-limit-tier concept anywhere — also depends on Chapter 69's account model, which doesn't exist yet. |
| Time-Based Restrictions | *(does not exist)* | `TimeState` is `{day, hour, minute}` only — nothing gates trading to specific hours today; agents and the sim run continuously. |
| Weekend Holding Rules | *(does not exist)* | No day-of-week concept exists anywhere in `TimeState` — there is no calendar to check a "weekend" against, let alone a rule enforcing flat-by-Friday. |
| Broker-Specific Rules | *(explicitly future, per the brief's own "(future)" tag)* | Honored at face value — depends on Chapter 68's real broker connections, which don't exist. |

**Score: 6 of 15 already real and enforced** (Daily Loss, Overall
Drawdown, Position Size, Risk Per Trade, Open Positions — five
directly, plus Profit Targets in a related daily-scoped shape) — by
far the highest real-coverage ratio of any chapter written in this
run so far, precisely because this brief asks for machinery Chapter 57
and Chapter 66 already built for the one account that exists.

## Inputs

**Real today:** every `RiskLimits` field listed as real above, and
`DailyObjectiveStatus`'s live daily counters. **Would need, once
Chapter 69's account model is real:** a per-account rule profile (this
chapter's own scope) distinct from the single global `RiskLimits`
object that exists today.

## Outputs

**Real today:** a critical `RiskWarning` on the first violated limit,
`DailyObjectiveStatus.tradingHalted`/`haltReason`. **Would produce,
once real:** Challenge Progress, Rule Compliance Score, Account Health
Score scoped to a Prop Firm challenge specifically — none of which
exist as named, computed outputs today.

## Internal Workflow

**The brief's own Pre-Trade Validation, checked question by question:**
"Will this trade violate today's daily loss limit?" — real, checked,
today (`evaluate_sentinel_risk()`). "Will this trade violate the
trailing drawdown?" — cannot be checked; no trailing-drawdown
computation exists. "Will this position exceed maximum account
exposure?" — real, checked, today (`maxPositionPct`/
`maxSectorConcentrationPct`). "Will this trade break any prop firm
rules?" — real for the six rules confirmed real above; not checkable
for the other nine. **"If YES: the trade is automatically blocked, the
AI explains exactly why"** — this exact shape is already real and
unconditional: the Trade Gatekeeper's eight checks (Ch58) block
regardless of CEO intent and each carries a real, specific reason
string, never a generic rejection.

## Decision Logic

**Real today, for the six confirmed-real rules:** each is a
transparent, named threshold check, no hidden weighting — matches this
codebase's "no black-box composite" convention throughout, same as
every other risk formula in Chapters 57/58/66. **Not real:** any
formula for trailing-drawdown recalculation, consistency-rule
percentage math, or a combined Rule Compliance Score across multiple
rules — today each real check is independent, never combined into one
composite readout the way the brief's own Prop Firm Dashboard implies.

## Department Cooperation

**Would receive from:** Chapter 69 (the Prop Firm account type this
chapter's rules would attach to — does not exist yet), Chapters 57/58/66
(the real risk-check machinery six of this chapter's fifteen rules
already are), Chapter 67 (the real sticky-critical-toast + Alert
Center delivery mechanism this chapter's Warning System would use).
**Would provide:** Rule Compliance state to the Executive Dashboard
(Chapter 67's real `useDashboardData()` hook would be the natural
integration point once this chapter has real data to contribute),
account-protection recommendations to the CEO.

## CEO Controls

| Control | Status |
|---|---|
| Enable Prop Firm Rule Set on an account | **Not built** — depends on Chapter 69's account-type model, which doesn't exist. |
| Configure Daily Loss / Drawdown / Position Size / Risk Per Trade / Open Positions | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today. |
| Configure Trailing Drawdown / Consistency Rules / Leverage / Scaling Milestones | **Not built** — no underlying computation exists for any of these four yet. |
| Weekend Holding Rules (configurable) | **Not built** — no day-of-week concept exists to configure a rule against. |
| Auto-pause on rule-violation risk ("if CEO approval settings allow") | **Not built as a settings-gated auto-pause specifically** — the closest real precedent is Chapter 66's AI Consensus Safety `pause_trading` enforcement, a real system-triggered pause, but for department disagreement, not rule-violation proximity. Emergency Stop (Chapter 67) is real but CEO-triggered only, never system-initiated. |

## Warning System

**The brief's own example warnings, checked against real delivery
infrastructure:** "One additional full-loss trade could violate
today's drawdown," "Maximum exposure nearly reached," "Trading should
stop for today" — none of these specific messages are generated today,
but the delivery mechanism they'd use is real and already built:
Chapter 67's sticky, non-auto-dismissing critical-tier toast (added for
Risk Warnings and Emergency Stop activation) plus the Executive Alert
Center's recorded history. A real Prop Firm proximity-warning
generator would be new logic; the pipe it would push through already
exists. "Challenge target is 82% complete" specifically depends on
Chapter 69's challenge-scoped tracking, which doesn't exist yet.

## Account Protection

**Two of the brief's five protective recommendations have zero real
backing under any name:** "Switch to swing trading" (Chapter 67's own
Command Palette research already confirmed no such mode exists under
any name) and "Research only" as a distinct enforced mode (the closest
real analog, `learning` Operating Mode, still allows manual CEO trades
— it restricts automation, not all trading). **Two are real, but
CEO-triggered only, never system-initiated:** Emergency Stop (full
pause) and, loosely, reducing position size (the CEO can already edit
`RiskLimits` manually at any time — there's no AI-recommended,
one-click "reduce size for this account" action). **"End the trading
session"** has no real analog — there is no session concept distinct
from the always-running sim clock.

## Prop Firm Dashboard

**Genuinely unbuilt as a named, dedicated dashboard** — but seven of
its nine listed metrics already have a real, live, close analog:
Daily Loss Remaining and Maximum Drawdown Remaining (derivable today
from `RiskLimits` minus `DailyObjectiveStatus`'s live P&L), Profit
Target (`dailyProfitTargetPct`, daily-scoped), Trading Days Completed
(no real counter, see Ownership), Rule Compliance Score (no real
composite score, only independent real checks), Account Health Score
(Chapter 63's real `CompanyHealth.overall` is the closest analog,
company-wide not account-scoped), Capital at Risk (real — sum of open
position exposure already computed for `maxPositionPct` checks).
**Challenge Progress specifically remains the one metric with no real
foundation at all** — it presumes the challenge-window tracking this
chapter's Ownership section already confirmed doesn't exist.

## Security

No new surface — inherits Chapter 68's and Chapter 69's identical
finding: no broker credential or per-account permission exists
anywhere yet for a Prop Firm rule set to need to secure differently
from any other account.

## Reports

**Not built.** No named Prop Firm-specific report object exists.
`DailyObjectiveStatus` is the closest real, live analog (see Live
Account Monitoring / Ownership above) but is never archived into a
persisted report series the way `TreasuryMonthlyReport` or
`CoachReport` already are for their own domains.

## KPIs

**Real and computable today, if scoped honestly to "daily" rather than
"challenge":** compliance against the six confirmed-real rules above.
**Not honestly computable:** a combined Rule Compliance Score,
Challenge Progress percentage, or Trading Days Completed — each
depends on tracking this codebase doesn't do yet, and reporting a
number for any of them today would fabricate a measurement that never
actually ran, the same trap Chapter 68's KPIs section already named
for Execution Success Rate.

## Learning System

**Not built**, for the same reason as Chapters 68/69's own Learning
System sections: there's no Prop Firm account, challenge, or rule
violation history to learn from yet, since no Prop Firm account type
exists to generate any.

## Dependencies

Chapter 69 (Multi-Account & Fund Management System — the Prop Firm
account type this chapter's rules attach to; itself pure architecture,
so this chapter is gated transitively behind it), Chapters 57/58/66
(the real risk-check machinery this chapter reuses rather than
duplicates), Chapter 67 (the real notification-delivery pipe the
Warning System would use). All previous Design Bible chapters, per the
same honest framing Chapters 66/68/69 already use correctly.

## Future Expansion

Broker-Specific Rules (per the brief's own "(future)" tag), automatic
account scaling on milestone achievement, and multi-firm rule-set
templates (different prop firms enforce different specific thresholds)
all require Chapter 68's real broker connections and Chapter 69's real
account model, neither of which exist. Matches this volume's own
Future Expansion precedent exactly.

## Design Bible Integration

**Would integrate with, once real:** the Executive Dashboard (via
Chapter 67's real `useDashboardData()` hook — the natural place a Prop
Firm account's live compliance state would surface once it exists),
Company Memory (a rule violation or near-violation would be exactly
the kind of event `app/scribe.py` already records for other real risk
events today), Risk Authority (this chapter's own rules would run
*inside* the existing Sentinel/Gatekeeper pipeline, never a second
parallel one). None of this requires new integration design — it
reuses seams Chapters 57/58/61/66/67 already built.

## Company Principle

"TradeTown should think like a disciplined professional trader whose
first objective is to keep the funded account alive" is, today,
already the operating principle of the one real account this codebase
has — Chapter 66's own Company Principle states it in almost identical
words ("disciplined survival over reckless growth"). A Prop Firm
account wouldn't need a new philosophy, only a tighter, challenge-
scoped, account-specific version of the same discipline already real
and enforced today.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written, not assumed — the strongest real-coverage ratio of any
chapter in this run:** five of the brief's fifteen supported rules
(Daily Loss Limit, Maximum Overall Drawdown, Maximum Position Size,
Maximum Risk Per Trade, Maximum Open Positions) are already real,
enforced, CEO-configurable `RiskLimits` fields, checked unconditionally
every relevant tick by `evaluate_sentinel_risk()`; a sixth (Profit
Targets) is real in a related daily-scoped shape
(`dailyProfitTargetPct`); the exact "block automatically, explain
exactly why" pre-trade shape the brief asks for is already real and
unconditional, via the Trade Gatekeeper's eight checks (Chapter 58);
`DailyObjectiveStatus` is a real, live, per-day compliance readout —
tradesToday/realizedPnlPctToday/profitTargetReached/maxLossReached/
tradingHalted/haltReason — that already does, daily, most of what the
brief's own Live Account Monitoring and Prop Firm Dashboard ask for at
challenge scope; and Chapter 67's sticky-critical-toast + Alert Center
is real, working delivery infrastructure this chapter's Warning System
would use rather than invent. **What's genuinely, entirely unbuilt:**
trailing drawdown (no peak-equity tracking exists to trail from),
consistency rules, leverage (this is a 100%-cash account, confirmed by
Chapter 68), account scaling milestones, time-based/weekend
restrictions (no day-of-week concept exists anywhere in `TimeState`),
challenge-scoped (rather than daily-scoped) tracking of any kind, "Swing
Trading Mode" (confirmed absent under any name by Chapter 67's own
research), any system-initiated automatic pause distinct from the
CEO-triggered Emergency Stop, and — transitively — everything that
depends on Chapter 69's account model, which is itself pure
architecture. **Also confirmed by direct research for the addendum
above:** no generic rule/rule-profile abstraction and no peak-equity/
high-water-mark field exist anywhere in this codebase's schemas — grep
against every backend module returned zero matches for either. No code
was written against this chapter. Gated by the same [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapters 68/69 are gated by, and — for enforcement specifically —
by [Chapter 71](chapter-71-institutional-rule-engine.md), the one
centralized system that would ever actually enforce any rule this
chapter defines.
