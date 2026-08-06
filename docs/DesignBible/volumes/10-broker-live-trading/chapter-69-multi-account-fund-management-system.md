# Chapter 69 — Multi-Account & Fund Management System (MAFMS)

**Status:** Pure architecture, not yet implemented — same posture as
[Chapter 68](chapter-68-institutional-broker-management-system.md).
This chapter now has three parts, all filed under Chapter 69 per
explicit correction: **Part 1** is the original Multi-Account & Fund
Management System brief. **Part 2** is the Prop Firm Rule Engine
(previously drafted as a standalone "Chapter 70," including its own
addendum) — merged in here rather than kept as a separate chapter
number. **Part 3** is the Institutional Rule Engine (previously drafted
as a standalone "Chapter 71") — merged in for the same reason. Each
part keeps its own full structure (Executive Summary through
Implementation Notes) rather than being flattened into one undivided
document, since each was researched and written as its own coherent
system; they're organized together here because that's how they're
meant to be read and maintained, not because their content overlaps.

---

## Part 1 — Multi-Account & Fund Management System

**Researched first:** this codebase's entire save state
(`GameSaveState`, `app/schemas.py`) holds exactly one trading ledger
(`PaperPortfolio`, its own docstring: "the company's one simulated
trading account") and one other, genuinely isolated capital pool
(`TreasuryState`, the CEO's personal treasury — `TreasuryPanel.tsx`'s
own "isolated second account" framing, Chapter 67's navigation notes).
Two pools, both hardcoded, neither carrying an account ID, type, owner,
or permission set. That's the real ceiling this part's architecture has
to grow past — not a redesign, an addition. See Part 1's own
Implementation Notes below for the precise inventory.

### Executive Summary

TradeTown has never managed more than one trading account at a time.
**Researched first:** the one real precedent for "capital in two
places, cleanly separated" already exists — `PaperPortfolio` (trading
capital) and `TreasuryState` (the CEO's personal capital) are two
genuinely independent balances with their own transaction histories,
and nothing in this codebase mixes them without an explicit deposit/
withdraw transaction. What doesn't exist is everything past that: a
generalized N-account model, account types, per-account risk profiles
or permissions, account switching, cross-account aggregation, or
anything resembling Fund Mode or Client Mode. This part describes the
architecture that would generalize the real two-pool precedent into the
brief's own account hierarchy — CEO → Master Portfolio → Account Groups
→ Individual Accounts → Strategies → Positions — without inventing any
of the intermediate real estate that doesn't exist yet.

### Company Philosophy

"Capital may belong to different accounts; intelligence belongs to
TradeTown; knowledge is shared; risk remains isolated" is not a new
principle for this codebase to adopt — it is, narrowly, already true.
Company Memory and the Knowledge Graph (Chapter 61) are real, global,
and already shared across every real system that touches the one
trading account that exists; nothing here would need to change for a
second account to benefit from the same shared knowledge. What isn't
proven yet is the "risk remains isolated" half at scale, since there
has only ever been one account's risk to isolate.

### Primary Responsibilities

**Would own:** Multi-Account Management, Portfolio Separation, Fund
Management, Account Permissions, Capital Allocation (account-level),
Account Reporting, Account Switching, Master Portfolio View,
Cross-Account Analytics, Performance Attribution (by account/broker).

**Does NOT own** (matches the brief, and matches this codebase's real
division of labor): Trade Research (Chapter 8), Trade Approval (the
CEO's own decision), Risk Authority (Chapters 57/58/66's real pre-trade
veto pipeline — this part would assign a risk *profile* to an account,
never compute or override a risk decision itself), Broker Communication
(Chapter 68's own real boundary), Execution Logic (`app/broker.py`),
and rule *enforcement* itself (Part 3 of this chapter, the Institutional
Rule Engine, is the only system that would ever enforce a rule for any
account).

### Ownership

Every brief concept checked against the real codebase before this part
was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Multi-Account Management" / "Account Hierarchy" | *(genuinely does not exist)* | `GameSaveState` holds exactly one `PaperPortfolio` and one `TreasuryState` — two hardcoded fields, not a list of N accounts with IDs to iterate over. There is no `AccountGroup`, no `Strategy`-to-`Account` link (Chapter 45's Research Sandbox `Strategy` objects belong to the company, not to any one account), and no code path that could "create" or "archive" an account today. |
| "Portfolio Separation" / "Account Isolation" | `PaperPortfolio` + `TreasuryState` (`app/schemas.py`, `app/treasury.py`) | The one real, working precedent for this entire part: two independent balances, each with its own transaction history (`PaperTrade`/`PaperOrder` vs. `TreasuryTransaction`), moved between only via an explicit deposit/withdraw call — never mixed silently. **Incomplete even for these two:** `RiskLimits` and Operating Mode (the real automation-level control) are each a single global object/setting, not scoped per-pool — a real gap even in today's narrower two-pool world, before a third account is ever added. |
| "Fund Management" (NAV, investor capital, contributions/withdrawals) | *(genuinely does not exist)* | No Net Asset Value concept, no investor-vs-fund capital distinction anywhere. `TreasuryState` tracks deposits/withdrawals for the CEO's own personal capital only — the closest real analog, and a single-owner one. |
| "Account Permissions" (View Only/Research Only/Paper/Manual/Automation/Execution/Transfers/Admin) | Operating Mode (`learning`/`assisted`/`executive`, `app/schemas.py`) | Real, but a single global AI-autonomy dial, not a per-account permission matrix — it changes how much of the *existing* proposal-resolution pipeline runs unattended, not who can view, trade, or transfer within a given account. No granular permission concept exists at all. |
| "Capital Allocation" (Company → Account → Position) | Chapter 57's Position Sizing (`app/nexus.py`), Chapter 59's Capital Priority (`app/capital_priority.py`) | Real, but two levels, not three: company-level cash-reserve/position-sizing math flows straight to position-level sizing, because there is only one account's capital to size against — the brief's middle "Account Level" has nothing to sit between yet. |
| "Account Reporting" | `TreasuryMonthlyReport` (`app/schemas.py`) | Real, and the one genuine precedent for a *named, persisted, per-period* report object in this whole part — but scoped to Treasury alone. `PaperPortfolio`'s own performance is always computed live off the ledger (`computePeriodFinancials()`), never archived into an equivalent `PortfolioMonthlyReport`. |
| "Account Switching" | *(does not exist)* | There is nothing to switch between — the Command Center already shows the one `PaperPortfolio` and the one `TreasuryState` simultaneously, on their own tabs (RISK/PORTFOLIO and TREASURY), not as alternate contexts to toggle. |
| "Master Dashboard" / "Master Portfolio View" / "Cross-Account Analytics" | *(does not exist)* | Nothing to aggregate — Total AUM, Per-Account P&L, Broker Distribution, and every other master-dashboard metric the brief lists require 2+ real accounts to compute honestly, and only one exists. |
| "Performance Attribution" (by account/broker/strategy/sector/timeframe/regime/employee/capital source) | Partially real, narrowly: by employee (`supportingAgents`/`opposingAgents` on every `PaperTrade`) and by timeframe (`computePeriodFinancials`'s daily/weekly/monthly/all-time periods) are both real today. **Not real:** by account or broker (only one of each exists to attribute against), by sector (no sector taxonomy exists on `PaperTrade`), by market regime (Chapter 65's regime read is real but never joined against trade P&L as an attribution dimension). |
| "Account Groups" | *(does not exist)* | No grouping concept anywhere — matches "Account Switching" above; nothing exists yet to group. |
| "Client Mode" / "Fund Mode" | *(does not exist — the brief's own framing, "future-ready architecture" and "future institutional support," already says so)* | Honored here at face value rather than re-litigated: these are named future work in the brief itself, not a gap this research needed to discover. |

### Inputs

**Would receive, once real:** account credentials/permissions from
Chapter 68's IBMS (does not exist — Chapter 68 is itself pure
architecture), a CEO-assigned risk profile per account (the underlying
`RiskLimits` machinery is real; per-account assignment is not), a
CEO-assigned objective/strategy preference per account (does not
exist). **Real today:** the two real capital pools themselves
(`PaperPortfolio`, `TreasuryState`) are the one honest input this
part's architecture would generalize from.

### Outputs

**Would produce, once real:** Master Portfolio, Account Context,
Capital Distribution, cross-account Performance Data, Account Reports,
Executive Analytics scoped per account. **Real today:** `PaperPortfolio`'s
live performance figures and `TreasuryMonthlyReport` — the same two
real, single-scope outputs already described under Ownership.

### Internal Workflow

**The brief's own two-level Capital Allocation flow (Company → Account
→ Position), checked against what's real:** Company Level (real —
`RiskLimits`' cash-reserve floor) → *Account Level* (does not exist —
nothing between the company and a position to allocate through) →
Position Level (real — Chapter 57's Position Sizing). A real
implementation would insert exactly one new stage into an existing,
real pipeline, not replace it.

### Decision Logic

**Not real, for the whole part:** no formula exists for account
prioritization, capital distribution across accounts, or per-account
risk-profile derivation, because there is only one account's capital to
distribute today. **Real precedent to build from:** Chapter 59's
Capital Priority engine already ranks *opportunities* against one
account's available capital with a real, transparent formula — the
same shape a future cross-account allocator would need, one level up.

### Department Cooperation

**Would receive from:** Chapter 68 (IBMS — itself pure architecture, so
this part inherits the same "not yet real" status transitively, since a
real multi-account model presumes real per-account broker connections
that don't exist), Chapters 57/58/66 (Risk Authority — real, would
supply the risk-check machinery any per-account profile assigns, never
duplicated), Chapter 56-adjacent Portfolio Intelligence (real, single-
account today), Chapter 61 (Knowledge Graph/Company Memory — real,
already shared company-wide, would need no change to serve a second
account), Chapter 62 (Innovation Lab — real). **Would provide:** Master
Portfolio (does not exist), Account Context (does not exist), Capital
Distribution (does not exist), Performance Data (real, single-account
today), Account Reports (Treasury's own real report is the closest
analog), Executive Analytics (Feature 24's real `ExecutiveReview` is
company-wide, not multi-account).

### CEO Controls

| Control | Status |
|---|---|
| Create Account / Archive Account | **Not built** — no account model exists to create or archive an instance of. |
| Switch Account | **Not built** — nothing to switch between. |
| Group Accounts | **Not built.** |
| Transfer Settings (between accounts) | **Not built** — the one real transfer mechanism, `TreasuryTransaction` deposit/withdraw, moves capital between the two existing hardcoded pools, not between CEO-created accounts. |
| Assign Strategy / Assign Risk Profile | **Not built** — `RiskLimits` is real but global, not an assignable per-account profile. |
| Enable/Disable Automation | **Partially real, globally scoped** — Operating Mode already toggles automation level company-wide; there is no per-account equivalent. |
| Paper Trading / Live Trading | **Not a real toggle, same finding as Chapter 68** — every account this codebase has ever had is paper; there is nothing live to switch to. |

### Security

**Real today: nothing to secure**, for the same reason as Chapter 68 —
no per-account credential, API key, or permission exists yet to leak,
because no second broker-connected account exists. This part's own
"never expose one account's credentials to another" requirement is
inherited directly from Chapter 68's Security section and stays
unbuilt for the identical reason: no credential storage exists in this
codebase at all yet.

### Reports

**Not built, for six of the brief's eight:** Master Portfolio Report,
Account Performance Report, Capital Allocation Report, Fund Report,
Client Report, Risk Distribution Report — all require 2+ real accounts
to report across. **Real today, and the closest honest analog to
"Account Performance Report":** `TreasuryMonthlyReport`, scoped to the
one Treasury pool. **Real today, company-wide, the closest analog to
"Executive Summary":** Feature 24's monthly `ExecutiveReview`
(`app/executive_review.py`).

### KPIs

**A trap worth naming explicitly, the same shape as Chapter 68's
Execution Success Rate warning:** "Assets Under Management" could
technically be computed today as `cashBalance + treasury.balance` — a
real, trivial two-term sum — but reporting it under the name "AUM"
would imply a real multi-account aggregation this system doesn't have.
The honest move is not to surface it under that name until it actually
aggregates something. **Not honestly computable, for the rest of the
brief's list:** Account Growth, Account Health, Diversification across
accounts, Automation Utilization across accounts, Client Satisfaction
(explicitly future, per the brief itself).

### Learning System

**Already real, company-wide, for the "knowledge is shared" half of
this part's own philosophy:** Company Memory and the Knowledge Graph
(Chapter 61) are real and global today — nothing about them is scoped
to a single account, so a second account would inherit the same shared
institutional knowledge with no change required. **Not yet
demonstrable:** the "individual accounts remain independent" half,
since there's only ever been one account whose isolated performance
could be tested against the shared-knowledge half.

### Dependencies

Chapter 68 (Institutional Broker Management System) — matches the
brief's own stated dependency exactly, and transitively means this part
cannot become real before IBMS does, since a second account without a
real broker connection behind it is just a second hardcoded pool, not
the brief's own vision. All previous Design Bible chapters, per the
brief's own honest framing (the same "ALL PREVIOUS DESIGN BIBLE
CHAPTERS" dependency Chapter 66's own brief already used correctly).

### Future Expansion

Unlimited Accounts, Unlimited Brokers, Family Office Management, RIA
Support, Hedge Fund Operations, Institutional Clients, Fractional
Account Management, Global Multi-Currency Accounts, Cross-Broker
Portfolio Management — every one of these requires both a real
multi-account foundation and real broker connections, neither of which
exist. Matches Chapter 66's and Chapter 68's own Future Expansion
precedent: not invented or stubbed here, because nothing here has the
real foundation to build on yet.

### Design Bible Integration

**Real today, for the one account that exists, and would need no
change to keep working for a second:** Company Memory, Knowledge Graph,
Portfolio Intelligence, Company Health, Executive Dashboard, and Risk
Authority all already consume `PaperPortfolio`'s real state and would
extend to a real second account without a rewrite, since none of them
hardcode a single-account assumption into their own logic — they simply
have never been asked to read a second one. **Not built:** a named,
distinct "Audit Center" surface (the same Chapter 68 finding, carried
over unchanged).

### Company Principle

"One company. One brain." is, narrowly, already true — trivially, when
there is only one account for that one brain to manage. Its deeper
meaning — one shared intelligence serving many separately-risked
accounts at once — is exactly what this part's architecture exists to
make possible, and exactly what hasn't been tested yet, because it has
never had a second account to prove itself against.

### Supported Account Types / Portfolio DNA Examples

**Genuinely, entirely unbuilt as configurable account types** — Personal
Brokerage, IRA/Roth IRA, Business Account, Prop Firm Account, and
Family Account all require the account model this part's Ownership
section already confirmed doesn't exist. **A real, working exception
worth calling out precisely:** the Prop Firm profile's own named
"Special Rules" — Daily Loss Limits, Maximum Drawdown, Position Size
Limits — are not aspirational. `RiskLimits`' `maxDailyLossPct`,
`maxDrawdownPct`, and `maxPositionPct` fields (Chapter 57) already
implement exactly this machinery, enforced today by
`app/risk_engine.py`'s `evaluate_sentinel_risk()` — just scoped
globally to the one account that exists, never as an assignable
per-account profile a CEO could attach specifically to a "Prop Firm"
account type. See Part 2 of this chapter for the full Prop Firm rule
set this profile would carry.

### Part 1 Implementation Notes

**What's real today, found by direct research before this part was
written, not assumed:** two genuinely isolated capital pools
(`PaperPortfolio`, the company's trading account; `TreasuryState`, the
CEO's personal capital), each with its own real, independent
transaction history, moved between only via an explicit, logged
transfer — the one real precedent this whole part's architecture would
generalize; a real, working per-period report object
(`TreasuryMonthlyReport`) for the Treasury pool specifically; real,
already-global Company Memory/Knowledge Graph sharing that would need
no change to serve a second account; and real risk-limit machinery
(`RiskLimits`, Chapter 57/66's enforcement) that already implements
the Prop Firm profile's own named special rules, just not as an
assignable per-account configuration. **What's genuinely, entirely
unbuilt:** a generalized N-account model of any kind, account types,
account IDs/owners/permissions, account switching, account groups,
cross-account aggregation or a Master Dashboard, Fund Mode, Client
Mode, and every KPI/report that depends on 2+ real accounts existing
to compute against. No code was written against this part — pure
architecture, matching Chapter 68's own posture exactly, and gated by
the same [Live Trading Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by, since this part's own real value depends on
IBMS becoming real first.

---

## Part 2 — Prop Firm Rule Engine

**Researched first:** this is the part of this chapter with the
*strongest* real backing found in this whole volume — nearly every
"Supported Rule" the brief lists either already exists as real,
enforced machinery under a different scope (daily, not challenge/
trailing), or maps directly onto `DailyObjectiveStatus`, a real,
already-live, per-day compliance readout. What's missing is narrower
and more precise than Part 1's near-total gaps: trailing drawdown,
consistency rules, leverage, scaling milestones, and challenge-scoped
(rather than daily-scoped) tracking. See Part 2's own Implementation
Notes below for the exact split. **A follow-up addendum** (Trailing
Drawdown Engine, Consistency Rule Engine, Leverage System, Scaling
Milestones, Challenge Windows, Weekday-Aware Time System, Prop Firm
Calendar, Compliance Score) is folded directly into this part's own
Ownership and a dedicated "Implementation Requirements Addendum"
section below, rather than kept separate. **The same addendum also
introduced a real architectural correction, covered in full in Part 3
of this chapter (the Institutional Rule Engine):** this part's own
rules must never become a standalone, independent enforcement system —
they become one Rule Profile loaded into the single centralized engine
every account type shares. This part still owns *which* rules a Prop
Firm account needs; Part 3 owns *how* any account's rules get enforced.

### Executive Summary

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
today, but the enforcement shape this part asks for already exists and
already works.

### Company Philosophy

"Passing and protecting funded accounts always takes priority over
maximizing profit" is not a new posture for this codebase to adopt —
it's the same posture Chapter 66's own Company Philosophy already
states ("survival comes first, profit comes second") for the one
account that exists today. A Prop Firm account would inherit that same
discipline, scoped tighter.

### Primary Responsibilities

**Would own:** the fifteen supported prop firm rules, pre-trade
validation against all of them, live account monitoring, proactive
warnings, account-protection recommendations, and the Prop Firm
Dashboard.

**Does NOT own** (matches this codebase's real division of labor):
Trade Decisions (the analyst desk), Trade Approval (the CEO, or
auto-resolution per Operating Mode), general Risk Authority (Chapters
57/58/66 — this part would sit *inside* that same pipeline as one more
account-type-specific check, never a second, parallel veto system),
Broker Communication (Chapter 68), Account Management (Part 1 of this
chapter owns the account type itself; this part owns only the rule set
a Prop Firm-typed account would carry), **and rule *enforcement*
itself** — this part defines which rules a Prop Firm account needs
(the fifteen supported rules plus the eight addendum systems below);
Part 3 of this chapter's centralized Institutional Rule Engine is the
only system that ever actually enforces any rule, for any account
type. This part must never grow its own independent enforcement path.

### Implementation Requirements Addendum

Eight systems named as "mandatory for a complete institutional-grade
Prop Firm Rule Engine," each checked against the real codebase before
being added here — every one of them lands on the "genuinely unbuilt"
side of this part's own Ownership table below, so this section adds
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
concept (does not exist) and Part 1's own account model (does not
exist, since a milestone is meaningless without a specific account to
track it against).

**5. Challenge Windows.** Requires a bounded time window (30/60/90-day
or unlimited) distinct from the sim's own unbounded day counter, plus
daily-pace-required math derived from days remaining and progress so
far. Neither exists — `TimeState.day` counts up forever with no
concept of "this challenge started on day N and must finish by day
N+30."

**6. Weekday-Aware Time System.** Confirmed by direct inspection:
`TimeState` (`app/schemas.py`) is exactly `{day: int, hour: int,
minute: int}` — no weekday, week number, month, quarter, year, market
session, or holiday field exists anywhere. This is real, load-bearing
infrastructure work, not a Prop Firm-specific add-on — Weekend Holding
Rules, Minimum Trading Days, News Blackout Days, and Challenge Windows
above all depend on it directly, and it would be a real, honest,
standalone backend slice (extending `TimeState` and whatever derives
sim days into weekdays) if this part's architecture is ever
implemented.

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

### Ownership

Every one of the brief's fifteen "Supported Rules," checked against the
real codebase before this part was written:

| Supported rule | Real system today | What it actually does |
|---|---|---|
| Daily Loss Limit | `RiskLimits.maxDailyLossPct` (Ch57), enforced in `evaluate_sentinel_risk()` | Real, live, checked every relevant tick — the strongest real match in this whole part. |
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
| Account Scaling Milestones | *(does not exist)* | No account-growth-triggers-a-new-limit-tier concept anywhere — also depends on Part 1's own account model, which doesn't exist yet. |
| Time-Based Restrictions | *(does not exist)* | `TimeState` is `{day, hour, minute}` only — nothing gates trading to specific hours today; agents and the sim run continuously. |
| Weekend Holding Rules | *(does not exist)* | No day-of-week concept exists anywhere in `TimeState` — there is no calendar to check a "weekend" against, let alone a rule enforcing flat-by-Friday. |
| Broker-Specific Rules | *(explicitly future, per the brief's own "(future)" tag)* | Honored at face value — depends on Chapter 68's real broker connections, which don't exist. |

**Score: 6 of 15 already real and enforced** (Daily Loss, Overall
Drawdown, Position Size, Risk Per Trade, Open Positions — five
directly, plus Profit Targets in a related daily-scoped shape) — by far
the highest real-coverage ratio of any part in this chapter, precisely
because this brief asks for machinery Chapter 57 and Chapter 66 already
built for the one account that exists.

### Inputs

**Real today:** every `RiskLimits` field listed as real above, and
`DailyObjectiveStatus`'s live daily counters. **Would need, once Part
1's account model is real:** a per-account rule profile (this part's
own scope) distinct from the single global `RiskLimits` object that
exists today.

### Outputs

**Real today:** a critical `RiskWarning` on the first violated limit,
`DailyObjectiveStatus.tradingHalted`/`haltReason`. **Would produce,
once real:** Challenge Progress, Rule Compliance Score, Account Health
Score scoped to a Prop Firm challenge specifically — none of which
exist as named, computed outputs today.

### Internal Workflow

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

### Decision Logic

**Real today, for the six confirmed-real rules:** each is a
transparent, named threshold check, no hidden weighting — matches this
codebase's "no black-box composite" convention throughout, same as
every other risk formula in Chapters 57/58/66. **Not real:** any
formula for trailing-drawdown recalculation, consistency-rule
percentage math, or a combined Rule Compliance Score across multiple
rules — today each real check is independent, never combined into one
composite readout the way the brief's own Prop Firm Dashboard implies.

### Department Cooperation

**Would receive from:** Part 1 of this chapter (the Prop Firm account
type this part's rules would attach to — does not exist yet), Chapters
57/58/66 (the real risk-check machinery six of this part's fifteen
rules already are), Chapter 67 (the real sticky-critical-toast + Alert
Center delivery mechanism this part's Warning System would use).
**Would provide:** Rule Compliance state to the Executive Dashboard
(Chapter 67's real `useDashboardData()` hook would be the natural
integration point once this part has real data to contribute),
account-protection recommendations to the CEO.

### CEO Controls

| Control | Status |
|---|---|
| Enable Prop Firm Rule Set on an account | **Not built** — depends on Part 1's account-type model, which doesn't exist. |
| Configure Daily Loss / Drawdown / Position Size / Risk Per Trade / Open Positions | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today. |
| Configure Trailing Drawdown / Consistency Rules / Leverage / Scaling Milestones | **Not built** — no underlying computation exists for any of these four yet. |
| Weekend Holding Rules (configurable) | **Not built** — no day-of-week concept exists to configure a rule against. |
| Auto-pause on rule-violation risk ("if CEO approval settings allow") | **Not built as a settings-gated auto-pause specifically** — the closest real precedent is Chapter 66's AI Consensus Safety `pause_trading` enforcement, a real system-triggered pause, but for department disagreement, not rule-violation proximity. Emergency Stop (Chapter 67) is real but CEO-triggered only, never system-initiated. |

### Warning System

**The brief's own example warnings, checked against real delivery
infrastructure:** "One additional full-loss trade could violate today's
drawdown," "Maximum exposure nearly reached," "Trading should stop for
today" — none of these specific messages are generated today, but the
delivery mechanism they'd use is real and already built: Chapter 67's
sticky, non-auto-dismissing critical-tier toast (added for Risk
Warnings and Emergency Stop activation) plus the Executive Alert
Center's recorded history. A real Prop Firm proximity-warning generator
would be new logic; the pipe it would push through already exists.
"Challenge target is 82% complete" specifically depends on this part's
own challenge-scoped tracking, which doesn't exist yet.

### Account Protection

**Two of the brief's five protective recommendations have zero real
backing under any name:** "Switch to swing trading" (Chapter 67's own
Command Palette research already confirmed no such mode exists under
any name) and "Research only" as a distinct enforced mode (the closest
real analog, `learning` Operating Mode, still allows manual CEO trades
— it restricts automation, not all trading). **Two are real, but
CEO-triggered only, never system-initiated:** Emergency Stop (full
pause) and, loosely, reducing position size (the CEO can already edit
`RiskLimits` manually at any time — there's no AI-recommended, one-click
"reduce size for this account" action). **"End the trading session"**
has no real analog — there is no session concept distinct from the
always-running sim clock.

### Prop Firm Dashboard

**Genuinely unbuilt as a named, dedicated dashboard** — but seven of
its nine listed metrics already have a real, live, close analog: Daily
Loss Remaining and Maximum Drawdown Remaining (derivable today from
`RiskLimits` minus `DailyObjectiveStatus`'s live P&L), Profit Target
(`dailyProfitTargetPct`, daily-scoped), Trading Days Completed (no real
counter, see Ownership), Rule Compliance Score (no real composite
score, only independent real checks), Account Health Score (Chapter
63's real `CompanyHealth.overall` is the closest analog, company-wide
not account-scoped), Capital at Risk (real — sum of open position
exposure already computed for `maxPositionPct` checks). **Challenge
Progress specifically remains the one metric with no real foundation at
all** — it presumes the challenge-window tracking this part's Ownership
section already confirmed doesn't exist.

### Security

No new surface — inherits Chapter 68's and Part 1's identical finding:
no broker credential or per-account permission exists anywhere yet for
a Prop Firm rule set to need to secure differently from any other
account.

### Reports

**Not built.** No named Prop Firm-specific report object exists.
`DailyObjectiveStatus` is the closest real, live analog (see Live
Account Monitoring / Ownership above) but is never archived into a
persisted report series the way `TreasuryMonthlyReport` or
`CoachReport` already are for their own domains.

### KPIs

**Real and computable today, if scoped honestly to "daily" rather than
"challenge":** compliance against the six confirmed-real rules above.
**Not honestly computable:** a combined Rule Compliance Score,
Challenge Progress percentage, or Trading Days Completed — each depends
on tracking this codebase doesn't do yet, and reporting a number for
any of them today would fabricate a measurement that never actually
ran, the same trap Chapter 68's KPIs section already named for
Execution Success Rate.

### Learning System

**Not built**, for the same reason as Part 1's and Chapter 68's own
Learning System sections: there's no Prop Firm account, challenge, or
rule violation history to learn from yet, since no Prop Firm account
type exists to generate any.

### Dependencies

Part 1 of this chapter (the Prop Firm account type this part's rules
attach to; itself pure architecture, so this part is gated transitively
behind it), Chapters 57/58/66 (the real risk-check machinery this part
reuses rather than duplicates), Chapter 67 (the real notification-
delivery pipe the Warning System would use). All previous Design Bible
chapters, per the same honest framing Chapters 66/68 already use
correctly.

### Future Expansion

Broker-Specific Rules (per the brief's own "(future)" tag), automatic
account scaling on milestone achievement, and multi-firm rule-set
templates (different prop firms enforce different specific thresholds)
all require Chapter 68's real broker connections and Part 1's real
account model, neither of which exist. Matches this volume's own Future
Expansion precedent exactly.

### Design Bible Integration

**Would integrate with, once real:** the Executive Dashboard (via
Chapter 67's real `useDashboardData()` hook — the natural place a Prop
Firm account's live compliance state would surface once it exists),
Company Memory (a rule violation or near-violation would be exactly the
kind of event `app/scribe.py` already records for other real risk
events today), Risk Authority (this part's own rules would run *inside*
the existing Sentinel/Gatekeeper pipeline, never a second parallel
one). None of this requires new integration design — it reuses seams
Chapters 57/58/61/66/67 already built.

### Company Principle

"TradeTown should think like a disciplined professional trader whose
first objective is to keep the funded account alive" is, today, already
the operating principle of the one real account this codebase has —
Chapter 66's own Company Principle states it in almost identical words
("disciplined survival over reckless growth"). A Prop Firm account
wouldn't need a new philosophy, only a tighter, challenge-scoped,
account-specific version of the same discipline already real and
enforced today.

### Part 2 Implementation Notes

**What's real today, found by direct research before this part was
written, not assumed — the strongest real-coverage ratio of any part in
this chapter:** five of the brief's fifteen supported rules (Daily Loss
Limit, Maximum Overall Drawdown, Maximum Position Size, Maximum Risk
Per Trade, Maximum Open Positions) are already real, enforced,
CEO-configurable `RiskLimits` fields, checked unconditionally every
relevant tick by `evaluate_sentinel_risk()`; a sixth (Profit Targets)
is real in a related daily-scoped shape (`dailyProfitTargetPct`); the
exact "block automatically, explain exactly why" pre-trade shape the
brief asks for is already real and unconditional, via the Trade
Gatekeeper's eight checks (Chapter 58); `DailyObjectiveStatus` is a
real, live, per-day compliance readout —
tradesToday/realizedPnlPctToday/profitTargetReached/maxLossReached/
tradingHalted/haltReason — that already does, daily, most of what the
brief's own Live Account Monitoring and Prop Firm Dashboard ask for at
challenge scope; and Chapter 67's sticky-critical-toast + Alert Center
is real, working delivery infrastructure this part's Warning System
would use rather than invent. **What's genuinely, entirely unbuilt:**
trailing drawdown (no peak-equity tracking exists to trail from),
consistency rules, leverage (this is a 100%-cash account, confirmed by
Chapter 68), account scaling milestones, time-based/weekend
restrictions (no day-of-week concept exists anywhere in `TimeState`),
challenge-scoped (rather than daily-scoped) tracking of any kind,
"Swing Trading Mode" (confirmed absent under any name by Chapter 67's
own research), any system-initiated automatic pause distinct from the
CEO-triggered Emergency Stop, and — transitively — everything that
depends on Part 1's own account model, which is itself pure
architecture. **Also confirmed by direct research for the addendum
above:** no generic rule/rule-profile abstraction and no peak-equity/
high-water-mark field exist anywhere in this codebase's schemas — grep
against every backend module returned zero matches for either. No code
was written against this part. Gated by the same [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by, and — for enforcement specifically — by Part 3
of this chapter, the one centralized system that would ever actually
enforce any rule this part defines.

---

## Part 3 — Institutional Rule Engine (IRE)

**Researched first:** this part's own central claim — "no account type
should implement its own independent rule system; every account loads
its own configurable Rule Profile into one centralized engine" — is the
exact opposite of how this codebase enforces every real risk check
today. `evaluate_sentinel_risk()`, `evaluate_guardian_exposure()`, and
the Trade Gatekeeper's eight checks (Chapters 57/58/66) are real,
working, and deliberately hardcoded Python functions with named, fixed
thresholds — not a data-driven rule interpreter, not organized into
swappable profiles, and not configurable without a code change. That's
not an oversight this part's architecture quietly fixes; it's a genuine
trade-off this part must own honestly: today's hardcoded checks are
simple and auditable by design (this Design Bible's own repeated "no
black-box composite" convention), and any real IRE implementation has
to preserve that same transparency for a CEO-authored rule, never trade
it away for configurability. See Part 3's own Implementation Notes
below for the precise inventory.

### Executive Summary

Every account type this chapter has described so far — Personal, IRA,
Business, Prop Firm, Family (Part 1) — would otherwise tempt a
separate, bespoke rule system per type. This part's own mission is to
prevent that duplication before it starts: one centralized engine, fed
a per-account Rule Profile, enforcing every account's rules the same
way. **Researched first:** the risk-checking *shape* this brief wants —
unconditional, pre-trade, block-and-explain — already exists and
already works, real today, for the one account this codebase has. What
doesn't exist is the *generalization*: today's checks are hardcoded
per-function, not data-driven per-profile, so there is nothing yet a
CEO could point a new account type at without a code change.

### Company Philosophy

"TradeTown should never hard-code account behavior; accounts define
rules, the Institutional Rule Engine enforces them" is a real
architectural commitment this codebase has not made yet — today, every
real risk rule *is* hard-coded, on purpose, readable in one place per
check (`app/risk_engine.py`, `app/gatekeeper.py`), which is exactly how
this Design Bible's own transparency principle ("every decision must be
explainable," Volume 9's own architecture principles) has been honored
so far. Adopting this part's philosophy is not a free upgrade — it
trades some of that today's-code-is-the-documentation simplicity for
real configurability, and a real implementation has to earn that trade,
not just declare it.

### Primary Responsibilities

**Would own:** centralized rule enforcement for every account type,
Rule Profile loading/management, the fourteen-plus Rule Categories, the
Custom Rule Builder, and the Rule Execution Order every trade would
pass through.

**Does NOT own** (matches the brief, and matches this codebase's real
division of labor): Trade Decisions (the analyst desk), Broker
Communication (Chapter 68), Account Management itself (Part 1 owns
*which* accounts exist; the IRE only enforces the rules attached to
them), and — critically — deciding *what* any specific account type's
rules should be (Part 2 owns the Prop Firm rule list; a future part or
chapter would own Personal/IRA/Business/Family's own lists; the IRE
only ever executes them).

### Ownership

Every brief concept checked against the real codebase before this part
was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Institutional Rule Engine" (one centralized enforcer) | *(genuinely does not exist)* | Grep-confirmed: no `Rule`, `RuleProfile`, or `RuleEngine` class or module exists anywhere in `backend/app/`. Every real check is its own named function, called directly by `app/nexus.py`, never through a shared interpreter. |
| "Rule Profiles" (per-account-type rule sets) | *(does not exist)* | `RiskLimits` is one single global object per game save — not a set of named profiles a CEO could pick from, and not attachable to a specific account, since no per-account model exists (Part 1). |
| "Rule Execution Order" (AI Decision → Risk Authority → IRE → Broker Management System → Order Execution) | Real for two of five stages | AI Decision (real — the analyst desk) → Risk Authority (real — Chapters 57/58/66's pre-trade veto pipeline) → *IRE* (does not exist) → *Broker Management System* (Chapter 68, itself pure architecture) → Order Execution (real — `app/broker.py`'s simulated fill). Today's real pipeline skips straight from Risk Authority to Order Execution — the exact same finding Chapter 68's own Internal Workflow section already made independently. |
| "If any rule fails: block, explain, suggest corrective actions, record in Company Memory" | Three of four real today | Block (real — the Trade Gatekeeper's unconditional reject), Explain (real — every real check carries a specific reason string, never generic), Record in Company Memory (real — `app/scribe.py` already records risk-relevant events). **Not real:** "suggest corrective actions" — a rejected proposal today states *why* it failed, never a recommended fix (e.g., "reduce size by X% to comply"). |
| "Rule Categories" (14 named + Future Rule Packs) | Five real, individually, under different names | Capital Rules (real — cash-reserve floor, Ch57), Risk Rules (real — `RiskLimits`), Drawdown Rules (real — `maxDrawdownPct`), Position Rules (real — `maxPositionPct`/`maxOpenPositions`), Automation Rules (real, but singular — Operating Mode, not a rule set). **Not real:** Leverage Rules (no leverage concept, Ch68/Part 2), Broker Rules (no broker, Ch68), Time Rules (no weekday/hour-gating, Part 2's addendum), Market Rules (Chapter 65's regime read is real but never framed as a blocking rule), Account Rules (no account model, Part 1), Strategy Rules (Chapter 45's `Strategy` stage-gating is real but not rule-driven), Tax Rules (no tax concept anywhere in this codebase), Compliance Rules (no compliance framework exists), Custom CEO Rules (no rule-authoring surface exists), Future Rule Packs (aspirational by the brief's own framing). |
| "Custom Rule Builder" (CEO writes rules without code changes) | *(genuinely does not exist)* | No rule-authoring UI, no rule DSL or parser, no natural-language-to-check pipeline anywhere in this codebase. Checked against the brief's own six examples individually — see Custom Rule Builder section below. |

### Inputs

**Real today:** every individual `RiskLimits` field this part's Rule
Categories table confirms real, and Chapter 65's real market
regime/volatility read. **Would need, once real:** a Rule Profile per
account (does not exist — depends on Part 1), a rule-definition format
the Custom Rule Builder could parse (does not exist).

### Outputs

**Real today:** a blocked trade with a real, specific reason (the Trade
Gatekeeper's own output shape). **Would produce, once real:** a
suggested corrective action alongside the block reason, and a
per-account Rule Compliance state distinct from today's single global
risk-warning list.

### Internal Workflow

**The brief's own Rule Execution Order, stage by stage, already covered
in full under Ownership above** — two of five stages real, three (IRE,
Broker Management System, and any account-scoped hand-off between them)
not yet built. A real IRE would insert itself as one new stage between
two real, already-connected ones (Risk Authority and Order Execution),
not replace either.

### Decision Logic

**Real today, for every individually-real check:** each is a
transparent, named threshold comparison — Chapter 66's own "no
black-box composite" convention, restated once more here because it's
the one principle a Custom Rule Builder implementation must not break.
**Not real:** any generic rule-evaluation formula that could take an
arbitrary CEO-authored rule (a string, a DSL expression, whatever form
it eventually takes) and decide pass/fail against live trade data —
this is the one piece of new decision logic this whole part actually
requires, and it doesn't exist in any form yet.

### Department Cooperation

**Would receive from:** Chapters 57/58/66 (Risk Authority — the real
rule logic this engine would centralize, never duplicate), Chapter 68
(Broker Management System — the real next stage in the brief's own
execution order, itself pure architecture), Part 1 (Account
Management — the source of which Rule Profile applies to which
account), Part 2 (the Prop Firm rule list — the first, and so far
only, fully-specified Rule Profile this chapter has written). **Would
provide:** pass/fail decisions with reasons to every account's trade
pipeline, a corrective-action suggestion, and a Company Memory record
for every real block.

### CEO Controls

| Control | Status |
|---|---|
| Select a Rule Profile for an account | **Not built** — no account model (Part 1) and no Rule Profile concept exist yet. |
| Author a Custom Rule | **Not built** — no rule-authoring surface exists anywhere. |
| Configure existing named limits (Daily Loss, Position Size, ...) | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today, for the one account that exists. |
| Enable/disable a Rule Category | **Not built** — rules aren't organized into toggleable categories today; each is its own independent check. |

### Rule Profiles

**Genuinely unbuilt, for all five named examples** (Personal, IRA,
Business, Prop Firm, Family) — this section restates Part 1's own
Portfolio DNA finding rather than re-deriving it: the underlying
machinery several of these profiles would need already exists
(position sizing, daily/weekly/monthly loss limits, the Prop Firm
profile's own special rules per Part 2), just not organized as a named,
selectable, per-account bundle. **The one real exception, already
confirmed by Part 2's own research:** the Prop Firm profile's core
three rules (Daily Loss Limit, Maximum Drawdown, Maximum Position Size)
are the most fully real of any profile in this list — everything else
in a real Prop Firm Rule Profile (Trailing Drawdown, Consistency Rules,
Scaling Milestones, Leverage Rules, Challenge Deadlines) remains
unbuilt per Part 2's own addendum research.

### Rule Categories

Covered in full under Ownership above — five of fourteen real
individually, none organized into a named, toggleable category system.

### Custom Rule Builder

**Checked against each of the brief's own six examples individually,
since "no code changes" claims are exactly the kind of thing this
Design Bible's own conventions require verifying rather than assuming:**

- "Never risk more than 1%" — the underlying number (`riskPerTradePct`)
  is real and CEO-editable today, but only as a fixed schema field, not
  free-form rule text a CEO could type.
- "Never trade after 2:00 PM" / "No trades on Fridays" — both require
  the Weekday-Aware Time System Part 2's addendum already confirmed
  doesn't exist (`TimeState` has no hour-gating or weekday concept to
  check against).
- "Maximum three open positions" — the underlying number
  (`maxOpenPositions`) is real and CEO-editable today, same shape as
  the 1%-risk example above.
- "Only trade when market volatility is below a defined threshold" —
  Chapter 65's real market regime read includes a `high_volatility`/
  `low_volatility` state, but it's never wired as a configurable,
  trade-blocking threshold anywhere.
- "Require AI confidence above 92%" — confidence is a real field on
  every `TradeDecision`, and the Trade Gatekeeper already checks it as
  one of its eight hardcoded checks (Chapter 58) — but the specific
  threshold isn't CEO-configurable as an arbitrary rule; it's a fixed
  constant in code today.

**The honest summary:** three of six examples reference numbers that
are already real, CEO-editable `RiskLimits` fields (just not
free-form-rule-shaped); three reference infrastructure (weekday
awareness, a volatility-threshold hook, a configurable confidence
threshold) that doesn't exist in any form. Building a genuine "CEO
writes a rule, no code change needed" system is real, new work in every
case — even the three real-number examples would need a rule
parser/interpreter layer that doesn't exist today, since editing a
`RiskLimits` field via the API is not the same thing as parsing
free-form rule text.

### Security

No new surface — inherits Chapter 68's, Part 1's, and Part 2's
identical finding: no credential or per-account permission model exists
yet for a Rule Profile to need isolating between accounts.

### Reports

**Not built.** No named IRE-specific report exists. The real per-check
`RiskWarning` history remains the closest live analog, same as every
other part in this chapter.

### KPIs

**Not honestly computable, for a Rule Compliance Score or Rule
Violation Rate across profiles** — no Rule Profile exists yet to score
compliance against, and only one account's worth of real risk-check
history exists to measure from. Reporting either today would fabricate
a cross-account measurement this system has no foundation for, the same
trap named explicitly in Part 2's own KPIs section.

### Learning System

**Not built**, for the same reason as every other part in this
chapter: no Rule Profile or cross-account violation history exists yet
to learn from.

### Dependencies

Chapter 68 (Broker Management System), Part 1 (Multi-Account & Fund
Management — the account model Rule Profiles attach to), and Part 2
(the Prop Firm Rule Profile, the only fully-specified profile so far).
All previous Design Bible chapters, per the same honest framing
Chapters 66/68 already use correctly.

### Future Expansion

Rule Packs distributed or shared across CEOs, machine-learned rule
suggestions, and natural-language rule authoring beyond a fixed DSL all
require the base Custom Rule Builder this part itself confirms doesn't
exist yet. Matches this volume's own Future Expansion precedent exactly
— not invented or stubbed here.

### Design Bible Integration

**Would integrate with, once real:** every chapter that currently
enforces its own hardcoded check (57/58/66) would migrate that check
into a Rule Profile rather than duplicate it — a real, non-trivial
refactor of already-working code, not a greenfield addition layered on
top. Company Memory would record every real rule violation exactly the
way it already records other risk events today.

### Company Principle

"Accounts define rules. The Institutional Rule Engine enforces them."
This is a real, specific architectural commitment this codebase has not
made — today, the code that defines a rule and the code that enforces
it are the same function, which is precisely what has made every
existing risk check simple to audit. Splitting definition from
enforcement is the right long-term direction for a multi-account,
multi-profile future, and it must be built without losing the
transparency that hardcoding has given every real check so far — the
one non-negotiable constraint on any future implementation of this
part.

### Part 3 Implementation Notes

**What's real today, found by direct research before this part was
written, not assumed:** five of fourteen Rule Categories are already
real, individually, as hardcoded checks (Capital, Risk, Drawdown,
Position, and — singularly — Automation via Operating Mode); the
brief's own Rule Execution Order is real for its first two stages (AI
Decision, Risk Authority) and its last stage (Order Execution), with
the middle two (IRE, Broker Management System) both genuinely unbuilt;
every real check already blocks unconditionally and explains why, and
is already recorded into Company Memory — three of the brief's own four
required behaviors on a rule failure are real today, only "suggest
corrective actions" is missing. Grep-confirmed: no
`Rule`/`RuleProfile`/`RuleEngine` class exists anywhere in
`backend/app/`. **What's genuinely, entirely unbuilt:** the centralized
engine itself, any Rule Profile concept, the Custom Rule Builder
(checked against all six of the brief's own examples individually —
three reference already-real numbers with no rule-authoring surface
around them, three reference infrastructure that doesn't exist at all),
and every KPI/report that depends on cross-account or cross-profile
data that doesn't exist yet. No code was written against this part.
Gated by the same [Live Trading Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by.
