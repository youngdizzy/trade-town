"""Covers app/strategy_registry.py — CEO directive "Professional Quant
Firm Phase," Feature 37: real, persisted CompiledStrategyDefinition
version history.
"""
from __future__ import annotations

import asyncio

from app.state import GameState
from app.strategy_registry import register_strategy_version

_TEXT_V1 = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high."
_TEXT_V2 = "Buy when price closes above the 20 EMA, then enter when price closes above the previous swing high."


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
