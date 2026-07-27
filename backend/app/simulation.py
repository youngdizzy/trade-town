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

from app.schemas import AgentId, BacktestSession, ResearchCategory, SimulationResult, Strategy, TimeState, WatchlistEntry

MAX_CONCURRENT_SESSIONS = 2
MAX_SIMULATION_RESULTS = 30
QUEUE_CHANCE_PER_TICK = 0.05
PROGRESS_GAIN_RANGE = (8.0, 18.0)


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
) -> list[BacktestSession] | None:
    """Queues one session unconditionally (no QUEUE_CHANCE_PER_TICK roll) —
    used both by the normal per-tick chance below and by the Agent Energy
    "extra_simulation" spend (app/routers/energy.py), which needs a real,
    immediate effect rather than a chance of one. Returns None if the lab
    is already at capacity or there's nothing to run yet, so callers (the
    energy spend endpoint especially) can tell the difference between "ran"
    and "nothing happened" instead of silently no-oping."""
    active = [s for s in sessions if s.status in ("queued", "running")]
    if len(active) >= MAX_CONCURRENT_SESSIONS or not strategies or not watchlist:
        return None
    strategy = random.choice(strategies)
    symbol = random.choice(watchlist).symbol
    session = BacktestSession(
        id=f"sim-{strategy.id}-{new_time.day}-{new_time.hour}-{new_time.minute}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        symbol=symbol,
        status="queued",
        progress=0.0,
        runBy=random.choice(runner_pool),
        queuedAt=_now_iso(),
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


def _placeholder_backtest_metrics() -> tuple[float, float, float, float, float, int]:
    """Explicitly placeholder — see this module's docstring. sharpe_ratio/
    sortino_ratio here are return-to-drawdown ratios, not real
    risk-adjusted-return statistics (those need a real daily-return
    series, which mock/placeholder data doesn't provide)."""
    total_return_pct = random.uniform(-15.0, 35.0)
    win_rate = random.uniform(35.0, 75.0)
    max_drawdown_pct = random.uniform(3.0, 25.0)
    sharpe_ratio = round(total_return_pct / max(max_drawdown_pct, 1.0), 2)
    sortino_ratio = round(sharpe_ratio * random.uniform(0.9, 1.3), 2)
    trade_count = random.randint(8, 60)
    return total_return_pct, win_rate, max_drawdown_pct, sharpe_ratio, sortino_ratio, trade_count


def _collect_completed(sessions: list[BacktestSession], results: list[SimulationResult]) -> tuple[list[BacktestSession], list[SimulationResult], list[SimulationResult]]:
    still_active: list[BacktestSession] = []
    newly_completed: list[SimulationResult] = []
    for session in sessions:
        if session.status == "running" and session.progress >= 100.0:
            total_return_pct, win_rate, max_drawdown_pct, sharpe, sortino, trade_count = _placeholder_backtest_metrics()
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
