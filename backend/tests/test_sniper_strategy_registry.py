"""Covers app/sniper_strategy_registry.py — CEO directive "TradeTown —
Sniper Strategy Engine + Registry 1.0." Pure metadata/governance only:
these tests never touch SniperRiskState, never evaluate a candidate,
never call evaluate_entry_firewall() — see that module's own docstring
for why."""
from __future__ import annotations

from app.schemas import SNIPER_STRATEGY_FAMILY, SNIPER_STRATEGY_ID, SNIPER_STRATEGY_NAME, SNIPER_STRATEGY_VERSION, SniperStrategyDefinition
from app.sniper_strategy_registry import default_sniper_strategies, register_sniper_strategy, resolve_sniper_strategy, set_sniper_strategy_status

_NOW = "2026-01-01T00:00:00+00:00"


def _strategy(*, strategy_id: str = "test-strategy", status: str = "enabled") -> SniperStrategyDefinition:
    return SniperStrategyDefinition(id=strategy_id, name="Test Strategy", family="test_family", version="1", status=status, provenance="hardcoded", createdAt=_NOW)  # type: ignore[arg-type]


class TestDefaultSniperStrategies:
    def test_registers_exactly_one_real_strategy(self) -> None:
        strategies = default_sniper_strategies()
        assert len(strategies) == 1

    def test_the_default_strategy_carries_the_real_canonical_identity(self) -> None:
        strategy = default_sniper_strategies()[0]
        assert strategy.id == SNIPER_STRATEGY_ID
        assert strategy.name == SNIPER_STRATEGY_NAME
        assert strategy.family == SNIPER_STRATEGY_FAMILY
        assert strategy.version == SNIPER_STRATEGY_VERSION

    def test_the_default_strategy_is_enabled_by_default(self) -> None:
        assert default_sniper_strategies()[0].status == "enabled"

    def test_the_default_strategy_provenance_is_honestly_hardcoded(self) -> None:
        assert default_sniper_strategies()[0].provenance == "hardcoded"


class TestResolveSniperStrategy:
    def test_resolves_a_known_strategy(self) -> None:
        strategies = [_strategy(strategy_id="a"), _strategy(strategy_id="b")]
        resolved = resolve_sniper_strategy(strategies, "b")
        assert resolved is not None
        assert resolved.id == "b"

    def test_unknown_strategy_id_returns_none_not_a_guess(self) -> None:
        strategies = [_strategy(strategy_id="a")]
        assert resolve_sniper_strategy(strategies, "does-not-exist") is None

    def test_empty_registry_resolves_nothing(self) -> None:
        assert resolve_sniper_strategy([], SNIPER_STRATEGY_ID) is None


class TestRegisterSniperStrategy:
    def test_registers_a_new_strategy(self) -> None:
        updated, error = register_sniper_strategy([], _strategy(strategy_id="new-one"))
        assert error is None
        assert len(updated) == 1
        assert updated[0].id == "new-one"

    def test_duplicate_id_is_rejected(self) -> None:
        existing = [_strategy(strategy_id="dup")]
        updated, error = register_sniper_strategy(existing, _strategy(strategy_id="dup"))
        assert error is not None
        assert "already registered" in error.lower()
        assert updated == existing  # unchanged on rejection

    def test_a_second_distinct_strategy_can_register_alongside_the_first(self) -> None:
        existing = default_sniper_strategies()
        updated, error = register_sniper_strategy(existing, _strategy(strategy_id="sibling-strategy"))
        assert error is None
        assert len(updated) == 2
        assert {s.id for s in updated} == {SNIPER_STRATEGY_ID, "sibling-strategy"}

    def test_enumerate_registered_strategies(self) -> None:
        strategies = [_strategy(strategy_id="a"), _strategy(strategy_id="b"), _strategy(strategy_id="c")]
        assert {s.id for s in strategies} == {"a", "b", "c"}


class TestSetSniperStrategyStatus:
    def test_disables_a_known_strategy(self) -> None:
        strategies = default_sniper_strategies()
        updated, error = set_sniper_strategy_status(strategies, SNIPER_STRATEGY_ID, "disabled")
        assert error is None
        resolved = resolve_sniper_strategy(updated, SNIPER_STRATEGY_ID)
        assert resolved is not None
        assert resolved.status == "disabled"

    def test_re_enables_a_disabled_strategy(self) -> None:
        strategies = default_sniper_strategies()
        disabled, _ = set_sniper_strategy_status(strategies, SNIPER_STRATEGY_ID, "disabled")
        re_enabled, error = set_sniper_strategy_status(disabled, SNIPER_STRATEGY_ID, "enabled")
        assert error is None
        assert resolve_sniper_strategy(re_enabled, SNIPER_STRATEGY_ID).status == "enabled"  # type: ignore[union-attr]

    def test_unknown_strategy_id_fails_safely_with_a_named_error(self) -> None:
        strategies = default_sniper_strategies()
        updated, error = set_sniper_strategy_status(strategies, "does-not-exist", "disabled")
        assert error is not None
        assert "no registered sniper strategy" in error.lower()
        assert updated == strategies  # unchanged on error

    def test_disabling_never_mutates_identity_fields(self) -> None:
        """Section 7 — status is the ONLY thing this function may
        change; id/name/family/version/provenance/createdAt must be
        byte-identical before and after."""
        strategies = default_sniper_strategies()
        before = strategies[0]
        updated, _ = set_sniper_strategy_status(strategies, SNIPER_STRATEGY_ID, "disabled")
        after = resolve_sniper_strategy(updated, SNIPER_STRATEGY_ID)
        assert after is not None
        assert after.id == before.id
        assert after.name == before.name
        assert after.family == before.family
        assert after.version == before.version
        assert after.provenance == before.provenance
        assert after.created_at == before.created_at

    def test_disabling_one_strategy_does_not_affect_a_sibling(self) -> None:
        strategies = [_strategy(strategy_id="a", status="enabled"), _strategy(strategy_id="b", status="enabled")]
        updated, error = set_sniper_strategy_status(strategies, "a", "disabled")
        assert error is None
        assert resolve_sniper_strategy(updated, "a").status == "disabled"  # type: ignore[union-attr]
        assert resolve_sniper_strategy(updated, "b").status == "enabled"  # type: ignore[union-attr]
