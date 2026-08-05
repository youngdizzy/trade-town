# Chapter 59 — Capital Priority & Opportunity Cost Engine

**Status:** Fully implemented — backend (`app/capital_priority.py`,
wired into `app/nexus.py`'s post-Chapter-58 approved-candidate loop and
`app/executive.py`'s `is_significant_proposal`) and frontend (the
EXECUTIVE tab's ranked Pending Proposals queue, and the RISK tab's two
new CEO controls). See [Volume 9's chapter template](README.md) for
what every section below must contain, and the Implementation Notes at
the bottom of this chapter for exactly what's real today versus new
here.

## Executive Summary

Professional firms constantly compare opportunities against each other,
not just against a fixed bar — an excellent trade can still lose to a
better one competing for the same finite capital. TradeTown should ask
not "is this a good trade?" (Chapter 58's job) but "is this the best use
of company capital *right now*?" — a question this codebase does not
currently ask at all.

**Researched first — the real gap is real and specific.** Chapter 58's
own Design Bible chapter already flagged this exact gap in its own
Implementation Notes: pending `TradeProposal`s sit in a flat,
first-approved-first-shown list (`app/nexus.py`'s
`trade_proposals = [*trade_proposals, *new_proposals]`), never ranked by
their own already-computed Decision Score. Nothing in this codebase
today ever asks whether capital would be better spent on a different,
currently-pending candidate before spending it on this one. Portfolio
Intelligence's real `opportunityCost` field (`app/portfolio_intelligence.py`'s
`_opportunity_cost()`) is real and honest, but is a single qualitative
sentence about cash-vs.-pending-count — never a ranked decision input.
This chapter is the natural place to close both gaps.

## Mission

Capital is finite. Every dollar allocated to one opportunity cannot be
allocated elsewhere. This engine ensures every approved trade competes
against every other currently-pending trade before receiving company
capital — TradeTown should never settle for "good enough" when a
better-ranked opportunity is sitting in the same queue.

## Philosophy

Every trade has an opportunity cost. Choosing one opportunity means
rejecting another, even implicitly. Capital should always seek its
highest-quality destination, not merely clear a fixed bar.

## Responsibilities

**Owns:** ranking the pending proposal queue by a real Priority Score;
Opportunity Cost Analysis at the pending-queue stage; Capital
Reservation (the CEO's real, intentional "hold capital back" decision);
Capital Competition among currently-pending proposals.

**Does NOT own** (see Appendix E, the Decision Authority Matrix):
whether a candidate is approved at all (Chapter 58's job, upstream of
this chapter); how large an approved trade's position is (Chapter 57's
job); continuous re-evaluation of already-*open* positions against new
opportunities — that is explicitly Chapter 60's job (Portfolio
Rebalancing & Adaptive Capital Rotation), a deliberate division matching
both chapters' own stated boundaries: this chapter ranks the queue
*before* capital is spent; Chapter 60 re-examines commitments *after*
capital is already spent. Trade Execution, Risk Approval, Strategy
Creation, Broker Communication are unowned here, same as every other
department in this volume.

## Ownership

Would extend `app/nexus.py`'s post-Chapter-58 approved-candidate loop
(the point where `new_proposals` is finalized, right before
`trade_proposals = [*trade_proposals, *new_proposals]`) and reuse
`app/war_room.py`'s `DecisionScoreBreakdown.overall` and
`ExpectedValueAnalysis` without modification, the same "no second
composite score" discipline Chapters 57 and 58 already established. A
real Capital Reservation control would extend `RiskLimits`
(`cash_reserve_pct` already exists from Chapter 57 as the *minimum*
floor; this chapter's reservation is a distinct, real CEO-facing
*intentional* choice to hold more than the floor, not a duplicate
field).

## Inputs

