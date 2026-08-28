"""Covers app/portfolio_monte_carlo.py — CEO directive "Portfolio Risk
Engine + Firm-Wide Risk Governance," final follow-up. A real historical
bootstrap over PaperPortfolio.trade_history's own real per-trade
percent-of-equity impacts — never the strategy-level's parametric
win-rate/avg-win/avg-loss bootstrap, and never a fabricated result below
MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO real trades."""
from __future__ import annotations

from app.portfolio import default_portfolio
from app.portfolio_monte_carlo import (
    MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO,
    _real_trade_percent_impacts,
    compute_portfolio_monte_carlo,
)
from app.schemas import PaperTrade, RiskLimits

_TRADE_DEFAULTS = {
    "id": "trade-x",
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 1.0,
    "entryPrice": 100.0,
    "exitPrice": 100.0,
    "durationMinutes": 30,
    "confidence": 80.0,
    "reason": "test",
    "marketConditions": "test",
    "supportingAgents": ["scout"],
    "opposingAgents": [],
    "openedAt": "2024-01-01T00:00:00+00:00",
    "closedAt": "2024-01-01T00:00:00+00:00",
    "openedSimMinutes": 0,
}


def _trade(n: int, pnl: float) -> PaperTrade:
    return PaperTrade.model_validate({**_TRADE_DEFAULTS, "id": f"trade-{n}", "pnl": pnl, "pnlPct": pnl / 1000.0 * 100})


def _portfolio_with_trades(trades: list[PaperTrade], *, starting_balance: float = 100_000.0):
    portfolio = default_portfolio().model_copy(update={"starting_balance": starting_balance, "cash_balance": starting_balance})
    equity = starting_balance
    for t in trades:
        equity += t.pnl
    return portfolio.model_copy(update={"trade_history": trades, "cash_balance": equity})


class TestRealTradePercentImpacts:
    def test_empty_history_is_empty(self) -> None:
        assert _real_trade_percent_impacts(default_portfolio()) == []

    def test_computes_pnl_over_equity_at_the_time_not_pnl_pct(self) -> None:
        # A $1,000 win on a $100,000 account is a real +1% portfolio
        # impact — regardless of what pnl_pct says about the position
        # itself (set here to something unrelated, 37%, to prove this
        # function ignores it).
        trade = PaperTrade.model_validate({**_TRADE_DEFAULTS, "pnl": 1_000.0, "pnlPct": 37.0})
        portfolio = _portfolio_with_trades([trade])
        impacts = _real_trade_percent_impacts(portfolio)
        assert len(impacts) == 1
        assert round(impacts[0], 4) == 0.01

    def test_walks_chronologically_so_later_trades_use_grown_equity(self) -> None:
        # First trade: +$10,000 on $100,000 = +10%. Second trade: -$5,000
        # on the now-$110,000 equity = a real -4.545...%, not -5%.
        trades = [_trade(1, 10_000.0), _trade(2, -5_000.0)]
        portfolio = _portfolio_with_trades(trades)
        impacts = _real_trade_percent_impacts(portfolio)
        assert round(impacts[0], 4) == 0.1
        assert round(impacts[1], 4) == round(-5_000.0 / 110_000.0, 4)


class TestComputePortfolioMonteCarlo:
    def test_none_below_the_minimum_real_trade_count(self) -> None:
        trades = [_trade(i, 100.0) for i in range(MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO - 1)]
        portfolio = _portfolio_with_trades(trades)
        assert compute_portfolio_monte_carlo(portfolio, RiskLimits(), sim_day=10) is None

    def test_real_result_at_the_minimum_real_trade_count(self) -> None:
        trades = [_trade(i, 100.0 if i % 2 == 0 else -50.0) for i in range(MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO)]
        portfolio = _portfolio_with_trades(trades)
        result = compute_portfolio_monte_carlo(portfolio, RiskLimits(), sim_day=10)
        assert result is not None
        assert result.source_trade_count == MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO
        assert result.paths_simulated == 200
        assert result.trades_per_path == MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO
        assert result.starting_equity == 100_000.0

    def test_ruin_threshold_is_the_real_configured_risk_limit_not_a_fabricated_bar(self) -> None:
        trades = [_trade(i, 100.0 if i % 2 == 0 else -50.0) for i in range(20)]
        portfolio = _portfolio_with_trades(trades)
        limits = RiskLimits(maxDrawdownPct=17.5)
        result = compute_portfolio_monte_carlo(portfolio, limits, sim_day=10)
        assert result is not None
        assert result.ruin_threshold_pct == 17.5

    def test_a_consistently_winning_history_produces_a_low_probability_of_ruin(self) -> None:
        # Every real trade a small, steady win — a real historical
        # bootstrap of this can never produce a large drawdown, since
        # every resampled trade is drawn from the same all-positive pool.
        trades = [_trade(i, 200.0) for i in range(20)]
        portfolio = _portfolio_with_trades(trades)
        result = compute_portfolio_monte_carlo(portfolio, RiskLimits(), sim_day=10)
        assert result is not None
        assert result.probability_of_ruin_pct == 0.0
        assert result.probability_of_profit_pct == 100.0
        assert result.source_win_rate_pct == 100.0

    def test_a_consistently_losing_history_produces_certain_ruin(self) -> None:
        trades = [_trade(i, -5_000.0) for i in range(20)]
        portfolio = _portfolio_with_trades(trades)
        result = compute_portfolio_monte_carlo(portfolio, RiskLimits(maxDrawdownPct=20.0), sim_day=10)
        assert result is not None
        assert result.probability_of_ruin_pct == 100.0
        assert result.source_win_rate_pct == 0.0

    def test_deterministic_for_identical_real_evidence(self) -> None:
        trades = [_trade(i, 100.0 if i % 3 else -80.0) for i in range(15)]
        portfolio = _portfolio_with_trades(trades)
        limits = RiskLimits()
        first = compute_portfolio_monte_carlo(portfolio, limits, sim_day=10)
        second = compute_portfolio_monte_carlo(portfolio, limits, sim_day=10)
        assert first is not None and second is not None
        assert first.median_return_pct == second.median_return_pct
        assert first.probability_of_ruin_pct == second.probability_of_ruin_pct
        assert first.value_at_risk_95_pct == second.value_at_risk_95_pct

    def test_different_real_trade_histories_produce_different_results(self) -> None:
        winners = [_trade(i, 500.0) for i in range(15)]
        losers = [_trade(i, -500.0) for i in range(15)]
        result_winners = compute_portfolio_monte_carlo(_portfolio_with_trades(winners), RiskLimits(), sim_day=10)
        result_losers = compute_portfolio_monte_carlo(_portfolio_with_trades(losers), RiskLimits(), sim_day=10)
        assert result_winners is not None and result_losers is not None
        assert result_winners.median_return_pct != result_losers.median_return_pct

    def test_custom_trades_per_path_is_honored(self) -> None:
        trades = [_trade(i, 100.0 if i % 2 == 0 else -50.0) for i in range(15)]
        portfolio = _portfolio_with_trades(trades)
        result = compute_portfolio_monte_carlo(portfolio, RiskLimits(), sim_day=10, trades_per_path=40)
        assert result is not None
        assert result.trades_per_path == 40
        assert result.source_trade_count == 15  # the real sample size is unchanged
