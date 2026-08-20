"""Covers app/strategy_tournament.py — CEO directive "Professional Quant
Firm Phase," Feature 40: the Quant Strategy Tournament. Assertions check
internal consistency and the real, disclosed round-by-round rule, never
a specific backtest outcome (this directive family's own house
convention — see tests/test_ema_pullback_research.py's
TestRunEmaPullbackResearchIntegration docstring).
"""
from __future__ import annotations

from app.schemas import CompiledStrategyBacktestResult, EmaPullbackStatsBucket, ResearchExperimentRecord, WalkForwardSymbolResult, WalkForwardValidationResult, WalkForwardWindowResult
from app.strategy_compiler import compile_strategy_text
from app.strategy_tournament import _assess_pair_correlations, _regime_stability, run_strategy_tournament

_VALID_TEXT_A = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_VALID_TEXT_B = "Buy when price closes above the 20 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 3R."
_INVALID_TEXT = "Buy when the moon is full."


def _bucket(expectancy: float | None) -> EmaPullbackStatsBucket:
    return EmaPullbackStatsBucket.model_construct(label="w", trade_count=0, win_count=0, loss_count=0, open_count=0, detail="x", expectancy_r=expectancy)  # type: ignore[call-arg]


def _regime_bucket(label: str, expectancy: float | None, *, verdict: str | None) -> EmaPullbackStatsBucket:
    return EmaPullbackStatsBucket.model_construct(label=label, trade_count=0, win_count=0, loss_count=0, open_count=0, detail="x", expectancy_r=expectancy, verdict=verdict)  # type: ignore[call-arg]


def _record_with_regime_buckets(trend: list[EmaPullbackStatsBucket], volatility: list[EmaPullbackStatsBucket]) -> ResearchExperimentRecord:
    backtest = CompiledStrategyBacktestResult.model_construct(regime_trend_breakdown=trend, regime_volatility_breakdown=volatility)  # type: ignore[call-arg]
    return ResearchExperimentRecord.model_construct(backtest=backtest)  # type: ignore[call-arg]


def _window(index: int, expectancy: float | None) -> WalkForwardWindowResult:
    return WalkForwardWindowResult.model_construct(window_index=index, start_timestamp="t", end_timestamp="t", bucket=_bucket(expectancy))  # type: ignore[call-arg]


def _symbol_result(symbol: str, expectancies: list[float | None]) -> WalkForwardSymbolResult:
    return WalkForwardSymbolResult.model_construct(  # type: ignore[call-arg]
        symbol=symbol, windows=[_window(i, e) for i, e in enumerate(expectancies)], positive_window_count=0, negative_window_count=0, evaluated_window_count=0, detail="x"
    )


def _record(definition_id: str, symbol: str, expectancies: list[float | None]) -> ResearchExperimentRecord:
    walk_forward = WalkForwardValidationResult.model_construct(  # type: ignore[call-arg]
        id="wf", definition_id=definition_id, definition_version=1, window_bars=500, symbols=[_symbol_result(symbol, expectancies)], verdict="stable", detail="x", data_honesty_note="x", generated_at="t"
    )
    return ResearchExperimentRecord.model_construct(definition_id=definition_id, walk_forward=walk_forward)  # type: ignore[call-arg]


