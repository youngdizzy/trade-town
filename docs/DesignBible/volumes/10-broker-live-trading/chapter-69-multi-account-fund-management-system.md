# Chapter 69 — Multi-Account & Fund Management System (MAFMS)

**Status:** All three parts now implemented, on the paper-trading side
only — [Chapter 68](chapter-68-institutional-broker-management-system.md)
(the real broker connection this chapter's accounts would eventually
route live orders through) remains explicitly deferred until Chapter
75, per the project's own [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md).
This chapter has three parts, all filed under Chapter 69 per explicit
correction: **Part 1** is the original Multi-Account & Fund Management
System brief — a real `Account` model, capital allocation, and account
switching now exist. **Part 2** is the Prop Firm Rule Engine (previously
drafted as a standalone "Chapter 70," including its own addendum) — the
Weekday-Aware Time System, Trailing Drawdown Engine, Consistency Rule
Engine, Scaling Milestones, Challenge Windows, and a transparent
Compliance Score are now real. **Part 3** is the Institutional Rule
Engine (previously drafted as a standalone "Chapter 71") — a real,
centralized `app/rule_engine.py` now enforces a closed, named set of
per-account Custom Rules, resolving the brief's own configurability-vs-
transparency tension by scope rather than by building a free-text DSL.
Each part keeps its own full structure (Executive Summary through
Implementation Notes) rather than being flattened into one undivided
document, since each was researched and written as its own coherent
system; they're organized together here because that's how they're
meant to be read and maintained, not because their content overlaps.
The original design-time research below (what existed *before* this
implementation pass) is left intact throughout, since it's the accurate
record of what motivated each design decision — each part's own
Implementation Notes section at its end is the place to check for
exactly what was actually built, and the honest boundaries of what
remains unbuilt.

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
| "Multi-Account Management" / "Account Hierarchy" | **Now real** — `GameSaveState.accounts: list[Account]` (`app/schemas.py`, `app/accounts.py`) | A real list of N accounts, each with its own id, name, type, embedded `PaperPortfolio`, and `RiskLimits`, with real `create_account()`/`close_account()` code paths. **Still not real:** `AccountGroup` (no grouping concept — see "Account Groups" below) and a `Strategy`-to-`Account` link (Chapter 45's `Strategy` objects still belong to the company, not to any one account). |
| "Portfolio Separation" / "Account Isolation" | `PaperPortfolio` + `TreasuryState` (`app/schemas.py`, `app/treasury.py`) | The one real, working precedent for this entire part: two independent balances, each with its own transaction history (`PaperTrade`/`PaperOrder` vs. `TreasuryTransaction`), moved between only via an explicit deposit/withdraw call — never mixed silently. **Incomplete even for these two:** `RiskLimits` and Operating Mode (the real automation-level control) are each a single global object/setting, not scoped per-pool — a real gap even in today's narrower two-pool world, before a third account is ever added. |
| "Fund Management" (NAV, investor capital, contributions/withdrawals) | *(genuinely does not exist)* | No Net Asset Value concept, no investor-vs-fund capital distinction anywhere. `TreasuryState` tracks deposits/withdrawals for the CEO's own personal capital only — the closest real analog, and a single-owner one. |
| "Account Permissions" (View Only/Research Only/Paper/Manual/Automation/Execution/Transfers/Admin) | Operating Mode (`learning`/`assisted`/`executive`, `app/schemas.py`) | Still real, but still a single global AI-autonomy dial, not a per-account permission matrix — it changes how much of the *existing* proposal-resolution pipeline runs unattended, not who can view, trade, or transfer within a given account. Now that real accounts exist, this is a genuine, narrower remaining gap rather than a hypothetical one: no granular per-account permission concept exists yet. |
| "Capital Allocation" (Company → Account → Position) | Chapter 57's Position Sizing (`app/nexus.py`), Chapter 59's Capital Priority (`app/capital_priority.py`) | Real, but two levels, not three: company-level cash-reserve/position-sizing math flows straight to position-level sizing, because there is only one account's capital to size against — the brief's middle "Account Level" has nothing to sit between yet. |
| "Account Reporting" | `TreasuryMonthlyReport` (`app/schemas.py`) | Real, and the one genuine precedent for a *named, persisted, per-period* report object in this whole part — but scoped to Treasury alone. `PaperPortfolio`'s own performance is always computed live off the ledger (`computePeriodFinancials()`), never archived into an equivalent `PortfolioMonthlyReport`. |
| "Account Switching" | **Now real** — `POST /api/accounts/switch-active` (`app/schemas.py`'s `GameSaveState.active_account_id`) | A real, persisted "which account is active" pointer the CEO can change. **Still narrower than the brief's own framing:** switching changes which account the CEO is viewing/managing capital for in `AccountsSection`, not which account new trades execute against — the primary `PaperPortfolio` remains the one place trades open (see Part 1's own Implementation Notes). |
| "Master Dashboard" / "Master Portfolio View" / "Cross-Account Analytics" | *(still does not exist)* | Real accounts now exist to aggregate, but nothing does yet — Total AUM, Per-Account P&L, Broker Distribution, and every other master-dashboard metric remain unbuilt; `AccountsSection` lists each account individually, never rolled into one summary view. |
| "Performance Attribution" (by account/broker/strategy/sector/timeframe/regime/employee/capital source) | Partially real, narrowly: by employee (`supportingAgents`/`opposingAgents` on every `PaperTrade`) and by timeframe (`computePeriodFinancials`'s daily/weekly/monthly/all-time periods) are both real today. **Not real:** by account or broker (only one of each exists to attribute against), by sector (no sector taxonomy exists on `PaperTrade`), by market regime (Chapter 65's regime read is real but never joined against trade P&L as an attribution dimension). |
| "Account Groups" | *(does not exist)* | No grouping concept anywhere — matches "Account Switching" above; nothing exists yet to group. |
| "Client Mode" / "Fund Mode" | *(does not exist — the brief's own framing, "future-ready architecture" and "future institutional support," already says so)* | Honored here at face value rather than re-litigated: these are named future work in the brief itself, not a gap this research needed to discover. |

### Inputs

**Still would need, once Chapter 68 is real:** account credentials/
permissions from Chapter 68's IBMS (Chapter 68 itself remains pure
architecture, deferred until Chapter 75). **Now real:** a CEO-assigned
risk profile per account — every `Account` carries its own real
`RiskLimits`, no longer only a single global object. **Still not real:**
a CEO-assigned objective/strategy preference per account. **Real
today, unchanged:** the two original capital pools (`PaperPortfolio`,
`TreasuryState`) plus every real `Account`'s own embedded portfolio.

### Outputs

**Now real:** per-account state (`Account.portfolio`, `Account.
riskLimits`) the CEO can list and act on individually. **Still not
real:** Master Portfolio (a rolled-up cross-account view), Capital
Distribution (a cross-account allocation formula), Executive Analytics
scoped per account. **Real today, unchanged:** `PaperPortfolio`'s live
performance figures and `TreasuryMonthlyReport`.

### Internal Workflow

**The brief's own two-level Capital Allocation flow (Company → Account
→ Position), checked against what's real:** Company Level (real —
`RiskLimits`' cash-reserve floor) → **Account Level (now real — an
`Account`'s own capital, allocated to it via `allocate_capital()`/
`deallocate_capital()`)** → Position Level (real — Chapter 57's Position
Sizing, still scoped to the primary `PaperPortfolio` only — see Part 1's
own Implementation Notes on the live-execution boundary). The one new
stage this brief asked for is real; positions still only open in the
primary portfolio, not inside a specific non-primary `Account`.

### Decision Logic

**Still not real:** no formula exists for account prioritization or
capital distribution *across* accounts (i.e., which account should get
the next dollar) — allocating to a specific account is a real, direct
CEO action (`allocate_capital()`), not yet an automated, ranked
decision. **Real precedent to build from, unchanged:** Chapter 59's
Capital Priority engine already ranks opportunities against one
account's available capital with a real, transparent formula.

### Department Cooperation

**Receives from:** Chapter 68 (IBMS — still pure architecture, deferred
until Chapter 75; a real broker connection per account remains
unbuilt), Chapters 57/58/66 (Risk Authority — real, supplies the
risk-check machinery every `Account`'s own `RiskLimits` already reuses),
Chapter 56-adjacent Portfolio Intelligence (real, still scoped to the
primary portfolio for live-trading purposes), Chapter 61 (Knowledge
Graph/Company Memory — real, already shared company-wide, needed no
change to serve the new accounts), Chapter 62 (Innovation Lab — real).
**Provides:** per-account state to `AccountsSection` (real). **Still
not provided:** a rolled-up Master Portfolio or cross-account Capital
Distribution view (does not exist), Performance Data (real, still
single-portfolio-scoped for live trading today), Account Reports
(Treasury's own real report remains the closest analog), Executive
Analytics (Feature 24's real `ExecutiveReview` is
company-wide, not multi-account).

### CEO Controls

| Control | Status |
|---|---|
| Create Account / Archive Account | **Real** — `POST /api/accounts/create` and `/close` (`app/accounts.py::create_account()`/`close_account()`). |
| Switch Account | **Real** — `POST /api/accounts/switch-active` sets `GameSaveState.active_account_id`. |
| Group Accounts | **Not built** — still no account-grouping concept. |
| Transfer Settings (between accounts) | **Real, for Account ↔ Treasury specifically** — `POST /api/accounts/allocate`/`deallocate` reuse `treasury.py`'s real deposit/withdraw machinery. **Not built:** direct account-to-account transfers (every real transfer still routes through the Treasury as the hub, matching this codebase's existing two-pool precedent rather than inventing a new topology). |
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

**Pre-existing, found by direct research before this part was
written:** two genuinely isolated capital pools (`PaperPortfolio`, the
company's trading account; `TreasuryState`, the CEO's personal
capital), each with its own real, independent transaction history,
moved between only via an explicit, logged transfer; a real, working
per-period report object (`TreasuryMonthlyReport`) for the Treasury pool
specifically; real, already-global Company Memory/Knowledge Graph
sharing; and real risk-limit machinery (`RiskLimits`, Chapter 57/66's
enforcement).

**Built this pass:** a real, generalized `Account` model
(`app/schemas.py`) — id, name, `account_type` (a closed
`personal`/`ira`/`business`/`prop_firm`/`family` set, matching the
brief's own five named types), an embedded `PaperPortfolio` (so every
existing function that already operates on a portfolio, like
`app/risk_engine.py`'s `portfolio_equity()`, works on an Account's
portfolio with no change), and its own editable `RiskLimits` — the
per-account risk profile this part's Ownership table confirmed didn't
exist. `app/accounts.py` (new) implements `create_account()`,
`close_account()`, `allocate_capital()`/`deallocate_capital()` (moving
real capital between an Account and the Treasury, reusing
`treasury.py`'s own real deposit/withdraw machinery rather than
inventing a second transfer mechanism), and account switching via
`GameSaveState.active_account_id`. `POST/GET /api/accounts/*`
(`app/routers/accounts.py`) exposes all of it; `TreasuryPanel.tsx`'s new
`AccountsSection` is the CEO-facing surface.

**Explicit, honest scope boundary (stated in `Account`'s own
docstring):** live trading execution — a new `TradeProposal` opening a
position *in* a specific non-primary account — is not wired. That would
mean parameterizing the entire trading pipeline (proposals, the Trade
Gatekeeper, Sentinel/Guardian) by account, a materially larger change
than this pass makes; every account beyond the primary one is today a
real, CEO-manageable capital ledger, not yet a second place trades can
execute. Named honestly here rather than silently assumed, and carried
into this part's own Future Expansion.

**Still genuinely unbuilt:** account groups, cross-account aggregation
or a Master Dashboard, Fund Mode, Client Mode, and every KPI/report that
depends on 2+ accounts *trading* (as opposed to holding capital) to
compute against. Verified: mypy/ruff clean, `tsc --noEmit`/eslint/`npm
run build` clean, and a full save-module persistence round-trip tested
against the real `GameState` singleton. Gated, for the live-execution
half specifically, by the same [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by.

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

**4. Scaling Milestones.** *(Both requirements below are now real — see
this part's own Implementation Notes; left here as the original
research record.)* Requires both a funded-account growth-stage
concept (did not exist at research time) and Part 1's own account model (did not
exist at research time, since a milestone is meaningless without a specific account to
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
| Trailing Drawdown | **Now real** — `Account.peak_equity` + `compute_trailing_drawdown()` (`app/prop_firm.py`) | A real, continuously-updated peak-equity high-water mark (`app/accounts.py::_with_updated_peak_equity()`), with drawdown recomputed from that moving peak, not a fixed floor — the existing static `maxDrawdownPct` check is kept exactly as-is alongside it, never replaced. |
| Maximum Position Size | `RiskLimits.maxPositionPct` | Real, enforced. |
| Maximum Risk Per Trade | `RiskLimits.riskPerTradePct` | Real, enforced. |
| Maximum Open Positions | `RiskLimits.maxOpenPositions` | Real, enforced. |
| News Trading Restrictions | *(does not exist)* | `ScannerAlert` has news-adjacent alert types (`gap_up`/`gap_down`/etc.) but no blackout-window or trade-blocking logic tied to them. |
| Minimum Trading Days | *(does not exist)* | No "days actually traded" counter distinct from total sim days elapsed — `DailyObjectiveStatus.simDay` tracks the calendar, not trading-day participation. |
| Consistency Rules (no single day &gt; X% of total profit) | **Now real** — `compute_consistency_status()` (`app/prop_firm.py`) | Real per-day P&L bucketed from the account's own closed-trade history, compared against the configured challenge window's real cumulative total — `applicable: false` honestly when no challenge window is configured, rather than fabricating a comparison against nothing. |
| Maximum Leverage | **Confirmed, explicitly, still not applicable** | `LEVERAGE_NOTE` (`app/prop_firm.py`), surfaced on every `PropFirmStatus` response, states outright: "Not applicable — this is a 100% cash, long-only paper account with no margin or leverage concept anywhere in this codebase." A stated boundary, not a fabricated number. |
| Profit Targets | `RiskLimits.dailyProfitTargetPct` (daily) **+ now real challenge-scoped target** — `compute_challenge_progress()` | Daily-scoped target remains real and unchanged. **Now also real, challenge-scoped:** `Account.challenge_profit_target_pct` + `compute_challenge_progress()`'s `onPace` read (required pace = target × days-elapsed/duration), the exact "8% over 30 days" shape the brief asked for. |
| Account Scaling Milestones | **Now real** — `compute_scaling_status()` (`app/prop_firm.py`) | Real, published growth-tier thresholds (`SCALING_TIER_THRESHOLDS_PCT`: 10/25/50/100% equity growth from starting balance) — a transparent step function, never a hidden one, matching this Design Bible's "no black-box composite" convention. |
| Time-Based Restrictions | *(still does not exist)* | `TimeState` remains `{day, hour, minute}` with no hour-of-day gating; nothing blocks trading to specific hours. |
| Weekend Holding Rules | **Weekday awareness now real; enforcement still not built** | `weekday_for()` (`app/prop_firm.py`) is a real, deterministic Weekday-Aware Time System (day 1 = Monday, never stored/driftable) — the load-bearing infrastructure this row previously said didn't exist. It's surfaced on `PropFirmStatus.weekday` today; no rule yet blocks holding a position into a weekend using it. |
| Broker-Specific Rules | *(explicitly future, per the brief's own "(future)" tag)* | Honored at face value — depends on Chapter 68's real broker connections, which don't exist. |

**Score, after this pass: 6 of 15 real and *enforced* (block a trade)**
(Daily Loss, Overall Drawdown, Position Size, Risk Per Trade, Open
Positions, Profit Targets-daily — unchanged from before this pass, all
still enforced by `evaluate_sentinel_risk()`), **plus 4 more now real
and *tracked/computed*, not yet enforced** (Trailing Drawdown,
Consistency, Scaling Milestones, Profit Targets-challenge-scoped —
`app/prop_firm.py`'s own module docstring is explicit: "this module
only computes real, honest status readouts, never blocks a trade
itself" — Part 3's Institutional Rule Engine is the system that would
ever enforce any of these), **1 more genuinely resolved by an honest
non-answer** (Maximum Leverage — `LEVERAGE_NOTE`), and **1 more with
real supporting infrastructure but still no enforcement** (Weekend
Holding — `weekday_for()`). 3 of 15 remain genuinely unbuilt in any
form (News Trading Restrictions, Minimum Trading Days, Time-Based
Restrictions), plus Broker-Specific Rules, still explicitly future per
the brief's own tag.

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

**Receives from:** Part 1 of this chapter (the account model this
part's rules attach to — now real), Chapters 57/58/66 (the real
risk-check machinery six of this part's fifteen rules already are),
Chapter 67 (the real sticky-critical-toast + Alert
Center delivery mechanism this part's Warning System would use).
**Would provide:** Rule Compliance state to the Executive Dashboard
(Chapter 67's real `useDashboardData()` hook would be the natural
integration point once this part has real data to contribute),
account-protection recommendations to the CEO.

### CEO Controls

| Control | Status |
|---|---|
| Enable Prop Firm Rule Set on an account | **Real** — Part 1's `account_type` field supports `prop_firm`, and any account (not only prop-firm-typed ones) can carry the Part 2 fields via `POST /api/accounts/prop-firm/configure`. |
| Configure Daily Loss / Drawdown / Position Size / Risk Per Trade / Open Positions | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today. |
| Configure Trailing Drawdown / Consistency Rules / Scaling Milestones | **Now real** — `POST /api/accounts/prop-firm/configure` sets `trailing_drawdown_limit_pct`/`consistency_limit_pct`; Scaling Milestones compute automatically from equity growth, no configuration needed. **Leverage remains not applicable**, stated via `LEVERAGE_NOTE` rather than a configurable field. |
| Weekend Holding Rules (configurable) | **Weekday awareness now real** (`weekday_for()`), surfaced on `PropFirmStatus.weekday` — **enforcement of a rule against it still not built.** |
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

**Now real as a named endpoint (`GET /api/accounts/prop-firm/status` →
`PropFirmStatus`, rendered by `TreasuryPanel.tsx`'s `PropFirmCard`),
covering eight of the brief's nine listed metrics:** Daily Loss
Remaining and Maximum Drawdown Remaining (derivable from `RiskLimits`
minus `DailyObjectiveStatus`'s live P&L, unchanged), Profit Target
(both the daily `dailyProfitTargetPct` shape and the new challenge-scoped
`challengeProfitTargetPct`/`onPace` read), Rule Compliance Score (now
real — `PropFirmComplianceScore`, a published, equal-weighted average of
five named sub-scores, never a hidden blend), Capital at Risk (real,
unchanged), and **Challenge Progress** (now real —
`compute_challenge_progress()`, `applicable: false` honestly when no
window is configured). **Still not a single real number, deliberately:**
Trading Days Completed (still no "days actually traded" counter distinct
from calendar days) and Account Health Score (Chapter 63's
`CompanyHealth.overall` remains company-wide, not account-scoped —
misrepresenting it as this one account's own would be the same trap
this Design Bible's KPIs sections warn against elsewhere).

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

**Real and computable today:** compliance against the six originally-real
daily-scoped rules, **plus, now:** `PropFirmComplianceScore.overall` (a
real, published, equal-weighted average of Drawdown Safety, Consistency,
Rule Compliance, Risk Exposure, and Capital Preservation — deliberately
excluding company-wide `CompanyHealth.overall`, since blending a
company-wide number into a single account's score would misrepresent
it), and Challenge Progress percentage. **Still not honestly
computable:** Trading Days Completed — no "days actually traded"
counter distinct from calendar days exists yet.

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

**Pre-existing, found by direct research before this part was written:**
five of the brief's fifteen supported rules (Daily Loss Limit, Maximum
Overall Drawdown, Maximum Position Size, Maximum Risk Per Trade,
Maximum Open Positions) already real, enforced, CEO-configurable
`RiskLimits` fields; a sixth (Profit Targets) real in a daily-scoped
shape; the "block automatically, explain exactly why" pre-trade shape
already real via the Trade Gatekeeper; `DailyObjectiveStatus` a real,
live, per-day compliance readout; Chapter 67's sticky-critical-toast +
Alert Center real, working delivery infrastructure.

**Built this pass, in `app/prop_firm.py` (new) — status-computation
only, never enforcement (see Part 3 below):**
- **Weekday-Aware Time System** — `weekday_for()`, a real, deterministic
  Monday-anchored mapping from `sim_day` to `Weekday`, never stored or
  driftable. The load-bearing infrastructure this part's addendum
  identified as needed by every other calendar-scoped feature below.
- **Trailing Drawdown Engine** — `Account.peak_equity`, a real,
  continuously-updated high-water mark (`app/accounts.py::_with_
  updated_peak_equity()`), plus `compute_trailing_drawdown()` recomputing
  drawdown from that moving peak. The existing static `RiskLimits.
  maxDrawdownPct` check is untouched, kept exactly as-is alongside it.
- **Consistency Rule Engine** — `compute_consistency_status()`: real
  per-day P&L bucketed from the account's own closed-trade history,
  compared against the challenge window's real cumulative total.
  `applicable: false` when no window is configured, rather than
  fabricating a comparison.
- **Scaling Milestones** — `compute_scaling_status()`: real, published
  growth-tier thresholds (10/25/50/100% equity growth), a transparent
  step function.
- **Challenge Windows** — `Account.challenge_start_sim_day`/
  `challenge_duration_days`/`challenge_profit_target_pct` +
  `compute_challenge_progress()`, including a real `onPace` read
  (required pace = target × elapsed/duration).
- **Prop Firm Compliance Score** — `compute_compliance_score()`: a real,
  published, **equal-weighted average of five named sub-scores**
  (Drawdown Safety, Consistency, Rule Compliance, Risk Exposure, Capital
  Preservation) — never a hidden blend, and deliberately excluding
  company-wide `CompanyHealth.overall` from the average, since it isn't
  account-scoped.
- **Leverage** — deliberately *not* fabricated. `LEVERAGE_NOTE`, a
  static, honest string ("Not applicable — 100% cash, long-only, no
  margin concept anywhere in this codebase"), surfaced on every
  `PropFirmStatus` response instead of a number.
- `GET /api/accounts/prop-firm/status` and `POST /api/accounts/
  prop-firm/configure` (`app/routers/accounts.py`) expose all of the
  above; `TreasuryPanel.tsx`'s new `PropFirmCard` is the CEO-facing
  surface.

**Still genuinely unbuilt:** any of this part's real new status reads
being *enforced* (blocking a trade) — that's Part 3's job, done next;
News Trading Restrictions, Minimum Trading Days, and hour-of-day
Time-Based Restrictions (Weekday-Aware Time System covers day-of-week,
not hour-of-day); "Swing Trading Mode"; any system-initiated automatic
pause distinct from the CEO-triggered Emergency Stop; and everything
that depends on Chapter 68's real broker connections. Verified:
mypy/ruff clean, `tsc --noEmit`/eslint/`npm run build` clean, and
runtime-tested against the real `GameState` singleton including a full
save-module persistence round-trip. Gated, for the eventual live-trading
half, by the same [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by.

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
| "Institutional Rule Engine" (one centralized enforcer) | **Now real, as a centralized evaluator — not yet a pre-trade blocker.** `app/rule_engine.py`'s `evaluate_rules()`. | A real, single, centralized module — one place, not one function per check — evaluates every enabled `Rule` on an account and returns a structured pass/fail per rule. **The one honest gap left open:** grep-confirmed `evaluate_rules()` is not called anywhere in `app/nexus.py` or the Trade Gatekeeper's pre-trade pipeline — it's invoked on demand (`GET/POST /api/accounts/rules/evaluate*`), not wired as a veto before a trade executes. The brief's own "one centralized enforcer" vision is architecturally real; the "enforcer" half (blocking a trade before it happens) is not yet connected. |
| "Rule Profiles" (per-account-type rule sets) | **Now real, per-account (not per-account-*type*)** — `Account.custom_rules: list[Rule]` | Each real `Account` (Part 1) carries its own list of `Rule` objects, up to `MAX_CUSTOM_RULES_PER_ACCOUNT` (20) — a real, CEO-authored, per-account rule set, closer to the brief's "Custom Rule Builder" output than a fixed named profile a CEO picks from a menu (no `personal`/`ira`/`prop_firm` preset bundles exist — every account starts with zero custom rules and the CEO adds its own). |
| "Rule Execution Order" (AI Decision → Risk Authority → IRE → Broker Management System → Order Execution) | Still real for two of five stages; IRE now exists but isn't spliced into this pipeline | AI Decision (real) → Risk Authority (real) → *IRE* (**now real as a module, `evaluate_rules()`, but not called from this pipeline**) → *Broker Management System* (Chapter 68, still deferred) → Order Execution (real). The pipeline itself still skips straight from Risk Authority to Order Execution — wiring the IRE into it as a genuine pre-trade veto stage remains open work, named honestly in Future Expansion below. |
| "If any rule fails: block, explain, suggest corrective actions, record in Company Memory" | **Now three of four real for the IRE specifically, one still open** | Explain (real — every `RuleCheckResult` carries the specific limit, current value, and pass/fail), **Suggest corrective actions (now real)** — `CORRECTIVE_ACTIONS`, a static, per-`RuleType` template dict (e.g. "Reduce position size to bring today's realized loss back under the daily limit."), never a generic message, Record in Company Memory (real — `record_rule_violation()` writes a real `"alert"`-category record on `POST /rules/evaluate-and-record`). **Still not real: Block** — see the Rule Execution Order gap above; a rule violation is recorded and explained, not yet used to reject a pending trade. |
| "Rule Categories" (14 named + Future Rule Packs) | Six real, individually or via the new closed `RuleType` set | Capital/Risk/Drawdown/Position Rules (real, pre-existing `RiskLimits`), Automation Rules (real, singular), **and now Trailing-Drawdown/Consistency/Weekday Rules** — three of Part 2's new computations are now selectable `RuleType` values a CEO can attach as a Custom Rule (`trailing_drawdown_pct`, `consistency_pct`, `no_trading_on_weekday`), alongside the five original `RiskLimits`-mirroring types (`max_daily_loss_pct`, `max_drawdown_pct`, `max_position_pct`, `max_open_positions`, `max_risk_per_trade_pct`) — 8 `RuleType` values total. **Still not real:** Leverage Rules (not applicable — Part 2), Broker Rules (Ch68), Market Rules, Account-type Rules (no per-type presets), Strategy Rules, Tax Rules, Compliance Rules, Future Rule Packs. |
| "Custom Rule Builder" (CEO writes rules without code changes) | **Real, by deliberate scope, not a free-text DSL** — `AddCustomRuleRequest` (`POST /api/accounts/rules/add`) + `CustomRulesCard` (`TreasuryPanel.tsx`) | The CEO picks a `RuleType` from a closed, named set (not a code change — no rule parser was built, and building one is out of scope; see Custom Rule Builder section below for the explicit reasoning), sets a label and a limit/weekday, and the rule is real, persisted, and independently evaluable/toggleable/removable — genuinely "no code change needed to add a *rule*," honestly narrower than "no code change needed to add a new *kind* of rule." |

### Inputs

**Real today:** every individual `RiskLimits` field this part's Rule
Categories table confirms real; Chapter 65's real market regime/
volatility read remains unused as a `RuleType`; and, now, a real
per-account `Rule` list (`Account.custom_rules`) plus a real, closed
`RuleType` definition format `evaluate_rules()` can parse. **Still not
real:** a rule-definition format for *arbitrary* CEO-authored logic
(the free-text DSL the brief's own "no code changes" framing implies) —
see Decision Logic and Custom Rule Builder above for the deliberate
scope decision behind that gap.

### Outputs

**Real today:** a blocked trade with a real, specific reason (the Trade
Gatekeeper's own output shape, unchanged) — **and, now, separately:** a
real `RuleEvaluationResult` per account (`GET/POST /api/accounts/rules/
evaluate*`) — a per-`RuleCheckResult` pass/fail with a corrective-action
suggestion, plus a real Company Memory record on every violation
recorded via the `-and-record` endpoint. **Not yet produced:** that
`RuleEvaluationResult` feeding back into a blocked trade — the two
outputs exist in parallel today, not yet merged into one pipeline.

### Internal Workflow

**The brief's own Rule Execution Order, stage by stage:** AI Decision
(real) → Risk Authority (real) → IRE (**now real as `evaluate_rules()`,
callable, but not called from this pipeline**) → Broker Management
System (Chapter 68, deferred) → Order Execution (real). A future pass
would insert `evaluate_rules()`'s call as a genuine stage between Risk
Authority and Order Execution — today it's invoked separately, on
demand or after the fact, never inline with a pending trade.

### Decision Logic

**Real today, for every check `evaluate_rules()` runs:** each `RuleType`
is its own transparent, named threshold comparison in `_check_rule()`
(`app/rule_engine.py`) — one simple, individually-inspectable comparison
per rule, never combined or weighted, matching Chapter 66's "no
black-box composite" convention exactly. **The scope decision that
resolves this part's own central tension (Company Philosophy, above):**
rather than build a generic rule-evaluation formula that parses an
arbitrary CEO-authored string or DSL expression (the brief's literal
"Custom Rule Builder" ask), this pass implemented a closed, named
`RuleType` enum instead — genuinely data-driven (no code change needed
to add a *rule*), but not "no code change to add a new *kind* of rule."
No rule parser exists anywhere in this codebase, and building one
remains explicitly out of scope — see the Custom Rule Builder section
below for the full reasoning.

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
| Select a Rule Profile for an account | **Not built as a named, pre-bundled profile** (no Personal/IRA/Prop Firm preset menu) — but every account now carries its own real, independently-authored rule set (see Author a Custom Rule below), the substance of a "profile" without the preset-menu packaging. |
| Author a Custom Rule | **Real** — `POST /api/accounts/rules/add` (`app/accounts.py::add_custom_rule()`), capped at 20 per account, from a closed 8-value `RuleType` set — not free-text, by deliberate scope decision (see Decision Logic and Custom Rule Builder). |
| Configure existing named limits (Daily Loss, Position Size, ...) | **Already real**, globally scoped — every one of these is already a CEO-editable `RiskLimits` field via `POST /api/risk-limits`, today, for the one account that exists. |
| Enable/disable a Rule Category | **Not built as categories** — but individual rules are now real toggleable units: `POST /api/accounts/rules/toggle` (`app/accounts.py::toggle_custom_rule()`) enables/disables any one Custom Rule without deleting it. |

### Rule Profiles

**Still no named, pre-bundled profile menu** (Personal/IRA/Business/
Prop Firm/Family presets a CEO picks from) — but the underlying reason
to want one is now substantially covered a different way: every real
`Account` carries its own real `custom_rules` list the CEO builds by
hand, rule by rule, from the closed `RuleType` set. **The Prop Firm
profile specifically:** its three original core rules (Daily Loss
Limit, Maximum Drawdown, Maximum Position Size) remain real via
`RiskLimits`; three more of Part 2's own additions (Trailing Drawdown,
Consistency, Weekday) are now also directly attachable as Custom Rules
through the IRE. Scaling Milestones and Leverage remain outside the
Custom Rule Builder's scope — Scaling computes automatically (no rule
needed), Leverage stays explicitly not applicable.

### Rule Categories

Covered in full under Ownership above — six of fourteen real, now
individually selectable as one of 8 `RuleType` values a Custom Rule can
target; still no named, toggleable *category* grouping (a CEO toggles
one rule at a time, not "all Drawdown Rules" as a group).

### Custom Rule Builder

**The scope decision made this pass, stated plainly:** the brief's own
"no code changes" ask, taken literally, means a CEO types or composes
arbitrary free-form rule logic (a DSL, natural language, whatever form)
and the system parses and evaluates it. That's a materially different,
much larger piece of work than a closed set of named, parameterized
rule types — and it directly threatens this codebase's own "no
black-box composite" convention, since an arbitrary parsed expression is
much harder for a CEO to audit than a fixed, named comparison. This pass
chose the closed set deliberately: `RuleType` is a fixed 8-value enum
(`max_daily_loss_pct`, `max_drawdown_pct`, `max_position_pct`,
`max_open_positions`, `max_risk_per_trade_pct`, `trailing_drawdown_pct`,
`consistency_pct`, `no_trading_on_weekday`), each with a label, limit,
and (for the weekday type) a `Weekday` value — genuinely CEO-authored
and data-driven (no code change to add a *rule instance*), but adding a
*new kind* of rule still requires a code change, honestly narrower than
the brief's literal ask.

**Re-checked against the brief's own six examples with this scope
decision in mind:**
- "Never risk more than 1%" — **now directly buildable** as a
  `max_risk_per_trade_pct` Custom Rule, independent of the global
  `RiskLimits.riskPerTradePct` field.
- "Maximum three open positions" — **now directly buildable** as
  `max_open_positions`.
- "No trades on Fridays" — **now directly buildable** as
  `no_trading_on_weekday`, using the real Weekday-Aware Time System
  Part 2 built.
- "Never trade after 2:00 PM" — **still not buildable** — no
  `RuleType` exists for hour-of-day, since `TimeState` still has no
  hour-gating concept to check against.
- "Only trade when market volatility is below a defined threshold" —
  **still not buildable** — Chapter 65's real regime read was not added
  as a `RuleType` this pass.
- "Require AI confidence above 92%" — **still not buildable** — the
  Trade Gatekeeper's confidence check remains a fixed constant in code,
  not exposed as a `RuleType`.

**The honest summary:** three of six brief examples are now real,
CEO-authored Custom Rules; three remain unbuilt, each blocked on
infrastructure (hour-gating, a volatility-threshold hook, a
configurable confidence threshold) this pass didn't add. No free-text
rule parser exists anywhere in this codebase, and none was built —
extending the `RuleType` enum, not building a DSL, is this system's own
stated path forward (see Future Expansion).

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

Wiring `evaluate_rules()` into the actual pre-trade pipeline as a real
veto stage (today it evaluates on demand, not inline with a pending
trade) is the single most consequential piece of remaining work — it's
what would turn this from a real evaluator into the brief's own
"enforcer." Beyond that: extending the closed `RuleType` enum with more
values (hour-of-day, volatility threshold, confidence threshold — the
three Custom Rule Builder examples still unbuilt), migrating Chapters
57/58/66's own hardcoded checks to route through the same engine rather
than staying parallel to it, Rule Packs shared across CEOs, and any
move toward free-form rule authoring. All deliberately not attempted in
this pass — matches this volume's own Future Expansion precedent.

### Design Bible Integration

**Real today:** Company Memory now records every real rule violation
found by `evaluate_and_record_account_rules()`, exactly the way it
already records other risk events (Chapter 61). **Not yet
integrated:** Chapters 57/58/66's own hardcoded checks still run
independently of the IRE — this pass built a second, real, centralized
system alongside them rather than migrating them into it, an explicit
scope boundary (see Primary Responsibilities): the IRE owns per-account
Custom Rules; it does not yet subsume the pre-existing global
`RiskLimits` checks for the primary account.

### Company Principle

"Accounts define rules. The Institutional Rule Engine enforces them."
**Now real, narrowly and honestly:** a real `Account.custom_rules` list
defines rules, and a real, separate `app/rule_engine.py` evaluates
them — definition and evaluation are now genuinely split code, not the
same function, for every Custom Rule an account carries. **Still not
true company-wide:** Chapters 57/58/66's own real, pre-existing checks
remain hardcoded, on purpose, and this pass deliberately did not
migrate them — the "one centralized engine for every account's rules"
vision is real for the *new* rule surface this pass built, not yet for
the *original* one it left untouched.

### Part 3 Implementation Notes

**Pre-existing, found by direct research before this part was written:**
five of fourteen Rule Categories already real, individually, as
hardcoded checks; the brief's own Rule Execution Order real for its
first two stages and its last stage; every real check already blocking
unconditionally, explaining why, and recording into Company Memory.
Grep-confirmed: no `Rule`/`RuleProfile`/`RuleEngine` class existed
anywhere in `backend/app/` before this pass.

**Built this pass:**
- **`app/rule_engine.py`** (new) — `evaluate_rules()`, a real,
  centralized evaluator. `_check_rule()` handles all 8 `RuleType`
  values, each one simple, individually-inspectable comparison, never
  combined. `CORRECTIVE_ACTIONS`, a static per-`RuleType` template
  dict, resolves the "suggest corrective actions" gap this part's own
  Ownership research identified — the fourth of the brief's four
  required rule-failure behaviors, and the last one still missing
  before this pass.
- **`Account.custom_rules: list[Rule]`** (`app/schemas.py`) — the real
  per-account rule set this part's "Rule Profiles" section asked for,
  built as an open-ended list rather than a fixed named-profile menu.
- **`app/accounts.py`** — `add_custom_rule()`/`remove_custom_rule()`/
  `toggle_custom_rule()`, capped at `MAX_CUSTOM_RULES_PER_ACCOUNT` (20).
- **`app/state.py::evaluate_account_rules()`** — the locked, persisted
  counterpart to the read-only evaluation, writing a real `"alert"`
  Company Memory record via `scribe.py::record_rule_violation()` for
  every real violation found.
- **`POST/GET /api/accounts/rules/*`** (`app/routers/accounts.py`) and
  `CustomRulesCard` (`TreasuryPanel.tsx`) expose all of the above.

**The one deliberate, load-bearing scope decision:** a closed `RuleType`
enum instead of a free-text DSL/rule parser — see Decision Logic and
Custom Rule Builder above for the full reasoning. No rule parser exists
anywhere in this codebase.

**What's genuinely still unbuilt:** `evaluate_rules()` wired into the
actual pre-trade pipeline as a blocking veto stage (today: real,
callable, evaluated on demand — not yet inline with a pending trade);
migrating Chapters 57/58/66's own hardcoded checks into this same
engine; named Rule Profile presets (Personal/IRA/Prop Firm bundles);
the three Custom Rule Builder examples that need new infrastructure
(hour-gating, a volatility threshold, a configurable confidence
threshold); and any KPI/report depending on cross-account rule-
violation history. Verified: mypy/ruff clean, `tsc --noEmit`/eslint/
`npm run build` clean, and extensive runtime tests against the real
`GameState` singleton — rule creation validation, PASS/FAIL evaluation
with corrective actions, disable-changes-outcome, Company Memory
recording (confirmed in a dedicated test with the rule left enabled),
removal, and a full save-module persistence round-trip. Gated, for the
eventual live-trading half, by the same [Live Trading
Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by.
