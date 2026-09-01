"""Covers app/state.py::GameState.submit_research_factory_run() — CEO
directive "TradeTown — Phase 9: Full Autonomous Quant Research Factory,"
Phase 5. Confirms the live entry point applies this codebase's own
real, richer defaults (MAX_CHILDREN_PER_PARENT/MAX_RUNTIME_SECONDS) for
a NEW run when the caller doesn't override them, while the underlying
pure `run_research_factory_cycle()` itself still defaults conservatively
(see tests/test_research_factory.py's own 49 backward-compatibility
tests) — the two defaults are deliberately different, by design.
"""
from __future__ import annotations

import asyncio

from app.research_factory import MAX_CHILDREN_PER_PARENT, MAX_RUNTIME_SECONDS
from app.schemas import StrategyHypothesis
from app.state import GameState
from app.strategy_compiler import compile_strategy_text

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."


def _hypothesis() -> StrategyHypothesis:
    return StrategyHypothesis(
        id="hyp-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )


def test_default_live_run_uses_the_richer_module_defaults() -> None:
    async def _run() -> None:
        state = GameState()
        definition = compile_strategy_text(name="State Factory Default Strategy", source_text=_EMA_TEXT)
        _updated, run = await state.submit_research_factory_run(_hypothesis(), definition, symbols=["AAPL"], max_generations=1)
        assert run.config.max_children_per_parent == MAX_CHILDREN_PER_PARENT
        assert run.config.max_runtime_seconds == MAX_RUNTIME_SECONDS

    asyncio.run(_run())


def test_explicit_override_is_respected() -> None:
    async def _run() -> None:
        state = GameState()
        definition = compile_strategy_text(name="State Factory Override Strategy", source_text=_EMA_TEXT)
        _updated, run = await state.submit_research_factory_run(
            _hypothesis(), definition, symbols=["AAPL"], max_generations=1, max_children_per_parent=1, max_runtime_seconds=0
        )
        assert run.config.max_children_per_parent == 1
        assert run.config.max_runtime_seconds == 0

    asyncio.run(_run())


def test_run_is_persisted_into_factory_runs() -> None:
    async def _run() -> None:
        state = GameState()
        definition = compile_strategy_text(name="State Factory Persistence Strategy", source_text=_EMA_TEXT)
        updated, run = await state.submit_research_factory_run(_hypothesis(), definition, symbols=["AAPL"], max_generations=1)
        assert run.id in [r.id for r in updated.factory_runs]
        assert run.id in [r.id for r in state.data.factory_runs]

    asyncio.run(_run())
