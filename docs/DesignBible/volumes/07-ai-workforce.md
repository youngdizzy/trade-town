# Volume 7 — AI Workforce

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

## What this volume will cover

- Employees
- Departments
- Academy
- Training
- Mentor Library
- Certifications
- Graduations
- Performance Reviews
- Psychology
- Knowledge Sharing
- Learning Systems
- Career Progression
- Hiring
- Retirement

## Where the real content lives today

- `backend/app/agents.py` — Employees (14 real agent profiles today:
  Scout, Atlas, Echo, Nova, Scribe, Coach, Sentinel, Pulse, Guardian,
  Meridian, Sage, Keystone, Compass, Vector).
- `backend/app/academy.py` / `backend/app/academy_research.py` — Academy,
  Training, Knowledge Sharing, Career Progression (real per-agent
  Knowledge Points and tiers).
- `backend/app/foundational_mentors.py` — Mentor Library, Certifications,
  Graduations.
- `backend/app/coach.py` — Performance Reviews.
- `backend/app/founders.py` — Retirement, real but narrow: Keystone and
  Compass's `FounderState.retired` flips permanently to True (Legendary
  Status) once company health sustains an "excellent" tier — a one-way
  transition, never reversed, and does not remove the founder from the
  roster.
- **Psychology and Hiring** have no real mechanic in this codebase today
  (the 14-agent roster is fixed; no agent is ever hired at runtime, and
  no agent has emotional/psychological state) — this volume should
  document that as a real, current gap, not imply it exists. Retirement
  beyond the two founders (an ordinary employee retiring) is likewise not
  built.

## Addendum — The Quant Organization (Quantitative Research & Intelligence System, Piece 1)

**Status:** Real, docs-only. No code changed by this piece — every role
named below was already doing this work under its existing name; this
addendum only makes the organizational structure explicit and
discoverable in one place. Per the CEO's own explicit instruction: *"Do
NOT rename an agent simply to make the organization look more
quantitative. Improve its actual capabilities."* Nothing here renames
`app/agents.py`'s `AgentProfile.name`/`.occupation` fields, adds a new
agent, or changes any agent's real behavior.

TradeTown's quant work is split across three real, independent
functions — the same separation Piece 4's Model Validator (see Chapter
62's own addendum) depends on and preserves:

