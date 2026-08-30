"""SimulationManager — the Simulation Lab's backend engine.

Owns four related concepts, all defined in app/schemas.py:
  - Strategy         a named research approach an agent authored
  - BacktestSession   one strategy run, queued/running (this module's
                      "SimulationQueue" is simply the list of sessions
                      filtered by status)
  - StrategyRunner    not a class — the run_strategy_step() function
                      below, advancing every active session's progress
                      one tick's worth, mirroring research.py's
                      confidence-gain-per-tick shape
  - SimulationResult  a completed run's output, archived once a session
                      finishes

v0.5 ships one historical-data path: entirely placeholder math (see
`_placeholder_backtest_metrics` below), because TradeTown has no real
historical `MarketDataProvider` yet (`app/market_data.py` ships mock
live-quote data only). The module is deliberately structured so a real
historical provider, a Monte Carlo variant (many placeholder runs per
session instead of one, varying the random seed), and a parameter
optimizer (multiple sessions per strategy across a parameter grid) can
all be added later as new functions that still produce a SimulationResult
— no other part of the pipeline (queueing, progress, archiving) needs to
change. See docs/FUTURE_ARCHITECTURE.md.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.schemas import AgentId, BacktestSession, ResearchCategory, SimulationResult, Strategy, TestScenario, TimeState, WatchlistEntry

MAX_CONCURRENT_SESSIONS = 2
MAX_SIMULATION_RESULTS = 30
QUEUE_CHANCE_PER_TICK = 0.05
PROGRESS_GAIN_RANGE = (8.0, 18.0)

# v0.7 Feature 45 — per-Testing-Environment win/loss ranges. Each tuple is
# (avg_win_pct range, avg_loss_pct range, win_rate range, max_drawdown_pct
# range) — real, hand-chosen, and honestly still placeholder (see this
# module's own docstring), but now the *generating* inputs rather than an
# independently-invented total_return_pct: total_return_pct, expected
# value, profit factor, and risk/reward are all derived FROM these same
# per-run numbers below, so a run's own reported metrics are always
# internally consistent with each other. "historical" keeps the exact
# distribution v0.5 shipped with. Reuses the same 5 regime names
# app/market_environment.py already computes live — see schemas.py's
# TestScenario for why "earnings_weeks"/"economic_news" aren't here.
_SCENARIO_RANGES: dict[TestScenario, tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]] = {
    "historical": ((2.0, 12.0), (-10.0, -1.5), (35.0, 75.0), (3.0, 25.0)),
    "bull": ((4.0, 16.0), (-6.0, -1.0), (50.0, 85.0), (2.0, 15.0)),
    "bear": ((1.0, 6.0), (-16.0, -3.0), (20.0, 55.0), (10.0, 35.0)),
    "sideways": ((1.5, 5.0), (-5.0, -1.0), (35.0, 65.0), (2.0, 10.0)),
    "high_volatility": ((3.0, 20.0), (-20.0, -2.0), (30.0, 70.0), (12.0, 40.0)),
    "low_volatility": ((1.0, 4.0), (-3.5, -0.5), (40.0, 70.0), (1.0, 6.0)),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_strategies() -> list[Strategy]:
    now = _now_iso()
    seeds: list[tuple[str, str, str, AgentId, ResearchCategory]] = [
        ("strategy-momentum", "Momentum Breakout", "Follows short-term price momentum on high-volume symbols.", "echo", "stock"),
        ("strategy-value", "Value Fundamentals", "Targets symbols with strong fundamentals trading below fair value.", "nova", "company"),
        ("strategy-macro", "Macro Rotation", "Rotates exposure across indexes and sectors with the macro cycle.", "atlas", "index"),
        ("strategy-scan", "News Momentum", "Reacts to breaking headline sentiment on watchlist symbols.", "scout", "sector"),
    ]
    return [
        Strategy(id=sid, name=name, description=desc, createdBy=agent, focusCategory=cat, createdAt=now)
        for sid, name, desc, agent, cat in seeds
    ]


def queue_backtest_now(
    sessions: list[BacktestSession],
    strategies: list[Strategy],
    watchlist: list[WatchlistEntry],
    runner_pool: tuple[AgentId, ...],
    new_time: TimeState,
    *,
    strategy: Strategy | None = None,
    symbol: str | None = None,
    scenario: TestScenario = "historical",
    custom_return_bias_pct: float = 0.0,
    custom_volatility_bias: float = 1.0,
) -> list[BacktestSession] | None:
    """Queues one session unconditionally (no QUEUE_CHANCE_PER_TICK roll) —
    used both by the normal per-tick chance below and by the Agent Energy
    "extra_simulation" spend (app/routers/energy.py), which needs a real,
    immediate effect rather than a chance of one. Returns None if the lab
    is already at capacity or there's nothing to run yet, so callers (the
    energy spend endpoint especially) can tell the difference between "ran"
    and "nothing happened" instead of silently no-oping.

    v0.7 Feature 45 — `strategy`/`symbol`/`scenario` let the Research
    Sandbox's own CEO-triggered POST /api/sandbox/backtest queue a
    specific strategy against a specific Testing Environment instead of
    the random pick below (still the automatic per-tick behavior when
    these are omitted)."""
    active = [s for s in sessions if s.status in ("queued", "running")]
    if len(active) >= MAX_CONCURRENT_SESSIONS or not strategies or not watchlist:
        return None
    chosen_strategy = strategy or random.choice(strategies)
    chosen_symbol = symbol or random.choice(watchlist).symbol
    session = BacktestSession(
        # v0.7 Feature 45 — len(sessions) disambiguates two sessions
        # queued for the same strategy/scenario within the same sim-
        # minute (e.g. a CEO-triggered backtest landing the same minute
        # as the automatic per-tick roll) — without it they'd share an
        # id and collide as React keys in SandboxPanel.
        id=f"sim-{chosen_strategy.id}-{scenario}-{new_time.day}-{new_time.hour}-{new_time.minute}-{len(sessions)}",
        strategyId=chosen_strategy.id,
        strategyName=chosen_strategy.name,
        symbol=chosen_symbol,
        status="queued",
        progress=0.0,
        runBy=random.choice(runner_pool),
        queuedAt=_now_iso(),
        scenario=scenario,
        customReturnBiasPct=custom_return_bias_pct,
        customVolatilityBias=custom_volatility_bias,
    )
    return [*sessions, session]


def _maybe_queue_backtest(
    sessions: list[BacktestSession],
    strategies: list[Strategy],
    watchlist: list[WatchlistEntry],
    runner_pool: tuple[AgentId, ...],
    new_time: TimeState,
) -> list[BacktestSession]:
    if random.random() >= QUEUE_CHANCE_PER_TICK:
        return sessions
    return queue_backtest_now(sessions, strategies, watchlist, runner_pool, new_time) or sessions


def _run_strategy_step(sessions: list[BacktestSession]) -> list[BacktestSession]:
    """StrategyRunner: advances every queued session to running, and every
    running session's progress, by one tick."""
    updated: list[BacktestSession] = []
    for session in sessions:
        if session.status == "queued":
            updated.append(session.model_copy(update={"status": "running", "started_at": _now_iso()}))
        elif session.status == "running":
            progress = min(100.0, session.progress + random.uniform(*PROGRESS_GAIN_RANGE))
            updated.append(session.model_copy(update={"progress": progress}))
        else:
            updated.append(session)
    return updated


