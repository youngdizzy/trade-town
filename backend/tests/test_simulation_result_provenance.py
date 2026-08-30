"""Covers the `SimulationResult.dataProvenance` field — CEO directive
"TradeTown — Research Engine Hardening + Self-Improvement Implementation
Pass," Phase 1. Proves the real, honest per-item labeling: the RNG-only
Sandbox engine always stamps `synthetic`, the two real price-series-driven
engines always stamp `simulated` — never a fabricated `real`, which no
producer in this codebase can honestly claim (see app/market_data.py).

The two real, price-series-driven producers
(app/strategy_engine.py::run_compiled_strategy_backtest(),
app/ema_pullback_research.py::run_ema_pullback_research()) build their own
real `SimulationResult` list as a purely LOCAL variable — feeding only
their own internal Monte Carlo/Model Validation calls — and never return
it as part of their own public result object (a real, separate,
pre-existing architectural fact this pass's own forensic audit found, not
introduced by it). Their own provenance stamp is therefore verified by
source inspection here rather than through the public return value, which
genuinely cannot see it.
"""
from __future__ import annotations

import inspect

from app.ema_pullback_research import run_ema_pullback_research
from app.schemas import DataCategory, SimulationResult
from app.simulation import queue_backtest_now, tick_simulation_lab
from app.state import GameState
from app.strategy_engine import run_compiled_strategy_backtest


class TestSimulationResultProvenanceDefault:
    def test_the_schema_default_is_the_honest_synthetic_value(self) -> None:
        assert SimulationResult.model_fields["data_provenance"].default == "synthetic"

    def test_data_provenance_accepts_every_real_data_category_value(self) -> None:
        from typing import get_args

        allowed = set(get_args(DataCategory))
        assert {"synthetic", "simulated"} <= allowed


class TestSandboxEngineProvenance:
    def test_a_completed_sandbox_backtest_is_stamped_synthetic(self) -> None:
        state = GameState()
        strategies = state.data.strategies
        watchlist = state.data.watchlist
        sessions = queue_backtest_now([], strategies, watchlist, ("quant",), state.data.time, strategy=strategies[0], symbol=watchlist[0].symbol) or []
        results: list = []
        for _ in range(20):
            sessions, results, newly_completed = tick_simulation_lab(sessions, results, strategies, watchlist, ("quant",), state.data.time)
            if newly_completed:
                assert newly_completed[0].data_provenance == "synthetic"
                return
        raise AssertionError("session never completed within 20 ticks")


class TestResearchDeskEngineProvenance:
    """The real per-symbol SimulationResult these two real engines build
    is a local variable, never returned (see this module's own
    docstring) — verified by source inspection, a legitimate technique
    this codebase's own test suite already uses elsewhere (e.g.
    test_champion_challenger.py's `inspect.getsource()` check that
    `_decide_verdict()` never reads `classification`)."""

    def test_the_compiled_strategy_backtest_engine_stamps_simulated_not_synthetic(self) -> None:
        source = inspect.getsource(run_compiled_strategy_backtest)
        assert 'dataProvenance="simulated"' in source
        assert 'dataProvenance="synthetic"' not in source

    def test_the_ema_pullback_research_engine_stamps_simulated_not_synthetic(self) -> None:
        source = inspect.getsource(run_ema_pullback_research)
        assert 'dataProvenance="simulated"' in source
        assert 'dataProvenance="synthetic"' not in source

    def test_both_real_engines_still_run_cleanly_with_the_new_field_present(self) -> None:
        """Not a provenance assertion (the field is local-only on this
        path — see above) — proves the new field didn't break either
        real engine's own normal operation."""
        from app.strategy_compiler import compile_strategy_text

        definition = compile_strategy_text(
            name="Provenance Smoke Test Strategy",
            source_text="Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.",
        )
        backtest = run_compiled_strategy_backtest(definition, symbols=["AAPL"])
        assert backtest is not None
        report = run_ema_pullback_research(symbols=["AAPL"])
        assert report is not None
