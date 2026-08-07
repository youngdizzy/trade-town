# Chapter 68 — Institutional Broker Management System (IBMS)

**Status:** Part 1 (Execution Provider Adapter Interface) implemented —
see "Part 1: Execution Provider Adapter Interface" below. Everything
else in this chapter remains pure architecture, not yet implemented.
**Researched first:** this codebase has exactly one order-execution
engine (`app/broker.py`'s `PaperBroker`), and its own module docstring
has stated since v0.6 that it is "completely simulated" — no brokerage
SDK import, no API key, no code path that reaches a real execution
endpoint. That finding, and every other real-vs-aspirational line in
this chapter, is not new: Chapter 66's own Ownership table already
confirmed "Broker Failsafe... genuinely does not exist" for the same
reason. This chapter's job is to give that permanent boundary a real
architecture to grow into — the interface every future connector
(Charles Schwab first) would implement. Part 1 built exactly that
interface — `ExecutionProvider`, mirroring `app/market_data.py`'s
`MarketDataProvider` pattern — with only a `PaperExecutionProvider`
wired in; no SDK, no credentials, no real connection, still 100%
simulated. See the Implementation Notes at the bottom for the precise
inventory of what's real today, and the Charles Schwab V1.0 section for
the standing **Live Trading Gate** policy (also [Appendix
G](../../appendices/appendix-g-permanent-development-policy.md))
governing exactly when — not if — this chapter moves from architecture
to a real connection. **Part 1 does not move that gate any closer to
open** — it gives a future connector a real seam to implement, nothing
more.

## Executive Summary

TradeTown's AI has never spoken to a broker. It has spoken to
`PaperBroker`, an in-process order book that evaluates fill conditions
against sim-clock ticks and watchlist prices it already holds in
memory — see `app/broker.py`. That module was deliberately shaped so a
real adapter could sit behind the same `place_order()`/`tick_broker()`
calls later, mirroring `app/market_data.py`'s own `MarketDataProvider`
abstract-base-class pattern (only a `"mock"` provider is implemented
there today, selected via an env var that falls back with a warning for
any other value — the exact same honesty posture this chapter inherits
for brokers). No such adapter exists or is wired in today's codebase.
This chapter describes IBMS — the gateway layer that would sit between
TradeTown's AI and any real broker, Charles Schwab first — as pure
target architecture: every section below states plainly whether it
describes something real or something none of this codebase's real
infrastructure supports yet, and never blurs the two.

## Part 1: Execution Provider Adapter Interface

**Real, implemented, and the only real code this chapter has ever
produced.** `app/broker.py` now defines `ExecutionProvider(ABC)` — an
abstract interface with `place_order()` and `tick_broker()` methods —
and `PaperExecutionProvider`, its one concrete implementation, which
delegates directly to this module's pre-existing, unchanged
`place_order()`/`tick_broker()` free functions. A module-level
`execution_provider` singleton is selected by `_select_execution_provider()`,
which reads an `EXECUTION_PROVIDER` environment variable (default
`"paper"`; any other value logs a warning and falls back to paper) —
the exact same shape `app/market_data.py`'s `_select_provider()` already
uses for `MARKET_DATA_PROVIDER`. `app/nexus.py`'s one real call site
(previously a bare `tick_broker(...)` import) now calls
`execution_provider.tick_broker(...)` — the only production code path
this interface changes.

**What this is not:** no brokerage SDK, no HTTP client, no credential
handling, no real connection of any kind was added. `place_order()`,
`_fill_price()`, and `tick_broker()` themselves are byte-for-byte
unchanged — `PaperExecutionProvider` only wraps them. This gives a
future Charles Schwab (or other) connector a real seam to implement
instead of `app/nexus.py` calling `broker.py`'s free functions
directly, and nothing more. It does not satisfy, advance, or shortcut
any of the seven Live Trading Gate conditions below — those remain
entirely about a real, credentialed, tested connection existing, which
this interface deliberately does not build toward. Covered by
`backend/tests/test_broker.py` (7 tests): the interface is abstract
with exactly the two methods above, the default/fallback provider
selection matches `market_data.py`'s pattern, and `PaperExecutionProvider`'s
`place_order()`/`tick_broker()` produce results identical to calling
the underlying free functions directly.

## Company Philosophy

TradeTown owns the intelligence; the broker only executes orders.
Changing brokers should never require changing company logic. This is
not a new principle for this codebase — it is the same "adapter behind
one interface, zero changes to consumers" shape `MarketDataProvider`
already proved out for market data. IBMS is that same shape, applied to
execution instead of quotes, one layer later than data ever needed to
go because until now there has been no real execution destination to
abstract away from.

## Primary Responsibilities

**Would own:** Broker Connections, Authentication, API Sessions, Order
Routing, Order Verification, Execution Monitoring, Account
Synchronization, Buying Power Validation, Position Synchronization,
Latency Monitoring, Broker Health, Execution Logs, Audit Trail.

**Does NOT own** (matches the brief exactly, and matches this
codebase's real division of labor today): Trade Decisions (NEXUS/the
analyst desk), Research (Chapter 8's own division), Risk Approval
(Chapters 57/58/66's real pre-trade veto pipeline — Position Sizing's
cash-reserve floor, the Opportunity Gatekeeper, the Trade Gatekeeper's
eight checks — all of which run and reject *before* an order would ever
reach IBMS), Probability Calculations (the analyst desk's own
confidence scoring), Portfolio Strategy (Chapter 59/60's own
allocation/rotation logic). IBMS's real boundary starts exactly where
today's Trade Gatekeeper already ends: it would receive an
already-approved order, never re-litigate whether it should happen.

## Ownership

Every brief concept below, checked against the real codebase before
this chapter was written — not assumed:

| Brief concept | Real system today | What it actually does |
|---|---|---|
| "Broker Connections" / "API Sessions" | *(genuinely does not exist)* | No brokerage SDK is imported anywhere in this codebase (grep-confirmed against `backend/app/*.py`). `backend/requirements.txt` carries no HTTP client library (no `httpx`, no `requests`) and no OAuth library — there is no technical capability to open a real broker session today, not just a missing credential. |
| "Authentication" / "Encrypt credentials" | *(genuinely does not exist)* | No credential storage of any kind exists to encrypt. `requirements.txt` carries no cryptography library (no `cryptography`, no `pynacl`). `python-dotenv` is present (env-var loading only) — the same "no API keys held anywhere in this repo" boundary `app/market_data.py`'s own docstring already states for market data. |
| "Order Routing" | `app/broker.py`'s `place_order()`, now reachable through `ExecutionProvider.place_order()` | Appends an order to an in-memory book on the *same* `PaperPortfolio` TradeTown already owns. Routes to nothing external — there is no second, broker-side order book to route to. Part 1 gave this a real interface seam (`ExecutionProvider`); it did not give it anywhere external to route to. |
| "Order Verification" (Accepted/Partially Filled/Filled/Rejected/Cancelled/Expired/Pending/Unexpected State) | `OrderStatus` (`schemas.py`): `"open" \| "filled" \| "closed" \| "cancelled"` | A real, working, but much narrower state machine: `_fill_price()` fills an order entirely or not at all (**no partial fills exist**), a filled exit order closes its linked position, and — since Chapters 57/58/66's own pre-trade checks already run before an order can be placed at all — **"rejected" cannot happen inside `broker.py`**, only before it. No `"expired"`/time-in-force concept exists (`broker.py`'s own docstring: orders "stay open indefinitely until filled"). |
| "Buying Power Validation" (cash, margin, PDT, options/short permissions) | Chapter 57's Position Sizing cash-reserve floor (`app/nexus.py`) | Real, but narrower: checks `cashBalance` against a reserve floor before a proposal is even created. **No margin account, Pattern Day Trader restriction, options permission, or short-selling permission concept exists anywhere** — this is 100% simulated cash-account, long-only paper trading. |
| "Position Synchronization" | *(does not apply)* | There is exactly one ledger — TradeTown's own `PaperPortfolio.positions` — with no second, broker-side position list to compare it against. Reconciliation, as the brief defines it, needs two sources of truth; today there is only one. |
| "Latency Monitoring" / "Broker Health" | `GlobalStatusBar.tsx`'s `BROKER` pill | Honestly static: the label reads `"SIMULATED"`, always, with a tooltip citing `app/broker.py` directly (Chapter 67's own work). No latency, no health score, no state machine — the one real, deliberate acknowledgment that nothing else in this row exists. |
| "Execution Logs" / "Audit Trail" | `PaperOrder`'s own resolved-order log (`MAX_ORDER_LOG = 40`, capped) | Real precedent, incomplete against the brief's own field list: `id`/`symbol`/`side`/`orderType`/`quantity`/`price`/`status`/`reason`/`placedBy`/`confidence`/`filledPrice`/`filledAt` exist; `Broker`, `Account`, and `Latency` do not, because none of those concepts exist yet to log. |
| "Account Management" (Personal/Paper/Business/IRA, multi-account) | `PaperPortfolio` (`schemas.py`) | One account. Its own docstring: "the company's one simulated trading account." No account ID, broker field, permissions, risk profile, currency, or status field exists — there is nothing to distinguish, because nothing to distinguish it from. |
| "Broker States" (Connected/Connecting/Disconnected/Auth Failed/Rate Limited/Maintenance/Market Closed/Emergency Disabled) | *(does not exist)* | The closest real precedent is `net:status`/`gameStore.netConnected` — a real, working binary connected/disconnected indicator (`TopStatusBar.tsx`'s own dot) for TradeTown's **own** WebSocket to its **own** backend, not a broker connection of any kind. Reusable event/UI *pattern*, zero broker-specific meaning today. |
| "Multi-Broker Ready" / "one connector, no changes to existing ones" | `app/market_data.py`'s `MarketDataProvider` (ABC), and now `app/broker.py`'s `ExecutionProvider` (ABC) | The real, working precedent for this exact shape, proven out for market data, now mirrored for execution: implement the interface, wire it in `_select_execution_provider()`, nothing that calls it changes. Only `PaperExecutionProvider` exists — a second, real connector would still need to be written from scratch — but `app/nexus.py` now calls through the abstraction (`execution_provider.tick_broker(...)`) rather than `broker.py`'s bare functions directly, so a second implementation could be wired in without touching that call site. |

## Inputs

**Would receive, once real:** an already CEO/Gatekeeper-approved order
(the one real input this chapter can assume exists, since Chapters
57/58/66 already produce it), broker credentials (does not exist),
account permissions (does not exist), real-time broker connection state
(does not exist). **Real today:** the approved-order handoff itself —
`app/nexus.py` already calls into `broker.py`'s `place_order()`
immediately after the Trade Gatekeeper clears an order, the exact seam
a real IBMS would sit in.

## Outputs

**Would produce, once real:** Execution Results, Broker Status,
Account Data, Position Updates, Buying Power, Order Events — all named
in the brief's own "Provides" list under Department Cooperation.
**Real today:** `PaperTrade` (a closed simulated trade), `PaperOrder`
(an order's own status), `PaperPosition` (an open simulated position) —
the same three outputs a real IBMS would eventually produce, just
sourced from `broker.py`'s deterministic fill logic instead of a real
execution confirmation.

## Internal Workflow

**The brief's own Order Execution Pipeline, checked stage by stage
against what's real:** AI Decision (real — the analyst desk) → Risk
Approval (real — Chapters 57/58/66's pre-trade veto pipeline) → *Broker
Validation, Buying Power Check, Market Status Check* (none of these
three exist as broker-side checks — Chapter 57's cash-reserve floor is
the closest real analog, and it runs earlier, before a proposal even
exists) → Order Submission (real — `place_order()`) → *Execution
Confirmation* (not real in the brief's sense — `tick_broker()` fills
deterministically against watchlist prices already held in memory,
never confirms against an external system) → Position Verification
(does not apply — see Ownership) → Portfolio Update (real —
`open_position()`/`close_position()`) → Company Memory (real —
`app/scribe.py` already records trade events for the simulated broker
today). Five of nine stages are real; four describe verifying against
an external system this codebase has never had.

## Decision Logic

**Real today:** `_fill_price()`'s per-order-type fill rules (market
fills at quote; limit/take-profit fill at-or-through the target price;
stop/stop-loss fill at-or-through the trigger price) are a real,
transparent, deterministic formula — no hidden weighting, matching this
codebase's "no black-box composite" convention throughout. **Not real:**
any formula for broker selection among multiple connectors (only one
would ever exist to select from today), any formula for a Broker Health
Score (nothing to score), any formula for reconciliation-mismatch
severity (nothing to reconcile).

## Department Cooperation

**Would receive from:** Chapters 57/58/66 (Risk Authority — the real
pre-trade veto pipeline that already runs before any order reaches
`broker.py` today), Chapter 56-adjacent Portfolio Intelligence (real),
Trade Execution (this chapter's own future scope, currently
`broker.py`), Company Memory (real — `app/scribe.py` already records
every simulated fill). **Would provide:** Execution Results (real
today, via `PaperTrade`), Broker Status (today, only the static
`"SIMULATED"` pill), Account Data (does not exist — one account, no
per-account fields), Position Updates (real, via `PaperPosition`),
Buying Power (no broker-side concept exists; `cashBalance` is the
closest real analog), Order Events (real, via `PaperOrder`).

## CEO Controls

| Control | Status |
|---|---|
| Connect Broker / Disconnect / Reconnect | **Not built** — no such control exists anywhere in this codebase; there is nothing to connect to. |
| Paper Trading Mode / Live Trading Mode | **Not a real toggle.** Every trade this codebase has ever executed is paper — there is no live mode to switch to, so this cannot honestly be a CEO-facing toggle yet. Operating Mode (learning/assisted/executive) is a real, different control: it governs how much AI autonomy resolves a proposal, not where an order executes. |
| Broker Selection | **Not built** — only one execution engine (`PaperBroker`) exists; there is nothing to select between. |
| API Keys / Permissions | **Not built** — no credential storage exists (see Ownership). |
| Account Switching | **Not built** — one account exists. |
| Execution Mode | **Not built**, distinct from the real Operating Mode selector above. |

Every row here is currently "Not built" — this table exists so the gap
is explicit and revisitable, not because any control is close to real.

## Security

**Real today:** nothing to secure, because nothing (credential, API
key, session) exists yet that could leak. This is the same honest
non-answer `app/broker.py`'s and `app/market_data.py`'s own docstrings
already give. **A real, load-bearing requirement for whenever Charles
Schwab v1.0 is actually built, not a description of anything
implemented now:** encrypted credential storage (`requirements.txt`
would need a real cryptography library — none is installed today),
never logging secrets, session-expiration handling, automatic
re-authentication. None of this should be retrofitted after a first
connector ships; it is the first thing that connector's own PR must
include, per this chapter's own Company Principle below.

## Paper Trading

**The brief's own principle — "Paper Trading should behave exactly
like Live Trading; same pipeline, same risk, same dashboards; only
execution destination changes" — cannot yet be verified either way,**
because there has never been a Live Trading path to compare Paper
Trading against. Today's `PaperBroker` **is** the only execution
destination that has ever existed in this codebase. This principle
becomes real, checkable work only once a first live connector exists to
diff against it — worth stating plainly now so it isn't silently
assumed true later without ever being tested.

## Execution Logging

**Real today, narrower than the brief:** every `PaperOrder` already
carries Timestamp (`createdAt`/`filledAt`), Order (`id`), Price,
Quantity, Status, and Reason. **Not real:** Broker (nothing to name),
Account (one account, no field for it), Latency (nothing to time
against an external system), and Execution Result as a distinct field
from Status. The order log itself is real and capped
(`MAX_ORDER_LOG = 40`) — a real precedent for "keep the last N events,"
not yet a permanent, unbounded audit trail.

## KPIs

**Not honestly computable, for any of the brief's eight:** Broker
Health, Average Latency, Execution Success Rate, Rejected Orders,
Synchronization Accuracy, API Availability, Fill Speed, Connection
Stability. **A trap worth naming explicitly:** `PaperBroker`'s fills
are deterministic price comparisons that always succeed once their
condition is met — an "Execution Success Rate" computed against it
today would read 100% by construction, not because anything real was
verified. Reporting that number would violate this Design Bible's own
no-fabrication rule by implying a health check that never actually
ran. None of these KPIs should be surfaced until a real broker exists
to genuinely fail against.

## Reports

**Not built, for the same reason as the KPIs above:** Broker Health
Report, Execution Report, Account Report, Buying Power Report,
Synchronization Report, Execution Latency Report, Audit Report. **Real
today, and the closest honest analog to "Order History":** the
capped `PaperOrder` resolved-order log described under Execution
Logging.

## Learning System

**Not built.** The brief asks this chapter to analyze rejected orders,
slow executions, failed authentications, API failures, and
synchronization issues to improve broker reliability continuously.
None of those failure modes can occur in a fully simulated, always-
available paper engine with no external dependency to fail — there is
nothing yet to learn from. This mirrors Chapter 66's own finding for
its "Broker Failsafe" gap: the absence of a real dependency means the
honest move is to say so, not to build a learning loop with nothing
real feeding it.

## Charles Schwab V1.0

**Status: PLANNED — NOT IMPLEMENTED.** Every requirement below — secure
authentication, paper trading support, live trading support, account
synchronization, buying power, position sync, order placement, order
cancellation, order status, execution confirmation — has zero real
backing anywhere in this codebase today. `app/broker.py`'s own module
docstring has named Charles Schwab, Interactive Brokers, and Alpaca as
hypothetical future adapters since v0.6; none has ever been
implemented, and no SDK, HTTP client, or OAuth library for any of them
is installed (`requirements.txt` carries none). TradeTown must remain
100% simulated until the Live Trading Gate below explicitly authorizes
live brokerage connectivity. **Standing constraints on every future
session that touches this section:** do not add live credentials, do
not add OAuth credentials, do not place real orders, do not bypass the
Live Trading Gate. The 15-phase target design below is the concrete
plan this whole chapter's architecture exists to make possible — the
first connector to actually implement the interface IBMS describes —
not a status update on work in progress, and not an implementation
schedule any future session may start executing without the CEO's
explicit, in-writing authorization the Live Trading Gate requires.

### Phase 1 — Current Architecture (Implemented)

The one piece of this plan that is real today: `app/broker.py`'s
`ExecutionProvider(ABC)` and its one concrete implementation,
`PaperExecutionProvider` — see "Part 1: Execution Provider Adapter
Interface" above. The application communicates with brokers through
`ExecutionProvider`, never by calling a broker API directly; every
future broker, Schwab included, must plug into this same interface
rather than becoming a second, parallel execution path.

### Phase 2 — Schwab Connector Design (Target)

A dedicated `SchwabExecutionProvider` implementing the existing
`ExecutionProvider` interface — not a new, parallel interface. It must
not leak Schwab-specific objects (raw API response shapes, Schwab's own
order/account models) anywhere outside its own module; every
TradeTown Order it receives is translated into a Schwab-shaped request,
and every Schwab response is translated back into TradeTown's existing
`PaperOrder`/`PaperTrade`/`PaperPosition` models before it reaches any
other system. Flow: TradeTown Order → `ExecutionProvider` →
Schwab Adapter → Schwab API, and the reverse on the way back.

### Phase 3 — Authentication (Target)

Schwab's official OAuth authorization flow only. TradeTown must never
store a Schwab username, password, or any other direct brokerage login
credential — only OAuth tokens, and only with secure token handling.
Required infrastructure, none of which exists today: an OAuth callback
endpoint, authorization-state validation, encrypted token storage,
token refresh handling, token-expiration detection, token-revocation
handling, a reauthorization flow, and authentication audit logging.
`requirements.txt` would need a real cryptography library (none is
installed) before any of this could be built safely.

### Phase 4 — Account Discovery (Target)

After authorization, discover the Schwab accounts available to the
authorized connection and map them to TradeTown's own supported account
types (Chapter 69's real `Account` model: Personal, IRA, Business, Prop
Firm, Family — no new categories invented beyond what Chapter 69
already supports). The CEO must explicitly select which discovered
Schwab account maps to which TradeTown account; no mapping is ever
assumed.

### Phase 5 — Read-Only Validation (Target)

Before order placement is enabled at all, connect to Schwab in
read-only mode where the integration architecture supports it, and
validate account information, balances, buying power, positions,
orders, transactions, market data, market status, account identifiers,
position quantities, and cash values against TradeTown's own internal
portfolio state.

### Phase 6 — Reconciliation (Target)

TradeTown must compare its internal state against Schwab's and detect:
missing positions, unexpected positions, quantity differences, cash
differences, order-state differences, price differences, stale data,
and connection failures. Any reconciliation failure must prevent
automated live execution until resolved — this is the same "TradeTown
never trusts that an order succeeded" standard this chapter's Company
Principle already states, made concrete and mandatory.

### Phase 7 — Order Safety (Target)

Every live order must pass through every one of these real or
target-real gates before it may reach Schwab: Trading Mode (Chapter
75), the Institutional Rule Engine (Chapter 69 Part 3), Risk Authority
(Chapters 57/58/66), the Trade Gatekeeper, the Daily Loss Circuit
Breaker, Losing Streak Protection, Position Limits, Correlation Limits,
News Risk Controls, Broker Health Checks, and Emergency Stop. None of
these gates may be bypassed for a live order, ever — this is the same
pre-trade veto pipeline already real for every paper order today,
extended rather than replaced.

### Phase 8 — Live Mode Protection (Target)

Live Trading must be visually unmistakable, never interchangeable with
Paper Mode: `LIVE MODE`, `REAL MONEY`, `BROKER: CHARLES SCHWAB`,
`ACCOUNT`, `ACTIVE RISK LEVEL`, and Emergency Stop must all be
displayed. The existing `GlobalStatusBar.tsx` `BROKER` pill's honest,
static `"SIMULATED"` label is the real precedent this would eventually
replace — for a live connection only, never blurring the two.

### Phase 9 — Live Mode Lock (Target)

Entering Live Mode requires explicit CEO acknowledgment (e.g. "I
UNDERSTAND I AM RISKING REAL MONEY"), and stays locked until: Live
Trading Gate = PASSED, Schwab connection = HEALTHY, account
reconciliation = PASSED, risk systems = HEALTHY, Emergency Stop =
READY, and audit system = HEALTHY. This is the CEO-facing enforcement
surface for the Live Trading Gate below — not a separate policy.

### Phase 10 — Paper → Shadow → Live (Target)

Three validation stages, in order, none skippable: **Paper** — no real
brokerage activity (today's `PaperExecutionProvider`, unchanged).
**Shadow** — TradeTown generates what it would execute while real
market/account information is monitored against Schwab; no real orders
are ever placed in this stage. **Live** — real orders become possible
only after every gate in Phase 7 and Phase 9 passes.

### Phase 11 — Live Execution Monitoring (Target)

Every state a live order can pass through must be monitored and
logged: submitted, acknowledged, accepted, rejected, partially filled,
filled, cancelled, expired, plus broker errors, connection status,
execution latency, and unexpected broker responses. `OrderStatus`
(`schemas.py`) would need real expansion beyond today's `"open" |
"filled" | "closed" | "cancelled"` to represent these states honestly
— not silently mapped onto the paper engine's narrower state machine.

### Phase 12 — Fail-Safe Behavior (Target)

New orders must stop the instant any of the following becomes true:
Schwab connectivity unhealthy, account reconciliation failing, the risk
engine failing, the Trade Gatekeeper failing, market data going stale,
authentication expiring, or Emergency Stop activating (which follows
the existing Emergency Stop protocol in addition to halting new
orders). TradeTown must never assume an order succeeded merely because
the request was sent — every fill must be confirmed, never inferred.

### Phase 13 — Audit Trail (Target)

Every live brokerage action must record: timestamp, account, trading
mode, strategy, order ID, internal trade ID, symbol, side, quantity,
order type, requested price, execution price, status, broker response,
risk decision, gatekeeper decision, CEO approval (when required), and
result. This is a real superset of today's capped `PaperOrder`
resolved-order log (Execution Logging, above) — the same fields that
log already carries, plus every field only a real broker connection
could ever populate.

### Phase 14 — The Live Trading Gate

Live Schwab connectivity must remain disabled until all of the
following hold, checked and confirmed in writing, never assumed:
Chapters 67–75 are complete; every required Design Bible requirement
touching this chapter is implemented; Risk systems are operational;
Emergency Stop is operational; Trading Modes are operational; the Daily
Loss Circuit Breaker is operational; Losing Streak Protection is
operational; Audit systems are operational; portfolio reconciliation
(Phase 6) is operational; paper trading has been validated extensively;
Shadow trading (Phase 10) has been validated; broker adapter tests
pass; a security review passes; failure/recovery testing passes; and
the CEO explicitly authorizes the transition. This restates, and does
not loosen, the same standing policy in [Appendix
G](../../appendices/appendix-g-permanent-development-policy.md): no
future session should build toward a live connector, request broker
credentials, or wire a real execution endpoint without first
confirming, explicitly and in writing, that every condition above
holds.

### Phase 15 — Progressive Live Rollout (Target)

Even after the Live Trading Gate passes, live automation must not be
enabled unrestricted all at once. Recommended progression, each stage
gated on the previous one's demonstrated reliability: **Stage 1** —
read-only Schwab connection only. **Stage 2** — account/position
reconciliation, still no orders. **Stage 3** — manual, CEO-approved
live orders only, no automation. **Stage 4** — restricted automated
execution under very conservative limits. **Stage 5** — gradual
expansion, only after each prior stage has proven reliable in practice,
not on paper.

### Design Principle

Charles Schwab must be treated as an external execution venue, never as
the foundation TradeTown is built on. TradeTown's own Risk, Strategy,
Execution, Governance, Audit, Portfolio, Decision, and Emergency
systems must remain broker-independent — the Schwab connector is simply
the final execution adapter, exactly the role `ExecutionProvider`
(Phase 1, real today) already exists to constrain it to. The broker
integration must never be allowed to bypass any of TradeTown's
institutional controls, in any phase, for any reason.

**The Live Trading Gate** (see [Appendix
G](../../appendices/appendix-g-permanent-development-policy.md)) is the
standing policy on exactly when this section stops being pure
architecture: Chapter 68 shall not connect to any live brokerage until
Chapters 67–75 are complete, paper trading has been extensively tested,
backtesting is validated, Risk Authority is fully operational,
Emergency Stop is verified, Audit Center is operational, and the CEO
explicitly enables Live Trading Mode. Charles Schwab v1.0 is one of the
final V1.0 milestones, built only after every system this platform's
paper-trading proof depends on is real and proven — never the vehicle
that proves them.

## Future Expansion

Interactive Brokers, Alpaca, Tradier, Tastytrade, Webull, Fidelity,
Crypto Exchanges, Futures Brokers, International Brokers, Automatic
Broker Failover, Multiple Simultaneous Brokers, and Institutional OMS
Integration all require a real broker connection this codebase's
100%-simulated engine does not have. Matches Chapter 66's own Future
Expansion precedent exactly: not invented or stubbed here, because
nothing here has the real foundation to build on yet.

## Design Bible Integration

**Real today, already true for the simulated broker, and would carry
forward unchanged to a real one:** every simulated fill already updates
Company Memory (`app/scribe.py`), Portfolio (`app/portfolio.py`), and
Company Health (derived from the same portfolio state) — the same real
event pipeline a live connector's fills would flow through, since IBMS
is designed to plug in behind `broker.py`'s existing seam, not replace
the systems downstream of it. **Not built:** a named, distinct "Audit
Center" surface — today's audit trail is the capped order log described
above, not a dedicated reviewable center.

## Company Principle

"TradeTown never trusts that an order succeeded — it verifies
everything" is the single most important standard for whichever
connector is built first, and today's `PaperBroker` cannot yet
demonstrate it: there is nothing external to verify against, only a
deterministic in-memory fill. This is the one line in this whole
chapter every future implementer should re-read before writing Charles
Schwab v1.0 — verification-first has to be the connector's own design
from its first commit, not a feature added after the fact once
something has already gone wrong silently.

## Implementation Notes

**What's real today, found by direct research before this chapter was
written, not assumed:** a real, working, fully simulated order-book
engine (`app/broker.py`'s `PaperBroker`) that already implements the
narrow slice of this brief that doesn't require a real broker — order
placement, deterministic fills, a capped execution log, and the
approved-order handoff seam from Chapters 57/58/66's own real
pre-trade veto pipeline; a real, proven adapter-interface *pattern*
(`app/market_data.py`'s `MarketDataProvider`) for how a future
connector could be wired in without touching its consumers, previously
applied only to market data. **Part 1 (this session) extended that
pattern to execution:** `ExecutionProvider(ABC)` +
`PaperExecutionProvider` + `_select_execution_provider()` + a module-level
`execution_provider` singleton in `app/broker.py`, with
`app/nexus.py`'s one real `tick_broker()` call site rewired through it
— see "Part 1: Execution Provider Adapter Interface" above. A single,
real, honest `"SIMULATED"` acknowledgment remains surfaced to the CEO
(`GlobalStatusBar.tsx`), unchanged by Part 1. **What's genuinely,
entirely unbuilt:** broker connections, authentication, encrypted
credentials, API sessions, order routing to anything external,
execution confirmation against a real system, account synchronization,
buying power beyond a cash-reserve floor, position reconciliation,
latency/health monitoring, a multi-account model, Charles Schwab v1.0
itself, and every KPI/report/learning-loop that depends on a real
broker existing to measure against. Every other section of this
chapter beyond Part 1 remains architecture only, exactly matching how
Chapters 65/66/67 were each written first as pure documentation before
any implementation began.