**Chief Quant — Vector** (`agentId: "quant"`, occupation "Chief
Quantitative Strategist," `app/agents.py`). Leads every real Black Box
Research Project (`app/black_box.py`) and is the `"quant"` reviewer seat
on every `StrategyReview` (`app/sandbox.py`'s `_quant_verdict`) —
statistical-soundness research and strategy discovery, never risk
sign-off and never independent validation authority over its own work.

**Risk Quant — Sentinel, Guardian, and Keystone together**, a real
three-tier structure, not one seat wearing three names:
- **Sentinel** (`agentId: "sentinel"`, occupation "Risk Management") —
  the hard, per-trade gate: position size, open-position count, and
  portfolio drawdown (`app/risk_engine.py`'s `evaluate_sentinel_risk`).
  A failing check becomes a real `RiskWarning` that drives Sentinel's
  own analyst vote to "wait" and, if the CEO tries to force the trade
  anyway, fails `app/gatekeeper.py`'s `_risk_manager_check` — see
  `app/risk_engine.py`'s own module docstring.
- **Guardian** (`agentId: "guardian"`, occupation "Portfolio
  Protection") — the softer, per-trade concentration/exposure monitor:
  is this symbol or sector already a large share of the book
  (`evaluate_guardian_exposure`), the same shape as Sentinel's check but
  framed as "should we be worried" rather than "can this happen at
  all."
- **Keystone** (`agentId: "keystone"`, occupation "Chief Risk
  Architect") — the strategic, governance-level tier: a Founder board
  seat (`FILLED_BOARD_SEAT_AGENT_IDS` in `app/board.py`) whose real
  domain is Risk Management/Capital Preservation/Position Sizing at the
  Constitution-amendment level (`app/constitution.py`'s
  `FOUNDER_DOMAIN_KEYWORDS`) and Academy mentorship (`app/founders.py`),
  not a per-trade check — the company's risk conscience above the two
  tactical gates, not a third copy of them.

**Model Validator — Meridian (CIO)**, documented in full in
`docs/DesignBible/volumes/09-departments/chapter-62-innovation-lab-continuous-improvement.md`'s
own Piece 4 addendum — independent statistical validation of a
strategy before Company Review, organizationally separate from both the
research above and the risk tiers above it.

This is the real three-way separation the CEO's spec asked for: Vector
researches, Sentinel/Guardian/Keystone manage risk at their respective
tiers, and Meridian validates — cooperating without collapsing into one
general-purpose "Quant AI." **Quant Developer** (the spec's remaining
named role) has no real seat in this codebase yet and is tracked as a
separate, deferred future piece (7) — not claimed here. **Execution
Quant** now has a real mechanism, documented below — still no new named
agent (per Q3's original scoping decision), since the mechanism sits at
the shared execution choke point every trade already funnels through.

## Addendum — Execution Quant (Quantitative Research & Intelligence System, Piece 5)

**Status:** Real. `app/portfolio.py`'s `open_position()`/`close_position()`
now deduct a real transaction cost from the cash ledger on every fill —
confirmed by direct trace to be this codebase's one real execution choke
point (every live-trade caller, `app/executive.py`'s `resolve_proposal()`,
`app/paper_trading.py`, `app/trading_modes.py`'s `flatten_day_positions`,
funnels through these same two functions; `app/broker.py`'s
`place_order()`/`tick_broker()` path is real but confirmed unreachable —
zero production call sites, always operating on an empty order book). Per
Q3's original scoping decision, this ships **agent-agnostic** — no new
named agent — with the mechanism owned by the same real pre-execution
pipeline Gatekeeper's `evaluate_gatekeeper()` already gates: cost only
ever applies to a trade that already passed that check, since
`open_position()` is only ever called after it.

**Why a flat rate, not a data-driven model.** A slippage/cost model that
varied by real spread or order-book depth is not honestly buildable in
this codebase today — confirmed by direct research, not assumed. There
is no real bid-ask spread anywhere; `app/market_data.py`'s `Quote.volume`
is `random.uniform` mock data, not a real market signal; and
`app/market_intelligence.py`'s `LiquidityRead`/`StrategyLiquidityValidation`
are real price-action *pattern detectors* (equal-high/low clustering,
sweep-and-close-back), explicitly documented there as "never a claim
about real resting stop orders... real order-book/order-flow data this
codebase does not have." A cost that varied per-symbol by any of those
inputs would be deriving "realism" from numbers that are themselves
fabricated or pattern-inferred — the same trap `app/simulation.py`'s own
disclosed-placeholder Sharpe/Sortino already fell into for a different
metric, and which that module's docstring already declines to repeat.

So `TRANSACTION_COST_BPS = 5.0` (`app/portfolio.py`) is instead a real,
functioning mechanism built on one flat, deliberately chosen, fully
disclosed constant — standing in for combined commission + spread +
slippage as a single number, applied identically to every symbol and
every side. This is the honest tradeoff: real dollars leave the cash
ledger on every fill (not a cosmetic display number), every trade's
`pnl`/`pnlPct` is genuinely net of it, and the cost itself is fully
auditable (`PaperPosition.entry_cost_usd`, `PaperTrade.
transaction_cost_usd`) — but the *rate* is a disclosed assumption, not a
measured statistic, and the report/UI never claims otherwise.

**The mechanics.** Entry and exit each pay `TRANSACTION_COST_BPS` (5.0
bps = 0.05%) of that fill's own notional once, so a full round trip pays
it twice. `open_position()` deducts `notional + entry_cost` from cash
(no-op — unchanged portfolio, not a partial fill — if that total exceeds
available cash, the same "no-op, not error" philosophy the function's
docstring already establishes for its other affordability check).
`close_position()` nets `gross_pnl - (entry_cost_usd + exit_cost)` into
`pnl`, and recomputes `pnl_pct` as `pnl / (quantity * entry_price) * 100`
— algebraically identical to the pre-Piece-5 formula whenever cost is
0, so this is a strict generalization, not a redefinition.

**Verified:** 4 new tests (`tests/test_portfolio.py::TestTransactionCost`
— hand-computed entry-cost deduction from cash, a refusal case when cash
can't cover notional-plus-cost, hand-computed net pnl/pnl_pct on a real
round trip, and a legacy position with no `entry_cost_usd` — pre-Piece-5
save-compatibility — still closing cleanly with only the exit side's
cost applied). Full backend suite (1611 tests, up from 1607) passed
unchanged with zero other regressions — the 5bps rate is small enough
that no existing exact-value test assertion in any of the 13 other test
files that call `open_position`/`close_position` was affected.
`mypy`/`ruff` clean. Frontend: `PaperPosition.entryCostUsd`/
`PaperTrade.transactionCostUsd` added to `types.ts`;
`PerformancePanel.tsx`'s "Recent Trades" journal card now shows a real
per-trade cost line ("real, already netted above") whenever a trade's
cost is nonzero. `tsc -b --noEmit`/`eslint`/`vite build` clean.