class TestRunStrategyTournament:
    def test_every_candidate_gets_exactly_one_real_entry(self) -> None:
        a = compile_strategy_text(name="Strategy A", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL", "MSFT"], candles_per_symbol=6000)
        assert {e.definition_id for e in result.entries} == {a.id, b.id}

    def test_every_directive_round_is_present_in_order(self) -> None:
        a = compile_strategy_text(name="Strategy A2", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B2", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL"], candles_per_symbol=6000)
        assert [r.round_number for r in result.rounds] == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_round_7_portfolio_interaction_is_disclosed_as_partially_blocked(self) -> None:
        a = compile_strategy_text(name="Strategy A3", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B3", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL"], candles_per_symbol=6000)
        round_7 = next(r for r in result.rounds if r.round_number == 7)
        assert round_7.blocked is True
        assert "PARTIALLY BLOCKED" in round_7.description
        # A real portfolio-level backtest (shared capital, combined position sizing) is still unavailable,
        # but round 7 must never eliminate — correlation alone is not a real portfolio risk verdict.
        assert round_7.eliminated == []

    def test_pair_correlations_are_computed_for_every_shared_symbol_between_every_pair(self) -> None:
        a = compile_strategy_text(name="Strategy A3b", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B3b", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL", "MSFT"], candles_per_symbol=6000)
        assert len(result.pair_correlations) == 2  # one per shared symbol (AAPL, MSFT)
        for pair in result.pair_correlations:
            assert {pair.definition_id_a, pair.definition_id_b} == {a.id, b.id}
            assert pair.symbol in ("AAPL", "MSFT")
            # correlation is either a real, bounded coefficient or honestly None below the evidence bar —
            # never a fabricated placeholder like 0.0 standing in for "not enough data."
            if pair.correlation is not None:
                assert -1.0 <= pair.correlation <= 1.0
            else:
                assert pair.windows_compared < 3

    def test_a_single_candidate_has_no_pairs_to_correlate(self) -> None:
        # run_strategy_tournament requires >= 2 candidates at the router layer, but the pure function
        # itself should still handle a 1-candidate list honestly (no pairs, never a crash).
        from app.research_experiment import run_research_experiment
        from app.strategy_tournament import _assess_pair_correlations

        a = compile_strategy_text(name="Strategy Solo", source_text=_VALID_TEXT_A)
        record = run_research_experiment(a, symbols=["AAPL"], candles_per_symbol=6000)
        assert _assess_pair_correlations([record]) == []

    def test_a_definition_with_zero_real_trades_is_eliminated_in_round_1(self) -> None:
        invalid = compile_strategy_text(name="Moon Strategy T", source_text=_INVALID_TEXT)
        valid = compile_strategy_text(name="Strategy Valid T", source_text=_VALID_TEXT_A)
        result = run_strategy_tournament([invalid, valid], symbols=["AAPL"], candles_per_symbol=6000)
        round_1 = next(r for r in result.rounds if r.round_number == 1)
        assert invalid.id in round_1.eliminated
        entry = next(e for e in result.entries if e.definition_id == invalid.id)
        assert entry.eliminated_at_round == 1
        assert entry.elimination_reason is not None

    def test_a_definition_never_eliminated_survives_to_production_candidates_only_if_overfitting_reads_robust(self) -> None:
        a = compile_strategy_text(name="Strategy A4", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B4", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL", "MSFT", "SPY"], candles_per_symbol=6000)
        for definition_id in result.production_candidates:
            entry = next(e for e in result.entries if e.definition_id == definition_id)
            assert entry.overfitting_verdict == "robust"
            assert entry.eliminated_at_round is None

    def test_superlatives_only_cite_real_strategies_that_are_actually_in_the_entry_list(self) -> None:
        a = compile_strategy_text(name="Strategy A5", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B5", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL"], candles_per_symbol=6000)
        entry_ids = {e.definition_id for e in result.entries}
        for slot in (result.highest_expectancy, result.highest_profit_factor, result.highest_sharpe_ratio, result.lowest_max_drawdown, result.most_walk_forward_stable):
            if slot is not None:
                assert slot.strategy_id in entry_ids

    def test_a_superlative_with_no_real_value_anywhere_reads_none_never_a_fabricated_default(self) -> None:
        # Two definitions with zero real closed trades never have a real Sharpe ratio anywhere.
        invalid_a = compile_strategy_text(name="Moon A", source_text=_INVALID_TEXT)
        invalid_b = compile_strategy_text(name="Moon B", source_text="Sell when the stars align.")
        result = run_strategy_tournament([invalid_a, invalid_b], symbols=["AAPL"], candles_per_symbol=6000)
        assert result.highest_sharpe_ratio is None

    def test_data_honesty_note_is_always_present_and_non_empty(self) -> None:
        a = compile_strategy_text(name="Strategy A6", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B6", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL"], candles_per_symbol=6000)
        assert result.data_honesty_note
        assert "never an autonomous production promotion" in result.data_honesty_note


