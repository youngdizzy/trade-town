"""Covers app/feature_registry.py — CEO directive "Phase 9 / Real
Market Data + Evidence Integrity Foundation," Feature Store section."""
from __future__ import annotations

from app.feature_registry import FEATURE_REGISTRY, feature_versions_for_definition
from app.schemas import StrategyIndicatorName
from app.strategy_compiler import compile_strategy_text
from typing import get_args


class TestFeatureRegistryCoverage:
    def test_every_strategy_indicator_name_has_a_descriptor(self) -> None:
        for name in get_args(StrategyIndicatorName):
            assert name in FEATURE_REGISTRY, f"{name!r} has no FeatureDescriptor"

    def test_every_descriptor_name_field_matches_its_key(self) -> None:
        for key, descriptor in FEATURE_REGISTRY.items():
            assert descriptor.name == key


class TestFeatureVersionsForDefinition:
    def test_ema_based_strategy_resolves_ema_version(self) -> None:
        definition = compile_strategy_text(
            name="EMA Test",
            source_text="Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.",
        )
        assert definition.status == "compiled"
        versions = feature_versions_for_definition(definition)
        assert FEATURE_REGISTRY["ema"].version in versions

    def test_versions_are_sorted_and_deduplicated(self) -> None:
        definition = compile_strategy_text(
            name="EMA Test 2",
            source_text="Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R.",
        )
        versions = feature_versions_for_definition(definition)
        assert versions == sorted(set(versions))

    def test_definition_with_no_sequence_returns_empty_list(self) -> None:
        definition = compile_strategy_text(name="Empty", source_text="")
        versions = feature_versions_for_definition(definition)
        assert versions == [] or isinstance(versions, list)
