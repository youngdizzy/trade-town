# Chapter 68 — Institutional Broker Management System (IBMS)

**Status:** Pure architecture, not yet implemented. **Researched
first:** this codebase has exactly one order-execution engine
(`app/broker.py`'s `PaperBroker`), and its own module docstring has
stated since v0.6 that it is "completely simulated" — no brokerage SDK
import, no API key, no code path that reaches a real execution
endpoint. That finding, and every other real-vs-aspirational line in
this chapter, is not new: Chapter 66's own Ownership table already
confirmed "Broker Failsafe... genuinely does not exist" for the same
reason. This chapter's job is to give that permanent boundary a real
architecture to grow into — the interface every future connector
(Charles Schwab first) would implement — without writing a single line
of code against it yet. See the Implementation Notes at the bottom for
the precise inventory of what's real today.

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
| "Order Routing" | `app/broker.py`'s `place_order()` | Appends an order to an in-memory book on the *same* `PaperPortfolio` TradeTown already owns. Routes to nothing external — there is no second, broker-side order book to route to. |
| "Order Verification" (Accepted/Partially Filled/Filled/Rejected/Cancelled/Expired/Pending/Unexpected State) | `OrderStatus` (`schemas.py`): `"open" \| "filled" \| "closed" \| "cancelled"` | A real, working, but much narrower state machine: `_fill_price()` fills an order entirely or not at all (**no partial fills exist**), a filled exit order closes its linked position, and — since Chapters 57/58/66's own pre-trade checks already run before an order can be placed at all — **"rejected" cannot happen inside `broker.py`**, only before it. No `"expired"`/time-in-force concept exists (`broker.py`'s own docstring: orders "stay open indefinitely until filled"). |
| "Buying Power Validation" (cash, margin, PDT, options/short permissions) | Chapter 57's Position Sizing cash-reserve floor (`app/nexus.py`) | Real, but narrower: checks `cashBalance` against a reserve floor before a proposal is even created. **No margin account, Pattern Day Trader restriction, options permission, or short-selling permission concept exists anywhere** — this is 100% simulated cash-account, long-only paper trading. |
| "Position Synchronization" | *(does not apply)* | There is exactly one ledger — TradeTown's own `PaperPortfolio.positions` — with no second, broker-side position list to compare it against. Reconciliation, as the brief defines it, needs two sources of truth; today there is only one. |
| "Latency Monitoring" / "Broker Health" | `GlobalStatusBar.tsx`'s `BROKER` pill | Honestly static: the label reads `"SIMULATED"`, always, with a tooltip citing `app/broker.py` directly (Chapter 67's own work). No latency, no health score, no state machine — the one real, deliberate acknowledgment that nothing else in this row exists. |
| "Execution Logs" / "Audit Trail" | `PaperOrder`'s own resolved-order log (`MAX_ORDER_LOG = 40`, capped) | Real precedent, incomplete against the brief's own field list: `id`/`symbol`/`side`/`orderType`/`quantity`/`price`/`status`/`reason`/`placedBy`/`confidence`/`filledPrice`/`filledAt` exist; `Broker`, `Account`, and `Latency` do not, because none of those concepts exist yet to log. |
| "Account Management" (Personal/Paper/Business/IRA, multi-account) | `PaperPortfolio` (`schemas.py`) | One account. Its own docstring: "the company's one simulated trading account." No account ID, broker field, permissions, risk profile, currency, or status field exists — there is nothing to distinguish, because nothing to distinguish it from. |
| "Broker States" (Connected/Connecting/Disconnected/Auth Failed/Rate Limited/Maintenance/Market Closed/Emergency Disabled) | *(does not exist)* | The closest real precedent is `net:status`/`gameStore.netConnected` — a real, working binary connected/disconnected indicator (`TopStatusBar.tsx`'s own dot) for TradeTown's **own** WebSocket to its **own** backend, not a broker connection of any kind. Reusable event/UI *pattern*, zero broker-specific meaning today. |
| "Multi-Broker Ready" / "one connector, no changes to existing ones" | `app/market_data.py`'s `MarketDataProvider` (ABC) | The one real, working precedent for this exact shape, proven out for market data, not execution: implement the interface, wire it in `_select_provider()`, nothing that calls it changes. No equivalent execution-side interface exists — `NexusManager`/`paper_trading.py` call `broker.py`'s functions directly today, not through an abstraction a second connector could sit behind. |

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

**Genuinely, entirely unbuilt.** Every requirement the brief lists —
secure authentication, paper trading support, live trading support,
account synchronization, buying power, position sync, order placement,
order cancellation, order status, execution confirmation — has zero
real backing anywhere in this codebase today. `app/broker.py`'s own
module docstring has named Charles Schwab, Interactive Brokers, and
Alpaca as hypothetical future adapters since v0.6; none has ever been
implemented, and no SDK for any of them is installed. This section is
the concrete target this whole chapter's architecture exists to make
possible — the first connector to actually implement the interface IBMS
describes — not a status update on work in progress.

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
connector could be wired in without touching its consumers, applied so
far only to market data, never to execution; a single, real, honest
`"SIMULATED"` acknowledgment already surfaced to the CEO
(`GlobalStatusBar.tsx`). **What's genuinely, entirely unbuilt:**
broker connections, authentication, encrypted credentials, API
sessions, order routing to anything external, execution confirmation
against a real system, account synchronization, buying power beyond a
cash-reserve floor, position reconciliation, latency/health
monitoring, a multi-account model, Charles Schwab v1.0 itself, and
every KPI/report/learning-loop that depends on a real broker existing
to measure against. No code was written against this chapter — it is
architecture only, exactly matching how Chapters 65/66/67 were each
written first as pure documentation before any implementation began.
