"""Covers CEO directive "TradeTown — Autonomous Quant Operating System
Ultimate End-State 1.0" — Phase 0 of "connect champion_history to live
trading": `app/strategy_engine.py::detect_live_setup_at_latest_bar()`
(the real, live counterpart to `backtest_symbol_over_candles()`, reusing
the exact same setup-detection pipeline) and its SHADOW-ONLY wiring into
`app/nexus.py::tick()` (`ChampionLiveSignalCapture`). Every positive-case
fixture is cross-checked against the real backtest engine's own real
output — never a hand-built "setup," which would risk silently testing a
different rule than the one actually shipped.
"""
from __future__ import annotations

from app.champion_challenger import compare_champion_challenger, promote_challenger
from app.market_data import market_data_provider
from app.nexus import tick as nexus_tick
from app.schemas import TimeState
from app.state import default_state
from app.strategy_compiler import compile_strategy_text, strategy_definition_slug
from app.strategy_engine import backtest_symbol_over_candles, detect_live_setup_at_latest_bar

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_WEAK_TEXT = "Buy when the RSI is above 70. Enter when price closes above the previous swing high. Place a 5% stop. Target 2R."
_INVALID_TEXT = "Buy when the moon is full."


def _promote_real_champion(strategy_family_name: str):  # type: ignore[no-untyped-def]
    """Real, end-to-end: two real compiled strategies through the real
    compare_champion_challenger()/promote_challenger() pipeline —
    verdict force-set for determinism, same lightweight convention
    tests/test_champion_challenger.py's own TestPromoteChallenger
    already establishes. `strategy_family_name` intentionally equals the
    challenger's own real `.name` — the real production convention
    (see app/research_factory.py's own `get_current_champion(...,
    strategy_family=seed_definition.name)`), unlike some other tests'
    looser "Test Family" label."""
    champion_seed = compile_strategy_text(name=f"{strategy_family_name} Seed", source_text=_WEAK_TEXT)
    challenger_definition = compile_strategy_text(name=strategy_family_name, source_text=_EMA_TEXT)
    comparison = compare_champion_challenger(
        champion_seed, challenger_definition, strategy_family=strategy_family_name, hypothesis="h", proposed_by="quant",
        comparison_id=f"cmp-{strategy_family_name}", generated_at=_CREATED_AT, symbols=["AAPL"],
    )
    comparison = comparison.model_copy(update={"verdict": "challenger_recommended"})
    record = promote_challenger(comparison, promoted_by="quant", reasoning="test promotion", record_id=f"champion-{strategy_family_name}", promoted_at=_CREATED_AT)
    return record, challenger_definition