| Brief asks for | Already real, as |
|---|---|
| Evidence / Confidence / Probability / Trade Quality Score | `DecisionScoreBreakdown` (Chapter 55), reused directly |
| Expected Value | `ExpectedValueAnalysis` (Chapter 55), reused directly |
| Position Size Recommendation | `PositionSizingResult` (Chapter 57), reused directly |
| Portfolio Heat | `PortfolioHeat` (Chapter 56), reused directly |
| Available Capital | `PortfolioIntelligence.cashPctOfEquity`/`deployedPctOfEquity` (Chapter 56) |
| Sector Exposure / Current Holdings | `CategoryExposure` (Chapter 56) |
| Company Risk Budget | `RiskLimits.maxWeeklyDeploymentPct` (Chapter 57's real spendable weekly budget) |
| Liquidity | `LiquidityRead` (already folded into Decision Score) |
| Approved Trade Queue | `trade_proposals` (real, but currently unranked — the gap this chapter closes) |
| Historical Performance | `app/decision_vault.py`'s similar-trade summary (already reused by War Room) |
| Company DNA | `app/company_dna.py`'s five real traits — real and read-only, **not currently wired as an input anywhere**, same honest gap Chapter 58's own chapter already flagged |

## Capital Competition Workflow

```
Approved candidate (already cleared Chapter 58's gate)
        v
Capital Availability check (real: PortfolioIntelligence's cash/deployed split)
        v
Opportunity Comparison — rank against every OTHER currently-pending
proposal by Priority Score (see below)
        v
Priority Score assigned + queue re-sorted, highest first
        v
Capital Allocation Decision — the CEO (or, in Assisted/Executive mode,
the existing auto-resolution pipeline) works the queue top-down;
Position Sizing (Chapter 57) still determines exactly how much each
individual approved trade gets, unchanged
```

## Priority Score

**Reuses, does not duplicate.** The brief's own factor list (Expected
Value, Evidence, Probability, Risk, Portfolio Diversification, Capital
Efficiency, Historical Edge, Market Quality, Liquidity, Trade Quality)
is, factor-for-factor, the same real composite Chapter 55's
`DecisionScoreBreakdown.overall` already is, plus Chapter 56's real
`CapitalEfficiency`/diversification reads. The honest design is to reuse
`decisionScore.overall` directly as this engine's real Priority Score —
inventing a second, competing composite from the same underlying
signals would be exactly the duplication this codebase's own convention
forbids (see Chapters 57 and 58's own precedent for the same reuse
decision). The one genuinely new element the brief's factor list adds
beyond what Decision Score already covers is **Opportunity Cost**
itself (see below) — a real, additive adjustment layered on top of the
reused score, not folded into it, so the underlying Decision Score
shown elsewhere in the Command Center never silently drifts from what
Chapter 55 already computes for it.

## Opportunity Cost Analysis

Before allocating capital to a pending proposal, this engine's real
question is whether a *currently pending* proposal outranks it — never
a speculative claim about trades that don't exist yet. "Will this
reduce the ability to take a better trade later today/tomorrow/this
week?" is honestly answerable only in the aggregate, real sense
Chapter 56's `opportunityCost` field already gives (cash-vs.-pending
posture) — a literal per-symbol forecast of *future* opportunities that
haven't appeared yet would be fabrication, not analysis, and is
explicitly not built here.

## Capital Reservation

A CEO-set Capital Reserve % beyond Chapter 57's own `cashReservePct`
floor is a real, honest, additive control: `cashReservePct` is a hard
floor Position Sizing never spends into; this chapter's reservation is
the CEO's own *voluntary* choice to hold back more than that floor when
few high-quality opportunities exist — "holding cash is an intelligent
allocation decision," made real by simply respecting a higher
CEO-chosen number, never a second competing mechanism.

## Trade Ranking

The real, new Opportunity Queue: pending proposals sorted by Priority
Score, highest first — closing the exact gap Chapter 58's own
Implementation Notes flagged as not yet built. When capital is limited
(the weekly deployment budget or cash reserve would be exceeded),
capital allocates from the top of the ranked queue downward, honestly
skipping lower-ranked candidates rather than allocating in arrival
order.

## Replacement Analysis

**Explicitly not this chapter's job.** The brief's own "Replacement
Analysis" section (comparing new opportunities against *already-open*
positions) belongs to Chapter 60 (Portfolio Rebalancing & Adaptive
Capital Rotation) — this chapter's queue only ever contains *pending*,
not-yet-capitalized proposals. See Chapter 60 for the real, substantially
larger gap this half of the brief actually describes.

## CEO Controls

| Control | Status |
|---|---|
| Minimum Priority Score | **New** — a CEO-configurable floor on the reused Decision Score, distinct in purpose from Chapter 58's `minTradeQualityScore` (that one gates *approval*; this one gates *allocation order* once already approved) but the same real number underneath — implementation should reuse `decisionScore.overall` as the read, not invent a second read. |
| Capital Reserve % | **New**, additive to Chapter 57's existing `cashReservePct` floor — see Capital Reservation above. |
| Maximum Simultaneous Positions | **Already real** — `RiskLimits.maxOpenPositions`. |
| Sector Allocation Limits | **Already real** — `RiskLimits.maxSectorConcentrationPct`. |
| Cash Preference | Overlaps directly with Capital Reserve % above — not a separate real control. |
| Opportunity Cost Sensitivity | **Not built** — would require the numeric Opportunity Cost adjustment described above to exist first. |
| Capital Rotation Frequency | **Not this chapter's job** — belongs to Chapter 60, since rotation only makes sense against already-open positions. |
| Long-Term vs. Short-Term Preference / Swing vs. Day Allocation Ratio | **Not built** — this codebase has one real trading mode; the same honest gap Chapters 57 and 58 already document (`docs/DesignBible/volumes/06-trading-operating-system.md`). |