def _scenario_ranges(scenario: TestScenario, custom_return_bias_pct: float, custom_volatility_bias: float) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    if scenario != "custom":
        return _SCENARIO_RANGES[scenario]
    # "custom" scales the historical ranges by the CEO's own real chosen
    # numbers — a deterministic, traceable transform of real input, never
    # an independently fabricated range.
    win_low, win_high = _SCENARIO_RANGES["historical"][0]
    loss_low, loss_high = _SCENARIO_RANGES["historical"][1]
    rate_low, rate_high = _SCENARIO_RANGES["historical"][2]
    dd_low, dd_high = _SCENARIO_RANGES["historical"][3]
    bias = custom_return_bias_pct
    vol = max(custom_volatility_bias, 0.1)
    return (
        (max(0.1, win_low * vol + bias), max(0.2, win_high * vol + bias)),
        (loss_low * vol + bias, loss_high * vol + bias),
        (rate_low, rate_high),
        (max(0.5, dd_low * vol), max(1.0, dd_high * vol)),
    )


def _placeholder_backtest_metrics(scenario: TestScenario, custom_return_bias_pct: float, custom_volatility_bias: float) -> tuple[float, float, float, float, float, int, int, int, float, float]:
    """Explicitly placeholder — see this module's docstring. sharpe_ratio/
    sortino_ratio here are return-to-drawdown ratios, not real
    risk-adjusted-return statistics (those need a real daily-return
    series, which mock/placeholder data doesn't provide).

    v0.7 Feature 45 — win_count/loss_count/avg_win_pct/avg_loss_pct are
    now the real generating inputs; total_return_pct is derived FROM
    them (win_count * avg_win_pct + loss_count * avg_loss_pct), so every
    metric this function returns is internally consistent with every
    other one, never independently rolled. Returns (total_return_pct,
    win_rate, max_drawdown_pct, sharpe_ratio, sortino_ratio, trade_count,
    win_count, loss_count, avg_win_pct, avg_loss_pct)."""
    win_range, loss_range, rate_range, dd_range = _scenario_ranges(scenario, custom_return_bias_pct, custom_volatility_bias)

    trade_count = random.randint(8, 60)
    win_rate = random.uniform(*rate_range)
    win_count = round(trade_count * win_rate / 100.0)
    loss_count = trade_count - win_count
    avg_win_pct = random.uniform(*win_range)
    avg_loss_pct = random.uniform(*loss_range)

    total_return_pct = win_count * avg_win_pct + loss_count * avg_loss_pct
    max_drawdown_pct = random.uniform(*dd_range)
    sharpe_ratio = round(total_return_pct / max(max_drawdown_pct, 1.0), 2)
    sortino_ratio = round(sharpe_ratio * random.uniform(0.9, 1.3), 2)
    return total_return_pct, win_rate, max_drawdown_pct, sharpe_ratio, sortino_ratio, trade_count, win_count, loss_count, avg_win_pct, avg_loss_pct


