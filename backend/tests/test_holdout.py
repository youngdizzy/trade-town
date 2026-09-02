"""Covers app/holdout.py — CEO directive "TradeTown — Phase 10: Real
Data + True Holdout + Portfolio Intelligence," Section B/K. Pure-function
unit tests hand-build real `Candle` fixtures for exact control over the
adversarial cases (overlap, out-of-order, mutation-after-freeze);
integration tests run the real pipeline (`market_data_provider.get_candles()`
-> partition -> freeze -> validate -> evaluate) end to end.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

from app.holdout import (
    DEFAULT_TRAIN_FRACTION,
    DEFAULT_VALIDATION_FRACTION,
    freeze_strategy,
    partition_candles_chronologically,
    run_holdout_evaluation,
    validate_holdout,
)
from app.market_data import Candle, market_data_provider
from app.strategy_compiler import compile_strategy_text

_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_REPORT_ID = "holdout-report-1"


def _candle(ts: str, symbol: str = "AAPL", timeframe: str = "1h", close: float = 100.0) -> Candle:
    return Candle(symbol=symbol, timeframe=timeframe, timestamp=ts, open=close, high=close + 1, low=close - 1, close=close, volume=1000.0, data_status="simulated")


def _series(n: int, start_hour: int = 0) -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [_candle((base + timedelta(hours=start_hour + i)).isoformat(), close=100.0 + i) for i in range(n)]


def _definition():
    return compile_strategy_text(name="Holdout Test Strategy", source_text=_TEXT)


class TestPartitionCandlesChronologically:
    def test_splits_by_index_never_shuffles(self) -> None:
        candles = _series(100)
        train, validation, holdout = partition_candles_chronologically(candles)
        assert train == candles[:60]
        assert validation == candles[60:80]
        assert holdout == candles[80:]

    def test_partitions_are_non_overlapping_and_exhaustive(self) -> None:
        candles = _series(1000)
        train, validation, holdout = partition_candles_chronologically(candles)
        assert train + validation + holdout == candles
        assert len(set(id(c) for c in train) & set(id(c) for c in validation)) == 0
        assert len(set(id(c) for c in validation) & set(id(c) for c in holdout)) == 0

    def test_holdout_is_the_chronologically_latest_slice(self) -> None:
        candles = _series(100)
        _train, _validation, holdout = partition_candles_chronologically(candles)
        assert holdout[0].timestamp == candles[80].timestamp
        assert holdout[-1].timestamp == candles[-1].timestamp

    def test_custom_fractions_respected(self) -> None:
        candles = _series(100)
        train, validation, holdout = partition_candles_chronologically(candles, train_fraction=0.5, validation_fraction=0.3)
        assert len(train) == 50
        assert len(validation) == 30
        assert len(holdout) == 20

    def test_default_fractions_sum_to_less_than_one_leaving_a_real_holdout(self) -> None:
        assert DEFAULT_TRAIN_FRACTION + DEFAULT_VALIDATION_FRACTION < 1.0


class TestFreezeStrategy:
    def test_freeze_names_the_exact_definition(self) -> None:
        definition = _definition()
        freeze = freeze_strategy(definition, dataset_version="ds-v1", feature_versions=["ema-v1"])
        assert freeze.definition_id == definition.id
        assert freeze.definition_version == definition.version
        assert freeze.dataset_version == "ds-v1"
        assert freeze.feature_versions == ["ema-v1"]


class TestValidateHoldoutAdversarial:
    """Section K.1-K.4/K.13-K.16 — the real adversarial cases."""

    def test_empty_partition_is_unavailable_never_valid(self) -> None:
        definition = _definition()
        report = validate_holdout(
            definition, train=_series(300), validation=[], holdout=_series(300, 600), dataset_id="d", dataset_version="v", freeze=None, report_id=_REPORT_ID
        )
        assert report.status == "unavailable"

    def test_no_freeze_is_invalid(self) -> None:
        definition = _definition()
        train, validation, holdout = partition_candles_chronologically(_series(1000))
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=None, report_id=_REPORT_ID)
        assert report.status == "invalid"
        assert "not been frozen" in report.detail

    def test_freeze_naming_a_different_definition_version_is_invalid(self) -> None:
        """Section K.16 — strategy mutation after freeze invalidates holdout."""
        definition = _definition()
        train, validation, holdout = partition_candles_chronologically(_series(1000))
        stale_freeze = freeze_strategy(definition, dataset_version="d", feature_versions=[])
        mutated = definition.model_copy(update={"version": definition.version + 1})
        report = validate_holdout(mutated, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=stale_freeze, report_id=_REPORT_ID)
        assert report.status == "invalid"
        assert "mutated after freeze" in report.detail

    def test_overlapping_timestamps_across_partitions_is_invalid(self) -> None:
        """Section K.1/K.2 — overlapping/duplicate dates -> invalid."""
        definition = _definition()
        candles = _series(300)
        freeze = freeze_strategy(definition, dataset_version="d", feature_versions=[])
        # Deliberately corrupt: holdout starts BEFORE validation ends (a real overlap).
        train = candles[:100]
        validation = candles[100:200]
        holdout = candles[150:300]  # overlaps validation[150:200]
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=freeze, report_id=_REPORT_ID)
        assert report.status == "invalid"
        assert report.overlap_detected is True

    def test_duplicate_candle_across_partitions_is_invalid(self) -> None:
        definition = _definition()
        candles = _series(300)
        freeze = freeze_strategy(definition, dataset_version="d", feature_versions=[])
        train = candles[:100]
        validation = candles[100:200]
        holdout = [candles[199], *candles[200:300]]  # last validation candle duplicated into holdout
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=freeze, report_id=_REPORT_ID)
        assert report.status == "invalid"
        assert report.leakage_detected is True

    def test_correct_chronological_partition_with_freeze_is_valid(self) -> None:
        definition = _definition()
        train, validation, holdout = partition_candles_chronologically(_series(1000))
        freeze = freeze_strategy(definition, dataset_version="d", feature_versions=["ema-v1"])
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=freeze, report_id=_REPORT_ID)
        assert report.status == "valid"
        assert report.overlap_detected is False
        assert report.leakage_detected is False
        assert report.chronological_order_valid is True

    def test_partition_summaries_carry_real_content_hashes(self) -> None:
        definition = _definition()
        train, validation, holdout = partition_candles_chronologically(_series(1000))
        freeze = freeze_strategy(definition, dataset_version="d", feature_versions=[])
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=freeze, report_id=_REPORT_ID)
        assert report.train.content_hash != report.holdout.content_hash
        assert report.holdout.candle_count == len(holdout)


class TestRunHoldoutEvaluation:
    def test_invalid_report_never_produces_a_bucket(self) -> None:
        definition = _definition()
        train, validation, holdout = partition_candles_chronologically(_series(300))  # too few for a real freeze anyway
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=None, report_id=_REPORT_ID)
        assert report.status != "valid"
        result = run_holdout_evaluation(definition, "AAPL", report=report, holdout_candles=holdout, result_id="eval-1")
        assert result.bucket is None

    def test_valid_report_runs_a_real_isolated_backtest(self) -> None:
        definition = _definition()
        candles = market_data_provider.get_candles("AAPL", "1h", 3000)
        train, validation, holdout = partition_candles_chronologically(candles)
        freeze = freeze_strategy(definition, dataset_version="d", feature_versions=["ema-v1"])
        report = validate_holdout(definition, train=train, validation=validation, holdout=holdout, dataset_id="d", dataset_version="v", freeze=freeze, report_id=_REPORT_ID)
        assert report.status == "valid"
        result = run_holdout_evaluation(definition, "AAPL", report=report, holdout_candles=holdout, result_id="eval-2")
        assert result.bucket is not None
        assert result.bucket.label == "holdout"


class TestNeverWiredIntoMutation:
    """Section K — proven by real module-source inspection, matching
    this codebase's own established Champion/Challenger-boundary
    discipline: never a bare textual assertion, always import-shape."""

    def test_research_factory_never_imports_holdout(self) -> None:
        import app.research_factory as research_factory_module

        source = inspect.getsource(research_factory_module)
        assert "app.holdout" not in source
        assert "import holdout" not in source

    def test_research_loop_never_imports_holdout(self) -> None:
        import app.research_loop as research_loop_module

        source = inspect.getsource(research_loop_module)
        assert "app.holdout" not in source
        assert "import holdout" not in source

    def test_research_pareto_never_imports_holdout(self) -> None:
        """CEO directive "TradeTown — Autonomous Mutation Application +
        Pareto Survivor Engine" — the new Pareto dominance engine reads
        `StrategyScorecard.statistical_evidence_state` as one axis (a
        pre-existing string value from app/evidence_quality.py's own
        `EvidenceState` vocabulary), never anything from app/holdout.py
        itself. Same real, disclosed guarantee, same proof method."""
        import app.research_pareto as research_pareto_module

        source = inspect.getsource(research_pareto_module)
        assert "app.holdout" not in source
        assert "import holdout" not in source
