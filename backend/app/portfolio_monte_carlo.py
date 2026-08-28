"""CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
final follow-up — a real portfolio-level Monte Carlo / risk-of-ruin.

The original directive's own "Not built this pass" list named this
explicitly: "per-strategy Monte Carlo already exists and is real
(app/strategy_lab.py); a portfolio-level version was not attempted this
pass." This module closes that gap.

WHY THIS IS A DIFFERENT METHODOLOGY, NOT A COPY OF strategy_lab.py's
run_strategy_monte_carlo() — read before assuming this duplicates that
function: the strategy-level bootstrap draws synthetic win/loss outcomes
from a strategy's own AGGREGATED stats (win rate, average win %, average
loss %) computed over its SimulationResult history — backtested data,
and a PARAMETRIC bootstrap (every simulated trade is either "the average
win" or "the average loss," nothing in between). A portfolio has no
equivalent SimulationResult history to aggregate from — its only real
track record is PaperPortfolio.trade_history, the account's own actual
closed paper trades. So this module instead runs a real HISTORICAL (or
"empirical") bootstrap: it resamples, with replacement, the REAL
observed sequence of per-trade percent-of-equity-at-the-time impacts —
not a synthetic win/loss draw, but literally what the account's own real
trades actually did to its own real equity, in whatever mix of trade
sizes and outcomes really occurred. This is standard practice for
resampling an empirical returns distribution when no parametric model is
trusted, and it naturally captures real skew/fat-tails in a way a
binary win/loss model cannot.

REAL PER-TRADE IMPACT, NOT pnl_pct: `PaperTrade.pnl_pct` is that
POSITION's own percent return (e.g. "this AAPL trade was +5%"), not its
impact on the whole account — a $500 win on a $100,000 account and the
same $500 win on a $10,000 account both show the same pnl_pct but very
different portfolio impacts. This module instead computes
`trade.pnl / equity_at_the_time`, walking trade_history in its real
chronological order (the same append-only order and equity-walk
convention app/analytics.py::real_peak_equity() already established),
so every resampled number is the real historical fraction of THIS
account's own equity that trade actually moved.

RUIN, DEFINED AGAINST THE CEO'S OWN REAL LIMIT: strategy_lab.py's
RUIN_DRAWDOWN_PCT is a fixed, disclosed 50% bar, appropriate for judging
one strategy's own standalone hypothetical capital. At the portfolio
level, this account already has a real, CEO-configured
RiskLimits.max_drawdown_pct ceiling — using that instead of a second,
invented number means this answers a directly actionable question: "how
often would a real repeat of my own trading history have breached the
risk ceiling I've actually set." Disclosed on every result
(`ruinThresholdPct`), never hidden.

COMPUTED FRESH, NEVER PERSISTED (the CAGS convention this codebase's
PortfolioIntelligence/EconomicIntelligence/PortfolioRiskSnapshot already
use) — no new GameSaveState field, no cap-management, always reflects
today's real trade_history. Deterministically seeded (see `_seeded_rng`
below, the identical hashlib.sha256(...) -> random.Random(...)
convention strategy_lab.py's own `_seeded_rng()` already uses) from the
real trade ids and starting balance on file, so re-running this against
identical data always reproduces the identical result — never a
different answer to the same real evidence.

HONEST LIMITATIONS, disclosed rather than hidden: an empirical bootstrap
can only ever resample outcomes that have already happened — it cannot
imagine a worse single trade than the worst one on record, and with a
short trade history the resampled distribution is a small, noisy sample
of the account's true long-run behavior (see MIN_TRADES_FOR_MONTE_CARLO
below — this function honestly returns None rather than bootstrapping
from too few real trades). It also assumes each trade's percent-impact
is independent of the ones around it (no serial correlation/regime
memory) — a real simplification, the same one every bootstrap
methodology in this codebase already makes.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from app.schemas import PaperPortfolio, PortfolioMonteCarloResult, RiskLimits

# Same 200-path convention app/strategy_lab.py's MONTE_CARLO_PATHS
# already established — reused, not reinvented (see
# app/quant_developer.py for existing precedent of importing this exact
# constant across a module boundary).
from app.strategy_lab import MONTE_CARLO_PATHS

# Same reasoning and value as app/strategy_lab.py's
# MIN_RETIREMENT_TRADE_COUNT — just enough real evidence that an "not
# enough data yet" conclusion is honestly unavoidable below this bar,
# reused here for the same real-evidence discipline.
MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seeded_rng(*parts: str) -> random.Random:
    """Identical convention to app/strategy_lab.py's own `_seeded_rng()`
    — duplicated rather than cross-imported (that one is module-private,
    leading underscore), the same "small, stable helper duplicated
    across a module boundary, not cross-imported" precedent
    app/gatekeeper.py's own `_WEDE_TRADING_ACTIONS` already establishes
    for a small, stable value shared with app/executive_intelligence.py."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    return sorted_values[idx]