class TestDetectLiveSetupAtLatestBar:
    def test_a_never_compiled_definition_returns_none(self) -> None:
        bad_definition = compile_strategy_text(name="Live Signal Bad", source_text=_INVALID_TEXT)
        assert bad_definition.status != "compiled"
        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        assert detect_live_setup_at_latest_bar(bad_definition, "AAPL", candles) is None

    def test_too_few_candles_returns_none(self) -> None:
        definition = compile_strategy_text(name="Live Signal Short", source_text=_EMA_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        assert detect_live_setup_at_latest_bar(definition, "AAPL", candles[:10]) is None

    def test_never_mutates_the_input_candles(self) -> None:
        definition = compile_strategy_text(name="Live Signal Immutable", source_text=_EMA_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 300)
        before = list(candles)
        detect_live_setup_at_latest_bar(definition, "AAPL", candles)
        assert candles == before

    def test_reproduces_the_exact_same_real_setup_the_backtest_engine_finds(self) -> None:
        """The core honesty proof: slicing real candles up to and
        including a real backtest-discovered trade's own entry bar must
        make the live detector find THE SAME real setup — direction,
        entry price, stop, and target all matching — because it is
        calling the exact same underlying detection code, not a
        reimplementation."""
        definition = compile_strategy_text(name="Live Signal Cross-Check", source_text=_EMA_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 6000)
        trades = backtest_symbol_over_candles(definition, "AAPL", candles)
        assert trades, "sanity: the real strategy must find at least one real historical setup"
        trade = trades[0]
        entry_index = next(i for i, c in enumerate(candles) if c.timestamp == trade.entry_timestamp)
        assert entry_index >= 60  # sanity: enough real trailing history for indicators

        live_signal = detect_live_setup_at_latest_bar(definition, "AAPL", candles[: entry_index + 1])

        assert live_signal is not None
        assert live_signal.direction == trade.direction
        assert live_signal.entry_price == trade.entry_price
        assert live_signal.stop_price == trade.stop_price
        assert live_signal.target_price == trade.target_price
        assert live_signal.entry_timestamp == trade.entry_timestamp

    def test_is_bar_specific_not_a_stale_match(self) -> None:
        """One bar earlier, the same real setup's own entry has not
        happened yet — the live detector must not report it there."""
        definition = compile_strategy_text(name="Live Signal Bar Specific", source_text=_EMA_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 6000)
        trades = backtest_symbol_over_candles(definition, "AAPL", candles)
        assert trades
        trade = trades[0]
        entry_index = next(i for i, c in enumerate(candles) if c.timestamp == trade.entry_timestamp)
        assert entry_index >= 61

        one_bar_earlier = detect_live_setup_at_latest_bar(definition, "AAPL", candles[:entry_index])
        if one_bar_earlier is not None:
            assert one_bar_earlier.entry_timestamp != trade.entry_timestamp


class TestChampionLiveSignalCaptureWiring:
    """Real end-to-end wiring through app/nexus.py::tick() — a real
    promoted champion via the real champion_challenger pipeline, never a
    hand-built ChampionRecord."""

    def test_no_champion_history_produces_no_captures(self) -> None:
        state = default_state()
        assert state.champion_history == []
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert result.champion_live_signal_captures == []

    def test_a_champion_whose_definition_was_never_registered_is_skipped_gracefully(self) -> None:
        """Phase 0 finding: the factory's own registry only ever gains
        an entry for a MUTATED child, never the original seed/challenger
        — a champion promoted from a definition that was never
        separately registered has no resolvable CompiledStrategyDefinition
        object anywhere. The honest, correct behavior is to skip it, not
        crash or fabricate one."""
        record, _definition = _promote_real_champion("Unregistered Champion Family")
        state = default_state().model_copy(update={"champion_history": [record]})
        slug = strategy_definition_slug("Unregistered Champion Family")
        assert slug not in state.compiled_strategy_versions
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert result.champion_live_signal_captures == []

    def test_a_properly_registered_champion_does_not_crash_the_tick(self) -> None:
        record, definition = _promote_real_champion("Registered Champion Family")
        slug = strategy_definition_slug("Registered Champion Family")
        state = default_state().model_copy(
            update={"champion_history": [record], "compiled_strategy_versions": {slug: [definition]}}
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert isinstance(result.champion_live_signal_captures, list)

    def test_a_real_fresh_signal_produces_a_correctly_linked_capture(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Deterministic wiring test: forces detect_live_setup_at_latest_bar()
        to report a signal (real mock candle data may or may not have a
        fresh setup on any given tick — that randomness is not what this
        test is checking) and verifies the capture around it is real and
        correctly linked, never fabricated identity."""
        import app.nexus as nexus_module
        from app.schemas import LiveSetupSignal

        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-01-01T00:00:00+00:00", entryPrice=100.0, stopPrice=95.0, targetPrice=110.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        record, definition = _promote_real_champion("Forced Signal Family")
        slug = strategy_definition_slug("Forced Signal Family")
        state = default_state().model_copy(
            update={"champion_history": [record], "compiled_strategy_versions": {slug: [definition]}}
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

        captures = result.champion_live_signal_captures
        assert len(captures) == len(result.watchlist)  # one per watchlist symbol, since every symbol "fires" under the forced mock
        for capture in captures:
            assert capture.strategy_family == "Forced Signal Family"
            assert capture.champion_id == record.id
            assert capture.definition_id == definition.id
            assert capture.definition_version == definition.version
            assert capture.signal == forced_signal

    def test_captures_are_capped(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import app.nexus as nexus_module
        from app.schemas import ChampionLiveSignalCapture, LiveSetupSignal

        forced_signal = LiveSetupSignal(direction="long", entryTimestamp="2024-01-01T00:00:00+00:00", entryPrice=100.0, stopPrice=95.0, targetPrice=110.0)
        monkeypatch.setattr(nexus_module, "detect_live_setup_at_latest_bar", lambda definition, symbol, candles: forced_signal)

        record, definition = _promote_real_champion("Capped Family")
        slug = strategy_definition_slug("Capped Family")
        pre_existing = [
            ChampionLiveSignalCapture(
                id=f"pre-existing-{i}", strategyFamily="Capped Family", championId=record.id, definitionId=definition.id,
                definitionVersion=definition.version, symbol="AAPL", signal=forced_signal, capturedSimMinutes=0, createdAt=_CREATED_AT,
            )
            for i in range(nexus_module.MAX_CHAMPION_LIVE_SIGNAL_CAPTURES)
        ]
        state = default_state().model_copy(
            update={
                "champion_history": [record],
                "compiled_strategy_versions": {slug: [definition]},
                "champion_live_signal_captures": pre_existing,
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert len(result.champion_live_signal_captures) == nexus_module.MAX_CHAMPION_LIVE_SIGNAL_CAPTURES

    def test_a_second_promotion_for_the_same_family_updates_which_definition_is_evaluated(self) -> None:
        """get_current_champion() always resolves to the MOST RECENT real
        promotion for a family — this capture must follow that, never a
        stale earlier champion."""
        first_record, first_definition = _promote_real_champion("Superseded Family")
        second_definition = compile_strategy_text(name="Superseded Family", source_text=_EMA_TEXT, previous_version=1)
        second_comparison = compare_champion_challenger(
            first_definition, second_definition, strategy_family="Superseded Family", hypothesis="h", proposed_by="quant",
            comparison_id="cmp-superseded-2", generated_at=_CREATED_AT, symbols=["AAPL"],
        ).model_copy(update={"verdict": "challenger_recommended"})
        second_record = promote_challenger(second_comparison, promoted_by="quant", reasoning="second promotion", record_id="champion-superseded-2", promoted_at=_CREATED_AT)

        slug = strategy_definition_slug("Superseded Family")
        state = default_state().model_copy(
            update={
                "champion_history": [first_record, second_record],
                "compiled_strategy_versions": {slug: [first_definition, second_definition]},
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        for capture in result.champion_live_signal_captures:
            assert capture.definition_id == second_definition.id
            assert capture.definition_version == second_definition.version
