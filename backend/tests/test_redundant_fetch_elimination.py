"""Covers CEO directive "Phase 9 / Real Market Data + Evidence Integrity
Foundation," Section 10 — proving `run_adversarial_research()` reuses a
caller's already-fetched trades instead of independently re-fetching
candles and re-backtesting, and that `run_compiled_strategy_backtest()`
exposes its own real per-trade sequence for exactly that reuse."""
from __future__ import annotations

import app.adversarial_research as adversarial_research_module
from app.adversarial_research import run_adversarial_research
from app.research_experiment import run_research_experiment
from app.schemas import ParameterSensitivityResult
from app.strategy_compiler import compile_strategy_text
from app.strategy_engine import run_compiled_strategy_backtest

_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."


def _definition():
    return compile_strategy_text(name="Redundant Fetch Test", source_text=_TEXT)


class TestBacktestExposesRealTrades:
    def test_trades_field_matches_real_internal_trade_count(self) -> None:
        definition = _definition()
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        assert result.overall.trade_count == len(result.trades)

    def test_refusal_path_has_empty_trades_not_a_crash(self) -> None:
        definition = _definition()
        broken = definition.model_copy(update={"status": "invalid"})
        result = run_compiled_strategy_backtest(broken, symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        assert result.trades == []


class TestAdversarialResearchReusesTrades:
    def _parameter_sensitivity(self) -> ParameterSensitivityResult:
        return ParameterSensitivityResult(
            id="ps-1", definitionId="x", definitionVersion=1, verdict="insufficient_data",
            detail="x", multipleTestingNote="x", dataHonestyNote="x", generatedAt="2024-01-01T00:00:00+00:00",
        )

    def test_passing_closed_trades_skips_the_internal_candle_fetch(self, monkeypatch) -> None:
        definition = _definition()
        backtest = run_compiled_strategy_backtest(definition, symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)

        call_count = {"n": 0}
        original_get_candles = adversarial_research_module.market_data_provider.get_candles

        def _counting_get_candles(*args: object, **kwargs: object):
            call_count["n"] += 1
            return original_get_candles(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(adversarial_research_module.market_data_provider, "get_candles", _counting_get_candles)

        run_adversarial_research(
            definition,
            regime_trend_breakdown=[],
            regime_volatility_breakdown=[],
            parameter_sensitivity=self._parameter_sensitivity(),
            risk_per_trade_pct=1.0,
            result_id="test-adversarial",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
            timeframe="1h",
            candles_per_symbol=500,
            closed_trades=backtest.trades,
        )
        assert call_count["n"] == 0, "run_adversarial_research() re-fetched candles despite being given closed_trades directly"

    def test_omitting_closed_trades_still_fetches_standalone(self, monkeypatch) -> None:
        definition = _definition()
        call_count = {"n": 0}
        original_get_candles = adversarial_research_module.market_data_provider.get_candles

        def _counting_get_candles(*args: object, **kwargs: object):
            call_count["n"] += 1
            return original_get_candles(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(adversarial_research_module.market_data_provider, "get_candles", _counting_get_candles)

        run_adversarial_research(
            definition,
            regime_trend_breakdown=[],
            regime_volatility_breakdown=[],
            parameter_sensitivity=self._parameter_sensitivity(),
            risk_per_trade_pct=1.0,
            result_id="test-adversarial-2",
            generated_at="2024-01-01T00:00:00+00:00",
            symbols=["AAPL"],
            timeframe="1h",
            candles_per_symbol=500,
        )
        assert call_count["n"] == 1, "standalone (no closed_trades) call should still fetch exactly once per symbol"


class TestResearchExperimentDatasetMetadata:
    def test_experiment_record_carries_real_dataset_and_feature_metadata(self) -> None:
        definition = _definition()
        record = run_research_experiment(definition, symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        assert record.dataset_metadata is not None
        assert record.dataset_metadata.data_category == "simulated"
        assert record.dataset_metadata.symbols == ["AAPL"]
        assert record.point_in_time_verified == (record.look_ahead_audit.verdict == "clean")
        assert isinstance(record.feature_versions, list)
