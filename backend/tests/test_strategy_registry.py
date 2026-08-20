"""Covers app/strategy_registry.py — CEO directive "Professional Quant
Firm Phase," Feature 37: real, persisted CompiledStrategyDefinition
version history. Also covers this module's later
register_researchable_strategy() — CEO directive "Strategy Intelligence
+ Live Strategy Attribution": the real Strategy Lab <->
CompiledStrategyDefinition identity bridge.
"""
from __future__ import annotations

import asyncio

from app.state import GameState
from app.strategy_registry import register_researchable_strategy, register_strategy_version

_TEXT_V1 = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high."
_TEXT_V2 = "Buy when price closes above the 20 EMA, then enter when price closes above the previous swing high."

# A real, fully-specified 50 EMA breakout/pullback long setup — every
# clause chosen to match app/strategy_compiler.py's own disclosed
# vocabulary exactly (verified to reach status == "compiled", not just
# "invalid"/"ambiguous" — see TestRegisterResearchableStrategy below).
EMA_50_PULLBACK_LONG_TEXT = (
    "This strategy waits for price to stay below the 50 EMA, then closes above the 50 EMA on a confirmed candle. "
    "It then requires at least two bearish candles as the pullback. "
    "Entry triggers when price closes above the previous swing high established before the pullback. "
    "Use a chandelier stop with a 22-period ATR and a 3.0x multiplier. "
    "Target 2R."
)
# The symmetric short inverse.
EMA_50_PULLBACK_SHORT_TEXT = (
    "This strategy waits for price to stay above the 50 EMA, then closes below the 50 EMA on a confirmed candle. "
    "It then requires at least two bullish candles as the pullback. "
    "Entry triggers when price closes below the previous swing low established before the pullback. "
    "Use a chandelier stop with a 22-period ATR and a 3.0x multiplier. "
    "Target 2R."
)
# Deliberately missing a target — real, incomplete text, same class this
# compiler already refuses to silently guess at (see compile_strategy_text()).
_INCOMPLETE_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high."


class TestRegisterStrategyVersion:
    def test_the_first_registration_reads_version_1_regardless_of_caller_input(self) -> None:
        definition, registry = register_strategy_version({}, name="EMA Breakout", source_text=_TEXT_V1)
        assert definition.version == 1
        assert registry[definition.id] == [definition]

    def test_a_second_registration_for_the_same_name_reads_the_real_next_version(self) -> None:
        v1, registry = register_strategy_version({}, name="EMA Breakout", source_text=_TEXT_V1)
        v2, registry = register_strategy_version(registry, name="EMA Breakout", source_text=_TEXT_V2)
        assert v2.version == 2
        assert registry[v1.id] == [v1, v2]

    def test_prior_versions_are_never_overwritten(self) -> None:
        v1, registry = register_strategy_version({}, name="EMA Breakout", source_text=_TEXT_V1)
        v2, registry = register_strategy_version(registry, name="EMA Breakout", source_text=_TEXT_V2)
        assert registry[v1.id][0] is v1
        assert registry[v1.id][0].source_text == _TEXT_V1

    def test_other_strategies_in_the_registry_are_left_untouched(self) -> None:
        other, registry = register_strategy_version({}, name="Other Strategy", source_text=_TEXT_V1)
        _, registry = register_strategy_version(registry, name="EMA Breakout", source_text=_TEXT_V1)
        assert registry[other.id] == [other]

    def test_the_real_next_version_ignores_any_caller_supplied_previous_version_on_the_definition_itself(self) -> None:
        # register_strategy_version() never reads previous_version from the caller — only this
        # registry's own real, persisted length. Registering the same name twice in a row
        # (simulating two independent callers with no coordination) must still read 1, then 2.
        v1, registry = register_strategy_version({}, name="Race Test", source_text=_TEXT_V1)
        v2, registry = register_strategy_version(registry, name="Race Test", source_text=_TEXT_V1)
        assert (v1.version, v2.version) == (1, 2)


class TestRegisterCompiledStrategyVersionState:
    def test_state_persists_the_real_version_history_across_calls(self) -> None:
        state = GameState()
        saved, v1 = asyncio.run(state.register_compiled_strategy_version(name="EMA Breakout", source_text=_TEXT_V1))
        assert v1.version == 1
        assert saved.compiled_strategy_versions[v1.id] == [v1]
        saved, v2 = asyncio.run(state.register_compiled_strategy_version(name="EMA Breakout", source_text=_TEXT_V2))
        assert v2.version == 2
        assert saved.compiled_strategy_versions[v1.id] == [v1, v2]


