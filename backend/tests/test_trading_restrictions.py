"""Covers app/trading_restrictions.py — CEO directive "Layered Kill
Switches." See that module's own docstring for why symbol/category is
the one real granularity layer built here (strategy and agent already
have their own, different real mechanisms)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.trading_restrictions import (
    activate_trading_restriction,
    active_restrictions,
    find_blocking_restriction,
    lift_trading_restriction,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestActivateTradingRestriction:
    def test_creates_a_real_active_restriction(self) -> None:
        restrictions, restriction, error = activate_trading_restriction(
            [], scope="symbol", target="NEXA", reason="Suspicious pump-and-dump pattern.", now_iso=_now_iso()
        )
        assert error is None
        assert restriction is not None
        assert restriction.active is True
        assert restriction.scope == "symbol"
        assert restriction.target == "NEXA"
        assert restrictions == [restriction]

    def test_requires_a_real_reason(self) -> None:
        restrictions, restriction, error = activate_trading_restriction([], scope="symbol", target="NEXA", reason="   ", now_iso=_now_iso())
        assert error is not None
        assert restriction is None
        assert restrictions == []

    def test_refuses_a_duplicate_active_restriction(self) -> None:
        first, _, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="first", now_iso=_now_iso())
        second, restriction, error = activate_trading_restriction(first, scope="symbol", target="NEXA", reason="second", now_iso=_now_iso())
        assert error is not None
        assert restriction is None
        assert second == first

    def test_allows_a_new_restriction_after_the_old_one_was_lifted(self) -> None:
        active, restriction, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="first", now_iso=_now_iso())
        assert restriction is not None
        lifted, _, _ = lift_trading_restriction(active, restriction.id, reason="resolved", now_iso=_now_iso())
        reactivated, new_restriction, error = activate_trading_restriction(lifted, scope="symbol", target="NEXA", reason="second incident", now_iso=_now_iso())
        assert error is None
        assert new_restriction is not None
        assert len(reactivated) == 2

    def test_different_scopes_on_the_same_target_string_do_not_collide(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="symbol", target="bitcoin", reason="one-off", now_iso=_now_iso())
        restrictions, restriction, error = activate_trading_restriction(restrictions, scope="category", target="bitcoin", reason="whole category", now_iso=_now_iso())
        assert error is None
        assert restriction is not None
        assert len(restrictions) == 2


class TestLiftTradingRestriction:
    def test_lifts_a_real_active_restriction(self) -> None:
        restrictions, restriction, _ = activate_trading_restriction([], scope="category", target="bitcoin", reason="volatility spike", now_iso=_now_iso())
        assert restriction is not None
        updated, lifted, error = lift_trading_restriction(restrictions, restriction.id, reason="calmed down", now_iso=_now_iso())
        assert error is None
        assert lifted is not None
        assert lifted.active is False
        assert lifted.lifted_reason == "calmed down"
        assert lifted.lifted_at is not None
        # History preserved, not deleted.
        assert len(updated) == 1

    def test_errors_on_an_unknown_id(self) -> None:
        updated, lifted, error = lift_trading_restriction([], "no-such-id", reason="", now_iso=_now_iso())
        assert error is not None
        assert lifted is None
        assert updated == []

    def test_errors_when_already_lifted(self) -> None:
        restrictions, restriction, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="one-off", now_iso=_now_iso())
        assert restriction is not None
        once_lifted, _, _ = lift_trading_restriction(restrictions, restriction.id, reason="resolved", now_iso=_now_iso())
        twice, lifted_again, error = lift_trading_restriction(once_lifted, restriction.id, reason="resolved again", now_iso=_now_iso())
        assert error is not None
        assert lifted_again is None
        assert twice == once_lifted


class TestFindBlockingRestriction:
    def test_none_when_nothing_is_restricted(self) -> None:
        assert find_blocking_restriction([], symbol="NEXA", category="stock") is None

    def test_finds_a_symbol_scoped_restriction(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="one-off", now_iso=_now_iso())
        found = find_blocking_restriction(restrictions, symbol="NEXA", category="stock")
        assert found is not None
        assert found.scope == "symbol"

    def test_finds_a_category_scoped_restriction(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="category", target="bitcoin", reason="whole category", now_iso=_now_iso())
        found = find_blocking_restriction(restrictions, symbol="BTC-USD", category="bitcoin")
        assert found is not None
        assert found.scope == "category"

    def test_ignores_a_lifted_restriction(self) -> None:
        restrictions, restriction, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="one-off", now_iso=_now_iso())
        assert restriction is not None
        lifted, _, _ = lift_trading_restriction(restrictions, restriction.id, reason="resolved", now_iso=_now_iso())
        assert find_blocking_restriction(lifted, symbol="NEXA", category="stock") is None

    def test_ignores_an_unrelated_symbol_and_category(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="one-off", now_iso=_now_iso())
        assert find_blocking_restriction(restrictions, symbol="OTHER", category="stock") is None

    def test_symbol_scope_takes_priority_over_category_scope(self) -> None:
        restrictions, _, _ = activate_trading_restriction([], scope="category", target="stock", reason="category-wide", now_iso=_now_iso())
        restrictions, _, _ = activate_trading_restriction(restrictions, scope="symbol", target="NEXA", reason="symbol-specific", now_iso=_now_iso())
        found = find_blocking_restriction(restrictions, symbol="NEXA", category="stock")
        assert found is not None
        assert found.scope == "symbol"


class TestActiveRestrictions:
    def test_filters_to_only_active(self) -> None:
        restrictions, restriction, _ = activate_trading_restriction([], scope="symbol", target="NEXA", reason="one-off", now_iso=_now_iso())
        assert restriction is not None
        restrictions, _, _ = activate_trading_restriction(restrictions, scope="symbol", target="OTHER", reason="another", now_iso=_now_iso())
        restrictions, _, _ = lift_trading_restriction(restrictions, restriction.id, reason="resolved", now_iso=_now_iso())
        active = active_restrictions(restrictions)
        assert len(active) == 1
        assert active[0].target == "OTHER"