class TestRegimeStability:
    """Feature 43 — Regime-Adaptive Strategy Selection. Hand-traced
    fixtures over `EmaPullbackStatsBucket`'s own real `verdict`/
    `expectancy_r` fields, never a live backtest run (the round-level
    integration is covered by TestRunStrategyTournament above)."""

    def test_no_bucket_reaching_enough_evidence_reads_insufficient_data(self) -> None:
        record = _record_with_regime_buckets(
            trend=[_regime_bucket("trending_up", 0.4, verdict="not_enough_evidence")],
            volatility=[_regime_bucket("high", -0.1, verdict="not_enough_evidence")],
        )
        verdict, detail = _regime_stability(record)
        assert verdict == "insufficient_data"
        assert "missing evidence" in detail.lower()

    def test_one_real_positive_evidenced_bucket_reads_regime_validated(self) -> None:
        record = _record_with_regime_buckets(
            trend=[_regime_bucket("trending_up", 0.6, verdict="enough_evidence"), _regime_bucket("ranging", -0.2, verdict="not_enough_evidence")],
            volatility=[],
        )
        verdict, detail = _regime_stability(record)
        assert verdict == "regime_validated"
        assert "trending_up" in detail

    def test_every_evidenced_bucket_non_positive_reads_no_validated_regime(self) -> None:
        record = _record_with_regime_buckets(
            trend=[_regime_bucket("trending_up", -0.3, verdict="enough_evidence")],
            volatility=[_regime_bucket("normal", 0.0, verdict="enough_evidence")],
        )
        verdict, detail = _regime_stability(record)
        assert verdict == "no_validated_regime"
        assert "trending_up" in detail and "normal" in detail

    def test_a_negative_evidenced_bucket_never_masks_a_separate_positive_evidenced_bucket(self) -> None:
        record = _record_with_regime_buckets(
            trend=[_regime_bucket("trending_down", -0.5, verdict="enough_evidence")],
            volatility=[_regime_bucket("low", 0.3, verdict="enough_evidence")],
        )
        verdict, _ = _regime_stability(record)
        assert verdict == "regime_validated"


class TestAssessPairCorrelations:
    """Hand-traced fixtures — real Pearson correlation over a fixed,
    known expectancy sequence, reusing app/portfolio_intelligence.py's
    own already-tested pearson_correlation()."""

    def test_perfectly_correlated_windows_read_a_real_1_0(self) -> None:
        record_a = _record("def-a", "AAPL", [1.0, 2.0, 3.0, 4.0])
        record_b = _record("def-b", "AAPL", [2.0, 4.0, 6.0, 8.0])
        pairs = _assess_pair_correlations([record_a, record_b])
        assert len(pairs) == 1
        assert pairs[0].correlation == 1.0
        assert pairs[0].windows_compared == 4

    def test_perfectly_anti_correlated_windows_read_a_real_negative_1_0(self) -> None:
        record_a = _record("def-a", "AAPL", [1.0, 2.0, 3.0, 4.0])
        record_b = _record("def-b", "AAPL", [8.0, 6.0, 4.0, 2.0])
        pairs = _assess_pair_correlations([record_a, record_b])
        assert pairs[0].correlation == -1.0

    def test_below_the_minimum_paired_windows_reads_none_never_a_fabricated_zero(self) -> None:
        record_a = _record("def-a", "AAPL", [1.0, 2.0])
        record_b = _record("def-b", "AAPL", [2.0, 4.0])
        pairs = _assess_pair_correlations([record_a, record_b])
        assert pairs[0].correlation is None
        assert pairs[0].windows_compared == 2

    def test_windows_with_no_real_evidence_on_either_side_are_excluded_from_the_pairing(self) -> None:
        # None entries (a window without enough real trades for a bucket verdict) must never be
        # treated as 0.0 — they are simply excluded from the paired comparison.
        record_a = _record("def-a", "AAPL", [1.0, None, 3.0, 4.0])
        record_b = _record("def-b", "AAPL", [2.0, 4.0, None, 8.0])
        pairs = _assess_pair_correlations([record_a, record_b])
        # Only window indices 0 and 3 have real evidence on both sides.
        assert pairs[0].windows_compared == 2
        assert pairs[0].correlation is None  # still below the 3-window bar

    def test_no_shared_symbol_produces_no_pair_entry(self) -> None:
        record_a = _record("def-a", "AAPL", [1.0, 2.0, 3.0])
        record_b = _record("def-b", "MSFT", [2.0, 4.0, 6.0])
        assert _assess_pair_correlations([record_a, record_b]) == []

    def test_every_pair_always_cites_the_two_real_definition_ids(self) -> None:
        record_a = _record("def-a", "AAPL", [1.0, 2.0, 3.0])
        record_b = _record("def-b", "AAPL", [2.0, 4.0, 6.0])
        pairs = _assess_pair_correlations([record_a, record_b])
        assert {pairs[0].definition_id_a, pairs[0].definition_id_b} == {"def-a", "def-b"}