def _tail_mean(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    tail = sorted_values[: idx + 1]
    return sum(tail) / len(tail)


def _real_trade_percent_impacts(portfolio: PaperPortfolio) -> list[float]:
    """Walks trade_history in its real chronological (append-only)
    order, exactly like app/analytics.py::real_peak_equity(), producing
    one real `pnl / equity_at_the_time` fraction per closed trade — the
    account's own real historical returns series to bootstrap from."""
    impacts: list[float] = []
    equity = portfolio.starting_balance
    for trade in portfolio.trade_history:
        # Defensive floor only — a real account this codebase's own risk
        # gates allow to reach zero/negative equity mid-history is not a
        # scenario expected in practice; skips dividing by a
        # non-positive number rather than fabricating a fraction.
        if equity > 0:
            impacts.append(trade.pnl / equity)
        equity += trade.pnl
    return impacts


def compute_portfolio_monte_carlo(
    portfolio: PaperPortfolio, risk_limits: RiskLimits, *, sim_day: int, trades_per_path: int | None = None
) -> PortfolioMonteCarloResult | None:
    """None when there isn't enough real closed-trade history yet (see
    MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO) — never a bootstrap from too
    thin a real sample. `trades_per_path` defaults to the account's own
    real trade count (simulating a path as long as its actual history),
    matching run_strategy_monte_carlo()'s own "use the real observed
    count" convention."""
    impacts = _real_trade_percent_impacts(portfolio)
    if len(impacts) < MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO:
        return None

    path_length = trades_per_path if trades_per_path is not None else len(impacts)
    win_count = sum(1 for i in impacts if i > 0)
    source_win_rate_pct = round(win_count / len(impacts) * 100, 1)

    rng = _seeded_rng(*(t.id for t in portfolio.trade_history), f"{portfolio.starting_balance:.2f}", str(path_length))

    finals: list[float] = []
    max_drawdowns: list[float] = []
    ruin_count = 0
    ruin_threshold_pct = risk_limits.max_drawdown_pct
    for _ in range(MONTE_CARLO_PATHS):
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for _trade in range(path_length):
            r = rng.choice(impacts)
            cumulative = (1 + cumulative) * (1 + r) - 1
            peak = max(peak, cumulative)
            max_drawdown = min(max_drawdown, cumulative - peak)
        finals.append(cumulative)
        max_drawdowns.append(max_drawdown)
        if abs(max_drawdown) * 100 >= ruin_threshold_pct:
            ruin_count += 1

    finals.sort()
    max_drawdowns.sort()
    probability_of_ruin = round(ruin_count / MONTE_CARLO_PATHS * 100, 1)

    return PortfolioMonteCarloResult(
        id=f"portfolio-montecarlo-{sim_day}",
        pathsSimulated=MONTE_CARLO_PATHS,
        tradesPerPath=path_length,
        sourceTradeCount=len(impacts),
        sourceWinRatePct=source_win_rate_pct,
        startingEquity=portfolio.starting_balance,
        medianReturnPct=round(_percentile(finals, 0.50) * 100, 2),
        returnRangeLowPct=round(_percentile(finals, 0.10) * 100, 2),
        returnRangeHighPct=round(_percentile(finals, 0.90) * 100, 2),
        medianMaxDrawdownPct=round(abs(_percentile(max_drawdowns, 0.50)) * 100, 2),
        worstCaseDrawdownPct=round(abs(_percentile(max_drawdowns, 0.05)) * 100, 2),
        probabilityOfProfitPct=round(sum(1 for f in finals if f > 0) / len(finals) * 100, 1),
        ruinThresholdPct=ruin_threshold_pct,
        probabilityOfRuinPct=probability_of_ruin,
        capitalSurvivalPct=round(100 - probability_of_ruin, 1),
        valueAtRisk95Pct=round(_percentile(finals, 0.05) * 100, 2),
        valueAtRisk99Pct=round(_percentile(finals, 0.01) * 100, 2),
        conditionalValueAtRisk95Pct=round(_tail_mean(finals, 0.05) * 100, 2),
        conditionalValueAtRisk99Pct=round(_tail_mean(finals, 0.01) * 100, 2),
        simDay=sim_day,
        createdAt=_now_iso(),
    )