class TestRegisterResearchableStrategy:
    """The real Strategy Lab <-> CompiledStrategyDefinition identity
    bridge — a Strategy is only ever created when the real compiler
    actually reached status == "compiled"."""

    def test_a_fully_specified_text_creates_both_a_real_definition_and_a_linked_strategy(self) -> None:
        definition, strategy, registry = register_researchable_strategy(
            {}, [], name="50 EMA Breakout Pullback Long", description="A real, testable long setup.", source_text=EMA_50_PULLBACK_LONG_TEXT
        )
        assert definition.status == "compiled"
        assert strategy is not None
        assert strategy.id == definition.id == "50-ema-breakout-pullback-long"
        assert strategy.compiled_definition_id == definition.id
        assert strategy.stage == "idea"
        assert registry[definition.id] == [definition]

    def test_the_symmetric_short_inverse_also_compiles_and_links(self) -> None:
        definition, strategy, _ = register_researchable_strategy(
            {}, [], name="50 EMA Breakout Pullback Short", description="A real, testable short setup.", source_text=EMA_50_PULLBACK_SHORT_TEXT
        )
        assert definition.status == "compiled"
        assert strategy is not None
        assert strategy.compiled_definition_id == definition.id

    def test_an_incomplete_text_returns_the_real_definition_but_no_strategy(self) -> None:
        definition, strategy, registry = register_researchable_strategy({}, [], name="Incomplete Strategy", description="x", source_text=_INCOMPLETE_TEXT)
        assert definition.status == "invalid"
        assert strategy is None
        # The real, honestly-incomplete definition is still persisted —
        # a CEO/agent can see exactly why no Strategy was created.
        assert registry[definition.id] == [definition]

    def test_raises_when_a_strategy_with_the_same_real_slug_already_exists(self) -> None:
        definition, strategy, registry = register_researchable_strategy(
            {}, [], name="50 EMA Breakout Pullback Long", description="x", source_text=EMA_50_PULLBACK_LONG_TEXT
        )
        assert strategy is not None
        try:
            register_researchable_strategy(registry, [strategy], name="50 EMA Breakout Pullback Long", description="x", source_text=EMA_50_PULLBACK_LONG_TEXT)
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "already exists" in str(exc)

    def test_other_existing_strategies_do_not_block_a_genuinely_new_one(self) -> None:
        from app.schemas import Strategy

        other = Strategy(id="strategy-momentum", name="Momentum Breakout", description="x", createdBy="echo", focusCategory="stock", createdAt="2026-01-01T00:00:00+00:00")
        definition, strategy, _ = register_researchable_strategy(
            {}, [other], name="50 EMA Breakout Pullback Long", description="x", source_text=EMA_50_PULLBACK_LONG_TEXT
        )
        assert strategy is not None


class TestRegisterResearchableStrategyState:
    def test_state_appends_the_new_strategy_and_persists_the_definition(self) -> None:
        state = GameState()
        before = asyncio.run(state.snapshot())
        before_count = len(before.strategies)
        saved, definition, strategy = asyncio.run(
            state.register_researchable_strategy(name="50 EMA Breakout Pullback Long", description="A real, testable long setup.", source_text=EMA_50_PULLBACK_LONG_TEXT)
        )
        assert strategy is not None
        assert len(saved.strategies) == before_count + 1
        assert saved.strategies[-1].id == strategy.id
        assert saved.compiled_strategy_versions[definition.id] == [definition]

    def test_an_incomplete_text_persists_the_definition_but_adds_no_strategy(self) -> None:
        state = GameState()
        before = asyncio.run(state.snapshot())
        before_count = len(before.strategies)
        saved, definition, strategy = asyncio.run(state.register_researchable_strategy(name="Incomplete Strategy", description="x", source_text=_INCOMPLETE_TEXT))
        assert strategy is None
        assert len(saved.strategies) == before_count
        assert saved.compiled_strategy_versions[definition.id] == [definition]

    def test_raises_when_registering_the_same_strategy_name_twice(self) -> None:
        state = GameState()
        asyncio.run(state.register_researchable_strategy(name="50 EMA Breakout Pullback Long", description="x", source_text=EMA_50_PULLBACK_LONG_TEXT))
        try:
            asyncio.run(state.register_researchable_strategy(name="50 EMA Breakout Pullback Long", description="x", source_text=EMA_50_PULLBACK_LONG_TEXT))
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
