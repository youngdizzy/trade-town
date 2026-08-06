# Chapter 69 — Multi-Account & Fund Management System (MAFMS)

**Status:** Pure architecture, not yet implemented — the same posture
as [Chapter 68](chapter-68-institutional-broker-management-system.md),
and for the same reason. **Researched first:** this codebase's entire
save state (`GameSaveState`, `app/schemas.py`) holds exactly one
trading ledger (`PaperPortfolio`, its own docstring: "the company's one
simulated trading account") and one other, genuinely isolated capital
pool (`TreasuryState`, the CEO's personal treasury —
`TreasuryPanel.tsx`'s own "isolated second account" framing, Chapter
67's navigation notes). Two pools, both hardcoded, neither carrying an
account ID, type, owner, or permission set. That's the real ceiling
this chapter's architecture has to grow past — not a redesign, an
addition. See the Implementation Notes at the bottom for the precise
inventory.

## Executive Summary

TradeTown has never managed more than one trading account at a time.
**Researched first:** the one real precedent for "capital in two
places, cleanly separated" already exists — `PaperPortfolio` (trading
capital) and `TreasuryState` (the CEO's personal capital) are two
genuinely independent balances with their own transaction histories,
and nothing in this codebase mixes them without an explicit deposit/
withdraw transaction. What doesn't exist is everything past that: a
generalized N-account model, account types, per-account risk profiles
or permissions, account switching, cross-account aggregation, or
anything resembling Fund Mode or Client Mode. This chapter describes
the architecture that would generalize the real two-pool precedent into
the brief's own account hierarchy — CEO → Master Portfolio → Account
Groups → Individual Accounts → Strategies → Positions — without
inventing any of the intermediate real estate that doesn't exist yet.

## Company Philosophy

"Capital may belong to different accounts; intelligence belongs to
TradeTown; knowledge is shared; risk remains isolated" is not a new
principle for this codebase to adopt — it is, narrowly, already true.
Company Memory and the Knowledge Graph (Chapter 61) are real, global,
and already shared across every real system that touches the one
trading account that exists; nothing here would need to change for a
second account to benefit from the same shared knowledge. What isn't
proven yet is the "risk remains isolated" half at scale, since there
has only ever been one account's risk to isolate.

## Primary Responsibilities

**Would own:** Multi-Account Management, Portfolio Separation, Fund
Management, Account Permissions, Capital Allocation (account-level),
Account Reporting, Account Switching, Master Portfolio View,
Cross-Account Analytics, Performance Attribution (by account/broker).

**Does NOT own** (matches the brief, and matches this codebase's real
division of labor): Trade Research (Chapter 8), Trade Approval (the
CEO's own decision), Risk Authority (Chapters 57/58/66's real pre-trade
veto pipeline — MAFMS would assign a risk *profile* to an account,
never compute or override a risk decision itself), Broker Communication
(Chapter 68's own real boundary), Execution Logic (`app/broker.py`).

## Ownership

Every brief concept checked against the real codebase before this
chapter was written:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Multi-Account Management" / "Account Hierarchy" | *(genuinely does not exist)* | `GameSaveState` holds exactly one `PaperPortfolio` and one `TreasuryState` — two hardcoded fields, not a list of N accounts with IDs to iterate over. There is no `AccountGroup`, no `Strategy`-to-`Account` link (Chapter 45's Research Sandbox `Strategy` objects belong to the company, not to any one account), and no code path that could "create" or "archive" an account today. |
| "Portfolio Separation" / "Account Isolation" | `PaperPortfolio` + `TreasuryState` (`app/schemas.py`, `app/treasury.py`) | The one real, working precedent for this entire chapter: two independent balances, each with its own transaction history (`PaperTrade`/`PaperOrder` vs. `TreasuryTransaction`), moved between only via an explicit deposit/withdraw call — never mixed silently. **Incomplete even for these two:** `RiskLimits` and Operating Mode (the real automation-level control) are each a single global object/setting, not scoped per-pool — a real gap even in today's narrower two-pool world, before a third account is ever added. |
| "Fund Management" (NAV, investor capital, contributions/withdrawals) | *(genuinely does not exist)* | No Net Asset Value concept, no investor-vs-fund capital distinction anywhere. `TreasuryState` tracks deposits/withdrawals for the CEO's own personal capital only — the closest real analog, and a single-owner one. |
| "Account Permissions" (View Only/Research Only/Paper/Manual/Automation/Execution/Transfers/Admin) | Operating Mode (`learning`/`assisted`/`executive`, `app/schemas.py`) | Real, but a single global AI-autonomy dial, not a per-account permission matrix — it changes how much of the *existing* proposal-resolution pipeline runs unattended, not who can view, trade, or transfer within a given account. No granular permission concept exists at all. |
| "Capital Allocation" (Company → Account → Position) | Chapter 57's Position Sizing (`app/nexus.py`), Chapter 59's Capital Priority (`app/capital_priority.py`) | Real, but two levels, not three: company-level cash-reserve/position-sizing math flows straight to position-level sizing, because there is only one account's capital to size against — the brief's middle "Account Level" has nothing to sit between yet. |
| "Account Reporting" | `TreasuryMonthlyReport` (`app/schemas.py`) | Real, and the one genuine precedent for a *named, persisted, per-period* report object in this whole brief — but scoped to Treasury alone. `PaperPortfolio`'s own performance is always computed live off the ledger (`computePeriodFinancials()`), never archived into an equivalent `PortfolioMonthlyReport`. |
| "Account Switching" | *(does not exist)* | There is nothing to switch between — the Command Center already shows the one `PaperPortfolio` and the one `TreasuryState` simultaneously, on their own tabs (RISK/PORTFOLIO and TREASURY), not as alternate contexts to toggle. |
| "Master Dashboard" / "Master Portfolio View" / "Cross-Account Analytics" | *(does not exist)* | Nothing to aggregate — Total AUM, Per-Account P&L, Broker Distribution, and every other master-dashboard metric the brief lists require 2+ real accounts to compute honestly, and only one exists. |
| "Performance Attribution" (by account/broker/strategy/sector/timeframe/regime/employee/capital source) | Partially real, narrowly: by employee (`supportingAgents`/`opposingAgents` on every `PaperTrade`) and by timeframe (`computePeriodFinancials`'s daily/weekly/monthly/all-time periods) are both real today. **Not real:** by account or broker (only one of each exists to attribute against), by sector (no sector taxonomy exists on `PaperTrade`), by market regime (Chapter 65's regime read is real but never joined against trade P&L as an attribution dimension). |
| "Account Groups" | *(does not exist)* | No grouping concept anywhere — matches "Account Switching" above; nothing exists yet to group. |
| "Client Mode" / "Fund Mode" | *(does not exist — the brief's own framing, "future-ready architecture" and "future institutional support," already says so)* | Honored here at face value rather than re-litigated: these are named future work in the brief itself, not a gap this research needed to discover. |

## Inputs

**Would receive, once real:** account credentials/permissions from
Chapter 68's IBMS (does not exist — Chapter 68 is itself pure
architecture), a CEO-assigned risk profile per account (the underlying
`RiskLimits` machinery is real; per-account assignment is not), a
CEO-assigned objective/strategy preference per account (does not
exist). **Real today:** the two real capital pools themselves
(`PaperPortfolio`, `TreasuryState`) are the one honest input this
chapter's architecture would generalize from.

## Outputs

**Would produce, once real:** Master Portfolio, Account Context,
Capital Distribution, cross-account Performance Data, Account Reports,
Executive Analytics scoped per account. **Real today:** `PaperPortfolio`'s
live performance figures and `TreasuryMonthlyReport` — the same two
real, single-scope outputs already described under Ownership.

## Internal Workflow

**The brief's own two-level Capital Allocation flow (Company → Account
→ Position), checked against what's real:** Company Level (real —
`RiskLimits`' cash-reserve floor) → *Account Level* (does not exist —
nothing between the company and a position to allocate through) →
Position Level (real — Chapter 57's Position Sizing). A real MAFMS
would insert exactly one new stage into an existing, real pipeline, not
replace it.

## Decision Logic

**Not real, for the whole chapter:** no formula exists for account
prioritization, capital distribution across accounts, or per-account
risk-profile derivation, because there is only one account's capital to
distribute today. **Real precedent to build from:** Chapter 59's
Capital Priority engine already ranks *opportunities* against one
account's available capital with a real, transparent formula — the
same shape a future cross-account allocator would need, one level up.

## Department Cooperation

**Would receive from:** Chapter 68 (IBMS — itself pure architecture,
so MAFMS inherits the same "not yet real" status transitively, since a
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

## CEO Controls

| Control | Status |
|---|---|
| Create Account / Archive Account | **Not built** — no account model exists to create or archive an instance of. |
| Switch Account | **Not built** — nothing to switch between. |
| Group Accounts | **Not built.** |
| Transfer Settings (between accounts) | **Not built** — the one real transfer mechanism, `TreasuryTransaction` deposit/withdraw, moves capital between the two existing hardcoded pools, not between CEO-created accounts. |
| Assign Strategy / Assign Risk Profile | **Not built** — `RiskLimits` is real but global, not an assignable per-account profile. |
| Enable/Disable Automation | **Partially real, globally scoped** — Operating Mode already toggles automation level company-wide; there is no per-account equivalent. |
| Paper Trading / Live Trading | **Not a real toggle, same finding as Chapter 68** — every account this codebase has ever had is paper; there is nothing live to switch to. |

## Security

**Real today: nothing to secure**, for the same reason as Chapter 68 —
no per-account credential, API key, or permission exists yet to leak,
because no second broker-connected account exists. This chapter's own
"never expose one account's credentials to another" requirement is
inherited directly from Chapter 68's Security section and stays
unbuilt for the identical reason: no credential storage exists in this
codebase at all yet.

## Reports

**Not built, for six of the brief's eight:** Master Portfolio Report,
Account Performance Report, Capital Allocation Report, Fund Report,
Client Report, Risk Distribution Report — all require 2+ real accounts
to report across. **Real today, and the closest honest analog to
"Account Performance Report":** `TreasuryMonthlyReport`, scoped to the
one Treasury pool. **Real today, company-wide, the closest analog to
"Executive Summary":** Feature 24's monthly `ExecutiveReview`
(`app/executive_review.py`).

## KPIs

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

## Learning System

**Already real, company-wide, for the "knowledge is shared" half of
this chapter's own philosophy:** Company Memory and the Knowledge Graph
(Chapter 61) are real and global today — nothing about them is scoped
to a single account, so a second account would inherit the same shared
institutional knowledge with no change required. **Not yet
demonstrable:** the "individual accounts remain independent" half,
since there's only ever been one account whose isolated performance
could be tested against the shared-knowledge half.

## Dependencies

Chapter 68 (Institutional Broker Management System) — matches the
brief's own stated dependency exactly, and transitively means MAFMS
cannot become real before IBMS does, since a second account without a
real broker connection behind it is just a second hardcoded pool, not
the brief's own vision. All previous Design Bible chapters, per the
brief's own honest framing (the same "ALL PREVIOUS DESIGN BIBLE
CHAPTERS" dependency Chapter 66's own brief already used correctly).

## Future Expansion

Unlimited Accounts, Unlimited Brokers, Family Office Management, RIA
Support, Hedge Fund Operations, Institutional Clients, Fractional
Account Management, Global Multi-Currency Accounts, Cross-Broker
Portfolio Management — every one of these requires both a real
multi-account foundation and real broker connections, neither of which
exist. Matches Chapter 66's and Chapter 68's own Future Expansion
precedent: not invented or stubbed here, because nothing here has the
real foundation to build on yet.

## Design Bible Integration

**Real today, for the one account that exists, and would need no
change to keep working for a second:** Company Memory, Knowledge Graph,
Portfolio Intelligence, Company Health, Executive Dashboard, and Risk
Authority all already consume `PaperPortfolio`'s real state and would
extend to a real second account without a rewrite, since none of them
hardcode a single-account assumption into their own logic — they simply
have never been asked to read a second one. **Not built:** a named,
distinct "Audit Center" surface (the same Chapter 68 finding, carried
over unchanged).

## Company Principle

"One company. One brain." is, narrowly, already true — trivially, when
there is only one account for that one brain to manage. Its deeper
meaning — one shared intelligence serving many separately-risked
accounts at once — is exactly what this chapter's architecture exists
to make possible, and exactly what hasn't been tested yet, because it
has never had a second account to prove itself against.

## Supported Account Types / Portfolio DNA Examples

**Genuinely, entirely unbuilt as configurable account types** — Personal
Brokerage, IRA/Roth IRA, Business Account, Prop Firm Account, and
Family Account all require the account model this chapter's Ownership
section already confirmed doesn't exist. **A real, working exception
worth calling out precisely:** the Prop Firm profile's own named "Special
Rules" — Daily Loss Limits, Maximum Drawdown, Position Size Limits —
are not aspirational. `RiskLimits`' `maxDailyLossPct`, `maxDrawdownPct`,
and `maxPositionPct` fields (Chapter 57) already implement exactly this
machinery, enforced today by `app/risk_engine.py`'s
`evaluate_sentinel_risk()` — just scoped globally to the one account
that exists, never as an assignable per-account profile a CEO could
attach specifically to a "Prop Firm" account type. When a real
multi-account model is built, this is the one piece of the brief's
"Portfolio DNA" concept that would be wiring existing machinery into a
new home, not building something from zero.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written, not assumed:** two genuinely isolated capital pools
(`PaperPortfolio`, the company's trading account; `TreasuryState`, the
CEO's personal capital), each with its own real, independent
transaction history, moved between only via an explicit, logged
transfer — the one real precedent this whole chapter's architecture
would generalize; a real, working per-period report object
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
to compute against. No code was written against this chapter — pure
architecture, matching Chapter 68's own posture exactly, and gated by
the same [Live Trading Gate](../../appendices/appendix-g-permanent-development-policy.md)
Chapter 68 is gated by, since MAFMS's own real value depends on IBMS
becoming real first.