def _collect_completed(sessions: list[BacktestSession], results: list[SimulationResult]) -> tuple[list[BacktestSession], list[SimulationResult], list[SimulationResult]]:
    still_active: list[BacktestSession] = []
    newly_completed: list[SimulationResult] = []
    for session in sessions:
        if session.status == "running" and session.progress >= 100.0:
            (
                total_return_pct,
                win_rate,
                max_drawdown_pct,
                sharpe,
                sortino,
                trade_count,
                win_count,
                loss_count,
                avg_win_pct,
                avg_loss_pct,
            ) = _placeholder_backtest_metrics(session.scenario, session.custom_return_bias_pct, session.custom_volatility_bias)

            gross_profit = win_count * avg_win_pct
            gross_loss = abs(loss_count * avg_loss_pct)
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else round(gross_profit, 2) if gross_profit > 0 else 0.0
            risk_reward_ratio = round(avg_win_pct / abs(avg_loss_pct), 2) if avg_loss_pct != 0 else 0.0
            expected_value_pct = round(total_return_pct / trade_count, 3) if trade_count > 0 else 0.0

            newly_completed.append(
                SimulationResult(
                    id=f"result-{session.id}",
                    strategyId=session.strategy_id,
                    strategyName=session.strategy_name,
                    symbol=session.symbol,
                    totalReturnPct=total_return_pct,
                    winRate=win_rate,
                    maxDrawdownPct=max_drawdown_pct,
                    sharpeRatio=sharpe,
                    sortinoRatio=sortino,
                    tradeCount=trade_count,
                    runBy=session.run_by,
                    completedAt=_now_iso(),
                    scenario=session.scenario,
                    winCount=win_count,
                    lossCount=loss_count,
                    avgWinPct=round(avg_win_pct, 2),
                    avgLossPct=round(avg_loss_pct, 2),
                    expectedValuePct=expected_value_pct,
                    profitFactor=profit_factor,
                    riskRewardRatio=risk_reward_ratio,
                    # CEO directive "TradeTown — Research Engine
                    # Hardening + Self-Improvement Implementation
                    # Pass," Phase 1 — explicit, honest, matches this
                    # module's own docstring: entirely placeholder math,
                    # no real price series behind it.
                    dataProvenance="synthetic",
                )
            )
        else:
            still_active.append(session)
    new_results = [*results, *newly_completed]
    if len(new_results) > MAX_SIMULATION_RESULTS:
        del new_results[: len(new_results) - MAX_SIMULATION_RESULTS]
    return still_active, new_results, newly_completed


def tick_simulation_lab(
    sessions: list[BacktestSession],
    results: list[SimulationResult],
    strategies: list[Strategy],
    watchlist: list[WatchlistEntry],
    runner_pool: tuple[AgentId, ...],
    new_time: TimeState,
) -> tuple[list[BacktestSession], list[SimulationResult], list[SimulationResult]]:
    """Returns (sessions, results, newly_completed) — newly_completed lets
    the caller (nexus.tick()) log/award only what finished *this* tick,
    the same shape app/research.py's tick_research() already uses."""
    sessions = _maybe_queue_backtest(sessions, strategies, watchlist, runner_pool, new_time)
    sessions = _run_strategy_step(sessions)
    sessions, results, newly_completed = _collect_completed(sessions, results)
    return sessions, results, newly_completed
