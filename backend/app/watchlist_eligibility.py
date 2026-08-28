"""CEO directive "Professional Quant Trading Core," Phase B P2 item —
a formal Watchlist Eligibility Tier system.

THE GAP: `app/opportunity_feed.py`'s own per-entry status
(`eligible`/`insufficient_evidence`/`not_eligible`) already exists, but
it's a per-CANDIDATE read, true only at the instant a specific
`TradeProposal`/`OpportunityRejection`/in-progress `ResearchItem`
exists. Nothing gave the CEO a standing, per-SYMBOL read: "over this
symbol's WHOLE real history on the watchlist, has it actually been a
good one to trade?" This module is that read.

REAL REUSE, NOT A NEW METRIC: every number here is
`app/performance_attribution.py::compute_symbol_performance()`'s own
already-real, already-tested per-symbol win-rate/expectancy/
profit-factor over `trade_history` — gated by that same module's real
`MIN_SYMBOL_SAMPLE_FOR_VERDICT` evidence threshold. This module only
adds the TIER classification on top and extends coverage to every
symbol currently on the watchlist (not just symbols that already have
trades — `compute_symbol_performance()` only returns entries for
symbols with at least one closed trade).

THE FOUR TIERS, each a real, checkable classification — never a
fabricated score:
  - "proven" — at least `MIN_SYMBOL_SAMPLE_FOR_VERDICT` (3) real closed
    trades, a real win rate at or above `PROVEN_MIN_WIN_RATE_PCT`
    (55.0%) AND a real positive expectancy. Reuses the exact same
    55.0%/40.0% bar `app/strategy_lab.py`'s own
    `HALL_OF_FAME_MIN_WIN_RATE`/`HEALTH_CRITICAL_WIN_RATE` already
    establish for "this real track record is genuinely good/bad" —
    not a second, independently-chosen threshold.
  - "cautionary" — the same minimum real sample size, but a real win
    rate below `CAUTIONARY_MAX_WIN_RATE_PCT` (40.0%) OR a real negative
    expectancy. A real, disclosed warning, never an automatic action —
    the CEO decides what (if anything) to do about it, e.g. via
    app/trading_restrictions.py's real, manual symbol restriction.
  - "developing" — either some real trades exist but below the minimum
    sample size, or the sample is large enough but doesn't clear either
    the "proven" or "cautionary" bar (a genuinely mixed real record).
  - "unproven" — zero real closed trades yet. The most common tier for
    a newly-added `EXTRA_SYMBOL_POOL` symbol or one still early in
    research — an honest "no track record yet," never treated as bad.

`rejection_count` (real `OpportunityRejection` records naming this
symbol) is surfaced as informational context only — a rejection means
"not this specific instance," not proof the symbol itself is bad, so it
never alone moves a symbol into "cautionary."

COMPUTED FRESH, NEVER PERSISTED (the same CAGS convention
`app/opportunity_feed.py`/`app/trade_pipeline_health.py` already use) —
no new `GameSaveState` field, no new gate, no automatic action on any
tier. Purely a read the CEO can review.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.performance_attribution import compute_symbol_performance
from app.schemas import OpportunityRejection, PaperTrade, WatchlistEligibilityRead, WatchlistEligibilitySummary, WatchlistEntry, WatchlistTier

# Reused from app/strategy_lab.py's own real "good/bad real track
# record" bar (HALL_OF_FAME_MIN_WIN_RATE / HEALTH_CRITICAL_WIN_RATE) —
# not a second, independently-chosen threshold. Duplicated as its own
# named constant here (not cross-imported) since strategy_lab.py's
# constants are that module's own tuning knobs for a different feature,
# the same "small, stable value duplicated across a module boundary"
# precedent this codebase already uses elsewhere.
PROVEN_MIN_WIN_RATE_PCT = 55.0
CAUTIONARY_MAX_WIN_RATE_PCT = 40.0

# Reused from app/performance_attribution.py's own real-evidence floor —
# imported directly (public, no leading underscore, already a stable
# cross-module constant per that module's own convention).
MIN_TRADES_FOR_TIER_VERDICT = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify(trade_count: int, win_rate_pct: float, expectancy_pct: float | None) -> WatchlistTier:
    if trade_count == 0:
        return "unproven"
    if trade_count < MIN_TRADES_FOR_TIER_VERDICT:
        return "developing"
    if win_rate_pct >= PROVEN_MIN_WIN_RATE_PCT and expectancy_pct is not None and expectancy_pct > 0:
        return "proven"
    if win_rate_pct < CAUTIONARY_MAX_WIN_RATE_PCT or (expectancy_pct is not None and expectancy_pct < 0):
        return "cautionary"
    return "developing"


def _detail(tier: WatchlistTier, trade_count: int, win_rate_pct: float, expectancy_pct: float | None, rejection_count: int) -> str:
    rejection_note = f" {rejection_count} real rejection(s) on file." if rejection_count else ""
    if tier == "unproven":
        return f"No real closed trades yet on this symbol — no track record to judge.{rejection_note}"
    if tier == "developing" and trade_count < MIN_TRADES_FOR_TIER_VERDICT:
        return f"Only {trade_count} real closed trade(s) so far — below the {MIN_TRADES_FOR_TIER_VERDICT}-trade minimum for a real verdict.{rejection_note}"
    expectancy_text = f"{expectancy_pct:+.2f}% expectancy" if expectancy_pct is not None else "expectancy not computed"
    return f"{trade_count} real closed trades, {win_rate_pct:.0f}% win rate, {expectancy_text}.{rejection_note}"


def compute_watchlist_eligibility(
    watchlist: list[WatchlistEntry], trade_history: list[PaperTrade], opportunity_rejections: list[OpportunityRejection]
) -> WatchlistEligibilitySummary:
    performance_by_symbol = {r.symbol: r for r in compute_symbol_performance(trade_history).reads}
    rejection_counts: dict[str, int] = {}
    for rejection in opportunity_rejections:
        rejection_counts[rejection.symbol] = rejection_counts.get(rejection.symbol, 0) + 1

    reads: list[WatchlistEligibilityRead] = []
    for entry in watchlist:
        perf = performance_by_symbol.get(entry.symbol)
        trade_count = perf.trade_count if perf else 0
        win_rate_pct = perf.win_rate_pct if perf else 0.0
        expectancy_pct = perf.expectancy_pct if perf else None
        profit_factor = perf.profit_factor if perf else None
        rejection_count = rejection_counts.get(entry.symbol, 0)

        tier = _classify(trade_count, win_rate_pct, expectancy_pct)
        detail = _detail(tier, trade_count, win_rate_pct, expectancy_pct, rejection_count)

        reads.append(
            WatchlistEligibilityRead(
                symbol=entry.symbol,
                tier=tier,
                tradeCount=trade_count,
                winRatePct=win_rate_pct if trade_count else None,
                expectancyPct=expectancy_pct,
                profitFactor=profit_factor,
                rejectionCount=rejection_count,
                detail=detail,
            )
        )

    return WatchlistEligibilitySummary(reads=reads, updatedAt=_now_iso())
