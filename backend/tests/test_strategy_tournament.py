"""Covers app/strategy_tournament.py — CEO directive "Professional Quant
Firm Phase," Feature 40: the Quant Strategy Tournament. Assertions check
internal consistency and the real, disclosed round-by-round rule, never
a specific backtest outcome (this directive family's own house
convention — see tests/test_ema_pullback_research.py's
TestRunEmaPullbackResearchIntegration docstring).
"""
from __future__ import annotations

from app.strategy_compiler import compile_strategy_text
from app.strategy_tournament import run_strategy_tournament

_VALID_TEXT_A = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_VALID_TEXT_B = "Buy when price closes above the 20 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 3R."
_INVALID_TEXT = "Buy when the moon is full."


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
        assert [r.round_number for r in result.rounds] == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_round_7_portfolio_interaction_is_disclosed_as_architecturally_blocked(self) -> None:
        a = compile_strategy_text(name="Strategy A3", source_text=_VALID_TEXT_A)
        b = compile_strategy_text(name="Strategy B3", source_text=_VALID_TEXT_B)
        result = run_strategy_tournament([a, b], symbols=["AAPL"], candles_per_symbol=6000)
        round_7 = next(r for r in result.rounds if r.round_number == 7)
        assert round_7.blocked is True
        assert "ARCHITECTURALLY BLOCKED" in round_7.description

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