## KPIs

Real and computable once this engine exists: Average Priority Score of
allocated-vs.-skipped candidates; Capital Efficiency (already real,
Chapter 56's `CapitalEfficiency`, reused not duplicated); Cash
Deployment Efficiency (derivable from `deployedPctOfEquity` over time).
**Not honestly computable without fabrication:** "Missed Opportunity
Rate" and "Opportunity Utilization" as the brief frames them would
require knowing about opportunities that were never generated at all —
this engine can only report on the real, pending queue that actually
existed, never a hypothetical universe of missed ones.

## Reports

Same "no new data source, just a new aggregation view" pattern this
volume's other chapters already establish — a Daily Priority Rankings
view and a Capital Allocation view are both thin reads over the real,
newly-ranked queue and `PortfolioIntelligence`, nothing fabricated.

## Learning System

After every completed trade, the real, answerable question is whether
its Priority Score at allocation time correlated with its real outcome
— a genuine, computable correlation study over `PaperTrade` history and
the (newly real) Priority Score recorded at the moment capital was
allocated. "Were better opportunities missed?" is only honestly
answerable for opportunities that were real (i.e., other pending
proposals at the same moment), never a hypothetical broader universe.

## Safety Systems

Never allocate all capital to one opportunity — already enforced by
Chapter 57's per-tier and per-position caps, unchanged and not
re-implemented here. Never violate diversification limits — already
enforced by `RiskLimits.maxSectorConcentrationPct` and the Chapter 58
Gatekeeper's correlation check, unchanged. This chapter's own real
addition is ensuring the *order* capital is offered to the queue
respects real Priority Score ranking, never first-come-first-served.

## Department Cooperation

**Receives from:** the Opportunity Gatekeeper (Chapter 58, the approved
candidate pool this chapter ranks), Position Sizing (Chapter 57, the
real per-trade size once ranked), Risk Authority (Sentinel/Guardian),
Portfolio Intelligence (Chapter 56), the Research Division. **Sends to:**
the CEO (the real ranked Opportunity Queue, wherever pending proposals
are shown), the existing auto-resolution pipeline (Assisted/Executive
mode already works the pending list — this chapter changes the order it
works it in, not the mechanism itself).

## Dependencies

Chapter 55 (Executive Decision Simulator — the Decision Score/Expected
Value this chapter reuses), Chapter 56 (Enterprise Portfolio
Intelligence — cash/heat/category exposure), Chapter 57 (Institutional
Position Sizing — the weekly budget and cash reserve floor this
chapter's reservation sits on top of), Chapter 58 (Institutional Trade
Filter & Opportunity Gatekeeper — the approved-candidate pool this
chapter ranks). **A note on the brief's other named dependency:**
"Chapter 53 — Probabilistic Trading Philosophy" does not exist anywhere
in this codebase or Design Bible under that number or title — checked
directly, the same way this exact non-existent reference was already
checked and flagged in Chapter 58's own Dependencies section. The
brief's own numbering is also consistently off-by-one from this
codebase's real numbering for the Executive Decision Simulator and
Enterprise Portfolio Intelligence chapters (its "Chapter 54"/"Chapter
55" are this Design Bible's real Chapter 55/56) — noted once here
rather than re-litigated per section.

## Connected Features

Chapter 57 (Position Sizing, downstream — still decides individual
trade size once this chapter decides allocation order), Chapter 58
(Opportunity Gatekeeper, upstream — still decides pass/fail before this
chapter ever sees a candidate), Chapter 60 (Portfolio Rebalancing, the
natural next chapter — this chapter's ranked queue is exactly the real
input Chapter 60's own "compare open positions against new
opportunities" design needs).

## Future Expansion

Multiple Brokers/Portfolios, Institutional Funds, Client Accounts,
Cross-Market Allocation all require real infrastructure this codebase
doesn't have yet (a live broker, in particular — see
`docs/DesignBible/volumes/10-broker-live-trading.md`'s own "does not
exist today" note). Machine Learning Capital Rotation and Dynamic
Opportunity Forecasting are real future directions, not invented or
stubbed here.

## Company Principle

Good trades deserve consideration. Great trades deserve capital. Every
dollar must compete for the privilege of entering the market.

## Implementation Notes

**What's real today:** the entire scoring machinery this chapter needs
— `DecisionScoreBreakdown`, `ExpectedValueAnalysis` (Chapter 55),
`PositionSizingResult` and the real weekly deployment budget/cash
reserve floor (Chapter 57), the Opportunity Gatekeeper's approved-
candidate pool (Chapter 58), `PortfolioIntelligence`'s cash/heat/
category-exposure reads and its real (if currently qualitative-only)
`opportunityCost` field (Chapter 56); `RiskLimits.maxOpenPositions`/
`maxSectorConcentrationPct` (already real CEO controls).

**What's genuinely new in this chapter:** sorting the pending
`trade_proposals` queue by Priority Score (reusing `decisionScore.overall`
directly, not a second composite) instead of arrival order — the exact
gap Chapter 58's own Implementation Notes already flagged as unbuilt; a
CEO-configurable Minimum Priority Score and an additive Capital Reserve
% control layered on top of Chapter 57's existing floor; capital
allocating from the top of the ranked queue downward rather than
first-come-first-served when a real constraint (weekly budget, cash
reserve) would otherwise be exceeded.

**What's explicitly out of scope until named gaps close:** Replacement
Analysis against already-open positions (Chapter 60's job entirely, not
this chapter's); Swing vs. Day allocation ratio (no real distinct
trading modes exist); "Missed Opportunity Rate" as the brief frames it
(would require knowledge of opportunities that were never real
candidates at all — fabrication, not analysis).

**What was actually built (backend):** a new `app/capital_priority.py`
module with three functions — `priority_score()` (looks up a proposal's
own `WarRoomSession.decisionScore.overall` by `proposalId`, the same
reused number shown everywhere else — never a second composite),
`rank_trade_proposals()` (a stable sort of the pending queue, highest
score first, unscored proposals sort last rather than crashing), and
`cash_reserve_breached()` (true once cash as a % of equity is at or
below the CEO's `capitalReservePct`, additive to Chapter 57's hard
`cashReservePct` floor). Two new `RiskLimits` fields —
`minPriorityScore` and `capitalReservePct` — both default to `0.0`
(no-op/opt-in, since neither replaces prior fixed behavior), writable
via the existing `POST /api/risk-limits` endpoint
(`app/routers/risk.py`, `app/state.py`'s `update_risk_limits`), each
validated to a `0`–`100` percentage range the same way
`minTradeQualityScore`/`cashReservePct` already are. `app/nexus.py` now
re-sorts the *entire* pending queue by Priority Score every tick right
after new proposals are appended (not just the tick's new arrivals), so
switching CEO controls mid-game re-orders the existing backlog too.
`_apply_operating_mode()` gained two new real gates in its per-proposal
loop: a proposal below `minPriorityScore` is "significant" the same way
a low-confidence one already is (`app/executive.py`'s
`is_significant_proposal()` grew a new optional `priority_score`
parameter) — Assisted Mode only, since Executive Mode's whole point is
auto-resolving everything unconditionally; and once
`cash_reserve_breached()` is true, further BUY proposals stay pending in
**both** modes, since a real capital constraint (unlike a significance
judgment) applies regardless of how hands-off the CEO wants to be —
mirroring how Chapter 57's own hard `cashReservePct` floor already
applies unconditionally. Verified with `mypy`/`ruff` clean, 23 new unit
tests (`tests/test_capital_priority.py`, plus new cases in
`tests/test_executive.py` and `tests/test_state.py`) covering ranking,
stability, the missing-session case, both new CEO controls' boundaries,
and a live 400-tick simulation smoke test confirming the queue stays
sorted every tick and both gates produce real, observable holds.

**What was actually built (frontend):** `types.ts` mirrors the two new
`RiskLimits` fields; `net/api.ts`'s `updateRiskLimits()` accepts both.
The **EXECUTIVE tab**'s Pending Proposals list — already receiving the
queue in its real, backend-ranked order (the WS payload's
`tradeProposals` is the exact same list `rank_trade_proposals()` sorts
server-side, so no client-side re-sort was needed) — now shows each
proposal's rank number and its real Priority Score, read via a new
`priorityScoreFor()` helper (`derive.ts`) that looks up the same
`WarRoomSession.decisionScore.overall` by `proposalId` the backend's own
`priority_score()` reads, mirrored exactly rather than re-derived. The
**RISK tab** gained a "Capital Priority — Opportunity Cost" panel with
controls for `minPriorityScore`/`capitalReservePct`, following the same
per-section save-button pattern every other RISK tab control already
uses. Verified with `tsc --noEmit`, `eslint --max-warnings 0`, and
`vite build` all clean, plus two new Playwright tests against the live
Vite + FastAPI stack: one confirms the RISK tab's Capital Priority
controls round-trip a real save, one confirms the EXECUTIVE tab renders
either a real Priority Score or the honest "N/A" for an unlinked
proposal.
