"""app/portfolio_intelligence.py — Enterprise Portfolio Intelligence
(v0.7 Feature 56).

GOAL (from the brief): "TradeTown should think like a professional hedge
fund, not an individual trader" — manage company capital as a whole,
not one trade at a time: cash allocation, category/correlation exposure,
a continuous Portfolio Heat read, capital efficiency, and an honest
opportunity-cost signal.

RESEARCHED FIRST. Before writing this module, this codebase's real
portfolio/risk state was mapped: `app/portfolio.py`'s `PaperPortfolio`
has no sector/correlation/heat field anywhere; `app/risk_engine.py`'s
`evaluate_guardian_exposure()`/`monitor_portfolio()` cover per-symbol
concentration and drawdown-limit breaches, and `app/gatekeeper.py`'s
`_correlation_check()` is a real but narrow category-co-occurrence gate
(same symbol's `ResearchCategory` appearing in >2 open positions) — none
of it is a real correlation coefficient, a heat score, or a capital-
efficiency read. This module is genuinely new, built on top of those
existing signals rather than duplicating them.

HONESTY BOUNDARY:

  "Sector" is called "category" throughout — this codebase has no real
  sector taxonomy (see app/risk_engine.py's evaluate_guardian_exposure()
  docstring for the identical, already-established note); every symbol's
  only real classification is its `ResearchCategory`
  (app/watchlist.py's SYMBOL_CATEGORY).

  Correlation Intelligence is a REAL Pearson correlation coefficient
  computed from each pair of currently-held symbols' own real recent
  candle-to-candle returns (the same Candle series every other technical
  read in this codebase already uses) — never an invented relationship.
  Only pairs clearing CORRELATION_CLUSTER_THRESHOLD are reported, so a
  portfolio of genuinely unrelated positions reports none.

  Portfolio Heat is a real, visible READING, never an automatic
  corrective action — this codebase's own documented v0.8 stop condition
  (docs/ROADMAP.md: "risk is measured and displayed, never auto-hedged
  or auto-corrected without the player") already forbids the brief's
  literal "automatically reduce exposure" ask. `PortfolioHeat.tier`
  surfaces the read; nothing in this module places, closes, or resizes
  an order.

  Capital Efficiency is real — computed only over `portfolio.trade_history`
  (actually-closed trades), never a forward-looking prediction.

  Max Drawdown is deliberately NOT duplicated here: `PerformanceSnapshot`
  (app/analytics.py) already computes a real max_drawdown_pct per period
  (daily/weekly/monthly/all_time) from the same trade history — an
  Executive Portfolio Dashboard should read that existing field, not a
  second one computed here.

CEO directive "Professional Quant Firm Phase," Feature 40's Tournament
Round 7 (portfolio interaction) — `pearson_correlation()` below (renamed
from a previously-private `_pearson()`, behavior unchanged) is exported
specifically so `app/strategy_tournament.py` can compute a real
correlation between candidate strategies' own walk-forward window
expectancy sequences using the exact same, already-tested Pearson
implementation this module uses for symbol-to-symbol price-return
correlation — never a second, duplicate statistics implementation.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone

from app.market_data import MarketDataProvider
from app.risk_engine import portfolio_equity
from app.schemas import (
    CapitalEfficiency,
    CategoryExposure,
    CorrelationPair,
    PaperPortfolio,
    PortfolioHeat,
    PortfolioIntelligence,
    ResearchCategory,
)
from app.watchlist import SYMBOL_CATEGORY

PROPOSAL_TIMEFRAME = "1h"
PROPOSAL_CANDLE_COUNT = 30

# A real Pearson coefficient above this magnitude is reported as a real
# cluster — high enough that only a genuinely tight relationship (the
# brief's own NVDA/AMD/QQQ/SMH/SOXL "one tech exposure" example) shows
# up, not routine market-wide co-movement.
CORRELATION_CLUSTER_THRESHOLD = 0.6

# Real total-capital-at-risk thresholds for the four heat tiers.
_HEAT_TIER_THRESHOLDS: tuple[tuple[float, str], ...] = ((75.0, "overheated"), (50.0, "hot"), (25.0, "warm"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pearson_correlation(a: list[float], b: list[float]) -> float:
    """A real Pearson coefficient over the two series' own most recent
    `min(len(a), len(b))` values (aligned from the end). `0.0` — never a
    crash — below 3 paired values or when either series has zero real
    variance (`statistics.StatisticsError`); callers needing to
    distinguish "measured, genuinely zero" from "not enough data" should
    check `min(len(a), len(b)) >= 3` themselves before calling (see
    app/strategy_tournament.py's own real-vs-None handling for its
    per-pair correlation reads)."""
    n = min(len(a), len(b))
    if n < 3:
        return 0.0
    a, b = a[-n:], b[-n:]
    try:
        return statistics.correlation(a, b)
    except statistics.StatisticsError:
        return 0.0


def _returns(prices: list[float]) -> list[float]:
    return [(cur - prev) / prev for prev, cur in zip(prices, prices[1:]) if prev]


def _category_exposure(portfolio: PaperPortfolio, equity: float) -> list[CategoryExposure]:
    totals: dict[ResearchCategory, list[float]] = {}
    counts: dict[ResearchCategory, int] = {}
    for pos in portfolio.positions:
        category = SYMBOL_CATEGORY.get(pos.symbol)
        if category is None:
            continue
        value = pos.quantity * pos.current_price
        totals.setdefault(category, []).append(value)
        counts[category] = counts.get(category, 0) + 1
    exposures = [
        CategoryExposure(category=category, positionCount=counts[category], value=round(sum(values), 2), pctOfEquity=round(sum(values) / equity * 100, 1) if equity > 0 else 0.0)
        for category, values in totals.items()
    ]
    exposures.sort(key=lambda e: e.pct_of_equity, reverse=True)
    return exposures


def _correlation_pairs(portfolio: PaperPortfolio, provider: MarketDataProvider) -> list[CorrelationPair]:
    symbols = sorted({pos.symbol for pos in portfolio.positions})
    if len(symbols) < 2:
        return []
    returns_by_symbol: dict[str, list[float]] = {}
    for symbol in symbols:
        try:
            candles = provider.get_candles(symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
        except ValueError:
            continue
        returns_by_symbol[symbol] = _returns([c.close for c in candles])

    pairs: list[CorrelationPair] = []
    for i, symbol_a in enumerate(symbols):
        for symbol_b in symbols[i + 1 :]:
            a, b = returns_by_symbol.get(symbol_a), returns_by_symbol.get(symbol_b)
            if not a or not b:
                continue
            correlation = pearson_correlation(a, b)
            if abs(correlation) >= CORRELATION_CLUSTER_THRESHOLD:
                pairs.append(CorrelationPair(symbolA=symbol_a, symbolB=symbol_b, correlation=round(correlation, 2), direction="positive" if correlation > 0 else "negative"))
    return pairs


def _heat(portfolio: PaperPortfolio, equity: float, category_exposure: list[CategoryExposure]) -> PortfolioHeat:
    if equity <= 0 or not portfolio.positions:
        return PortfolioHeat(totalCapitalAtRiskPct=0.0, unrealizedDrawdownPct=0.0, largestPositionPct=0.0, hottestCategory=None, hottestCategoryPct=0.0, tier="cool")

    total_at_risk = sum(pos.quantity * pos.current_price for pos in portfolio.positions) / equity * 100
    largest = max((pos.quantity * pos.current_price for pos in portfolio.positions), default=0.0) / equity * 100
    unrealized_drawdown = abs(portfolio.total_pnl_pct) if portfolio.total_pnl_pct < 0 else 0.0
    hottest = category_exposure[0] if category_exposure else None

    tier = "cool"
    for threshold, label in _HEAT_TIER_THRESHOLDS:
        if total_at_risk >= threshold:
            tier = label
            break

    return PortfolioHeat(
        totalCapitalAtRiskPct=round(total_at_risk, 1),
        unrealizedDrawdownPct=round(unrealized_drawdown, 1),
        largestPositionPct=round(largest, 1),
        hottestCategory=hottest.category if hottest else None,
        hottestCategoryPct=hottest.pct_of_equity if hottest else 0.0,
        tier=tier,  # type: ignore[arg-type]
    )


def _capital_efficiency(portfolio: PaperPortfolio) -> CapitalEfficiency:
    trades = portfolio.trade_history
    if not trades:
        return CapitalEfficiency(profitPerDollar=0.0, profitPerDollarHour=0.0, tradesMeasured=0)

    profit_per_dollar_values: list[float] = []
    profit_per_dollar_hour_values: list[float] = []
    for trade in trades:
        capital_locked = trade.entry_price * trade.quantity
        if capital_locked <= 0:
            continue
        per_dollar = trade.pnl / capital_locked
        profit_per_dollar_values.append(per_dollar)
        hold_hours = max(trade.duration_minutes / 60, 1 / 60)
        profit_per_dollar_hour_values.append(per_dollar / hold_hours)

    if not profit_per_dollar_values:
        return CapitalEfficiency(profitPerDollar=0.0, profitPerDollarHour=0.0, tradesMeasured=0)

    return CapitalEfficiency(
        profitPerDollar=round(statistics.mean(profit_per_dollar_values), 4),
        profitPerDollarHour=round(statistics.mean(profit_per_dollar_hour_values), 5),
        tradesMeasured=len(profit_per_dollar_values),
    )


def _opportunity_cost(cash_pct_of_equity: float, pending_proposal_count: int) -> str:
    """A real, specific read — never generic filler."""
    if pending_proposal_count > 0 and cash_pct_of_equity > 50.0:
        return f"{cash_pct_of_equity:.0f}% of equity is sitting in cash while {pending_proposal_count} real trade proposal(s) await a capital decision."
    if cash_pct_of_equity > 75.0:
        return f"{cash_pct_of_equity:.0f}% of equity is sitting in cash — a real, deliberate patience call, not idle waste, as long as it's intentional."
    if cash_pct_of_equity < 10.0:
        return f"Only {cash_pct_of_equity:.0f}% of equity remains in cash — little room left to act on the next high-quality opportunity without closing something first."
    return f"{cash_pct_of_equity:.0f}% of equity in cash, {100 - cash_pct_of_equity:.0f}% deployed — no immediate opportunity-cost concern on file."


def compute_portfolio_intelligence(portfolio: PaperPortfolio, provider: MarketDataProvider, *, pending_proposal_count: int) -> PortfolioIntelligence:
    equity = portfolio_equity(portfolio)
    category_exposure = _category_exposure(portfolio, equity)
    correlation_pairs = _correlation_pairs(portfolio, provider)
    heat = _heat(portfolio, equity, category_exposure)
    capital_efficiency = _capital_efficiency(portfolio)
    cash_pct = round(portfolio.cash_balance / equity * 100, 1) if equity > 0 else 0.0
    deployed_pct = round(100.0 - cash_pct, 1) if equity > 0 else 0.0

    return PortfolioIntelligence(
        equity=round(equity, 2),
        cashBalance=portfolio.cash_balance,
        cashPctOfEquity=cash_pct,
        deployedPctOfEquity=deployed_pct,
        categoryExposure=category_exposure,
        correlationPairs=correlation_pairs,
        heat=heat,
        capitalEfficiency=capital_efficiency,
        opportunityCost=_opportunity_cost(cash_pct, pending_proposal_count),
        updatedAt=_now_iso(),
    )
