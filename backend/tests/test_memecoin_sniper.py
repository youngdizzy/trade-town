"""Covers app/memecoin_sniper.py — CEO directive "TradeTown — Memecoin
Sniper Agent." Paper-only, simulated data throughout — see that
module's own docstring."""
from __future__ import annotations

import random

import pytest

from app.memecoin_sniper import (
    DEFAULT_HARD_STOP_PCT,
    DEFAULT_MAX_HOLD_SECONDS,
    DEFAULT_TAKE_PROFIT_PCT,
    MIN_WHALE_SIGNALS_FOR_STRATEGY_B,
    RawCandidate,
    build_candidate,
    build_sniper_pnl_history,
    classify_candidate,
    classify_timing,
    close_position,
    derive_failure_code,
    evaluate_entry_firewall,
    evaluate_live_arming,
    generate_leads,
    generate_lesson_from_history,
    manage_position_tick,
    open_position,
    position_risk_sol,
    run_safety_firewall,
    score_candidate,
    size_paper_position,
    strategy_accepts_candidate,
    tick_sniper_engine,
    update_risk_state_after_trade,
)
from app.schemas import (
    SNIPER_STRATEGY_B_FAMILY,
    SNIPER_STRATEGY_B_ID,
    SNIPER_STRATEGY_FAMILY,
    SNIPER_STRATEGY_ID,
    SniperEngineConfig,
    SniperRiskState,
    SniperStrategyDefinition,
    SniperTrade,
)
from app.sniper_strategy_registry import default_sniper_strategies, set_sniper_strategy_status

_NOW = "2024-01-01T00:00:00+00:00"


def _raw(**overrides: object) -> RawCandidate:
    base = dict(
        mint="a" * 32,
        symbol="MEWPEPE",
        name="MEWPEPE Token",
        age_seconds=20.0,
        price_usd=0.0001,
        market_cap_usd=100_000.0,
        liquidity_usd=80_000.0,
        liquidity_trend="rising",
        buy_count_1m=40,
        sell_count_1m=10,
        buy_pressure_pct=80.0,
        unique_buyers=30,
        unique_sellers=8,
        top10_concentration_pct=25.0,
        mint_authority_revoked=True,
        freeze_authority_revoked=True,
        creator_risk="weak_signal",
        whale_signal_count=2,
        social_momentum_pct=50.0,
        expected_slippage_pct=2.0,
        momentum_pct=20.0,
    )
    base.update(overrides)
    return RawCandidate(**base)  # type: ignore[arg-type]


class TestSafetyFirewall:
    def test_clean_candidate_is_safe_enough(self) -> None:
        status, checks = run_safety_firewall(_raw())
        assert status == "safe_enough"
        assert all(c.status == "pass" for c in checks)

    def test_active_mint_authority_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(mint_authority_revoked=False))
        assert status == "rejected"

    def test_active_freeze_authority_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(freeze_authority_revoked=False))
        assert status == "rejected"

    def test_confirmed_creator_risk_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(creator_risk="confirmed"))
        assert status == "rejected"

    def test_unknown_creator_risk_is_unknown_never_safe(self) -> None:
        status, _checks = run_safety_firewall(_raw(creator_risk="unknown"))
        assert status == "unknown"
        assert status != "safe_enough"

    def test_collapsing_liquidity_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(liquidity_trend="collapsing"))
        assert status == "rejected"

    def test_excessive_concentration_is_caution_not_pass(self) -> None:
        status, _checks = run_safety_firewall(_raw(top10_concentration_pct=70.0))
        assert status == "caution"

    def test_insufficient_liquidity_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(liquidity_usd=1_000.0))
        assert status == "rejected"

    def test_excessive_slippage_rejects(self) -> None:
        status, _checks = run_safety_firewall(_raw(expected_slippage_pct=25.0))
        assert status == "rejected"


class TestScoreCandidate:
    def test_score_is_bounded_0_to_100(self) -> None:
        score, components = score_candidate(_raw())
        assert 0.0 <= score <= 100.0
        assert len(components) == 7

    def test_weights_sum_to_100(self) -> None:
        _score, components = score_candidate(_raw())
        assert abs(sum(c.weight_pct for c in components) - 100.0) < 0.01

    def test_strong_evidence_scores_higher_than_weak(self) -> None:
        strong_score, _ = score_candidate(_raw(buy_pressure_pct=90.0, momentum_pct=50.0, whale_signal_count=4, social_momentum_pct=200.0))
        weak_score, _ = score_candidate(_raw(buy_pressure_pct=10.0, momentum_pct=-20.0, whale_signal_count=0, social_momentum_pct=-10.0))
        assert strong_score > weak_score


class TestClassifyCandidate:
    def test_hard_safety_rejection_beats_a_perfect_score(self) -> None:
        assert classify_candidate(99.0, "rejected") == "rejected"

    def test_high_score_and_safe_is_high_conviction(self) -> None:
        assert classify_candidate(85.0, "safe_enough") == "high_conviction"

    def test_low_score_and_safe_is_rejected(self) -> None:
        assert classify_candidate(30.0, "safe_enough") == "rejected"

    def test_unknown_safety_never_reaches_high_conviction(self) -> None:
        assert classify_candidate(95.0, "unknown") != "high_conviction"


class TestClassifyTiming:
    def test_extreme_momentum_with_weak_buy_pressure_is_exhausted(self) -> None:
        assert classify_timing(_raw(momentum_pct=200.0, buy_pressure_pct=30.0)) == "exhausted"

    def test_very_extended_momentum_is_late(self) -> None:
        assert classify_timing(_raw(momentum_pct=120.0, buy_pressure_pct=70.0)) == "late"

    def test_fresh_with_strong_buy_pressure_is_early_setup(self) -> None:
        assert classify_timing(_raw(age_seconds=10.0, buy_pressure_pct=60.0, momentum_pct=5.0)) == "early_setup"


class TestBuildCandidate:
    def test_produces_a_full_evidence_card(self) -> None:
        candidate = build_candidate("c1", _NOW)
        assert candidate.id == "c1"
        assert candidate.data_provenance == "simulated"
        assert candidate.opportunity_score is not None
        assert len(candidate.score_components) == 7
        assert candidate.decision_reason != ""

    def test_never_claims_real_data_provenance(self) -> None:
        for _ in range(20):
            candidate = build_candidate("c", _NOW)
            assert candidate.data_provenance == "simulated"


class TestEntryFirewall:
    def _candidate(self, **overrides: object):  # noqa: ANN201
        candidate = build_candidate("c1", _NOW)
        return candidate.model_copy(update=overrides)

    def test_rejected_safety_blocks_entry(self) -> None:
        candidate = self._candidate(safety_status="rejected")
        config = SniperEngineConfig()
        risk = SniperRiskState()
        allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert "safety_status" in reason
        assert block_reason == "safety"

    def test_kill_switch_triggered_blocks_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState(killSwitchTriggered=True)
        allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert "kill_switch" in reason
        assert block_reason == "kill_switch"

    def test_evaluate_entry_firewall_has_no_strategy_parameter_at_all(self) -> None:
        """CEO directive "TradeTown — Sniper Strategy Engine + Registry
        1.0," negative-space test #26/29 — the registry cannot bypass
        this firewall because this function structurally has no way to
        receive a strategy/registry argument in the first place; an
        enabled, resolved strategy can never influence its verdict."""
        import inspect

        params = list(inspect.signature(evaluate_entry_firewall).parameters)
        assert params == ["candidate", "config", "risk_state", "open_position_count"]

    def test_kill_switch_blocks_entry_even_for_a_candidate_that_would_otherwise_qualify_for_an_enabled_strategy(self) -> None:
        """Same real firewall rejection as test_kill_switch_triggered_
        blocks_entry above — restated explicitly against the directive's
        own "enabled strategy does not imply authorization" requirement.
        A resolved, enabled SniperStrategyDefinition existing elsewhere
        changes nothing here, because this call never receives one."""
        candidate = self._candidate(safety_status="safe_enough", classification="high_conviction", timing_state="entry_window", opportunity_score=99.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState(killSwitchTriggered=True)
        allowed, _reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert block_reason == "kill_switch"

    def test_max_positions_blocks_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState()
        allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk, config.max_open_positions)
        assert allowed is False
        assert "max_open_positions" in reason
        assert block_reason == "max_positions"

    def test_all_gates_passing_allows_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState()
        allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is True
        assert reason == "PASS"
        assert block_reason is None

    def test_every_real_gate_maps_to_its_own_distinct_block_reason(self) -> None:
        """"Terminal 2.1" directive, Phase 3 — every real gate the
        firewall can actually take must produce a real, distinct
        category; none of the 9 real gates should silently collapse into
        another's category or into `None`."""
        base = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        default_config = SniperEngineConfig()
        default_risk = SniperRiskState()
        cases: list[tuple[object, object, object, str]] = [
            (base.model_copy(update={"data_quality": "insufficient"}), default_config, default_risk, "data_quality"),
            (base.model_copy(update={"timing_state": "watch"}), default_config, default_risk, "timing"),
            (base.model_copy(update={"opportunity_score": 1.0}), default_config, default_risk, "score"),
            (base.model_copy(update={"rug_risk": "high"}), default_config, default_risk, "risk_profile"),
            (base.model_copy(update={"creator_risk": "confirmed"}), default_config, default_risk, "risk_profile"),
            (base, SniperEngineConfig(maxDailyLossPct=1.0), SniperRiskState(equitySol=10.0, dailyLossSol=1.0), "daily_loss"),
            (base, SniperEngineConfig(maxOpenRiskPct=1.0), SniperRiskState(equitySol=10.0, openRiskSol=1.0), "max_open_risk"),
        ]
        for candidate, config, risk, expected in cases:
            allowed, _reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)  # type: ignore[arg-type]
            assert allowed is False, f"expected block for {expected}"
            assert block_reason == expected

    def test_max_open_risk_pct_blocks_entry_when_real_open_risk_is_too_high(self) -> None:
        """Professional Trading Terminal directive, Part VIII — this gate
        used to be a dead no-op (`open_risk_sol` was never written
        anywhere, always its schema default of 0.0). Confirms the gate is
        now real: with `open_risk_sol` at real, honest parity with
        `max_open_risk_pct * equity`, a new candidate is correctly
        blocked."""
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig(maxOpenRiskPct=3.0)
        risk = SniperRiskState(equitySol=10.0, openRiskSol=0.3)  # exactly at the 3% cap
        allowed, reason, block_reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert "max_open_risk_pct" in reason
        assert block_reason == "max_open_risk"


class TestPositionSizing:
    def test_returns_none_with_zero_equity(self) -> None:
        candidate = build_candidate("c1", _NOW)
        config = SniperEngineConfig()
        risk = SniperRiskState(equitySol=0.0)
        assert size_paper_position(config, risk, candidate) is None

    def test_returns_none_without_a_score(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"opportunity_score": None})
        config = SniperEngineConfig()
        risk = SniperRiskState()
        assert size_paper_position(config, risk, candidate) is None

    def test_size_never_exceeds_the_liquidity_cap(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"opportunity_score": 90.0, "liquidity_usd": 1_000.0, "price_usd": 0.001})
        config = SniperEngineConfig(riskPerTradePct=50.0)  # deliberately huge to force the liquidity cap to bind
        risk = SniperRiskState(equitySol=1000.0)
        result = size_paper_position(config, risk, candidate)
        assert result is not None
        size_sol, _stop, _target = result
        max_liquidity_sol = (1_000.0 * 0.02) / 180.0
        assert size_sol <= max_liquidity_sol + 1e-9

    def test_stop_and_target_use_the_real_configured_percentages(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"opportunity_score": 90.0, "price_usd": 1.0})
        config = SniperEngineConfig()
        risk = SniperRiskState(equitySol=100.0)
        result = size_paper_position(config, risk, candidate)
        assert result is not None
        _size, stop, target = result
        assert abs(stop - 1.0 * (1 - DEFAULT_HARD_STOP_PCT / 100)) < 1e-9
        assert abs(target - 1.0 * (1 + DEFAULT_TAKE_PROFIT_PCT / 100)) < 1e-9


class TestExitEngine:
    def test_hard_stop_triggers_exit(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        _updated, exit_reason = manage_position_tick(position, 0.80, 1.0)
        assert exit_reason == "stop_loss"

    def test_take_profit_triggers_exit(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        _updated, exit_reason = manage_position_tick(position, 1.60, 1.0)
        assert exit_reason == "take_profit"

    def test_max_hold_triggers_exit(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        _updated, exit_reason = manage_position_tick(position, 1.02, DEFAULT_MAX_HOLD_SECONDS + 1.0)
        assert exit_reason == "max_hold"

    def test_no_exit_when_price_is_between_stop_and_target(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        _updated, exit_reason = manage_position_tick(position, 1.05, 1.0)
        assert exit_reason is None

    def test_trailing_stop_activates_and_can_trigger(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        position, exit_reason = manage_position_tick(position, 1.30, 1.0)
        assert exit_reason is None
        assert position.trailing_active is True
        position, exit_reason = manage_position_tick(position, 1.10, 1.0)
        assert exit_reason == "trailing_stop"


class TestPositionRiskSol:
    """Professional Trading Terminal directive, Part VIII — the single
    real risk-in-SOL formula shared by an open position's own `risk_sol`
    field and a closed trade's `SniperTrade.risk_sol`, so the two can
    never drift into two different definitions of the same real number."""

    def test_matches_the_hand_computed_stop_distance(self) -> None:
        assert abs(position_risk_sol(1.0, 0.88, 2.0) - 0.24) < 1e-9

    def test_zero_at_zero_entry_price(self) -> None:
        assert position_risk_sol(0.0, 0.5, 10.0) == 0.0

    def test_open_position_carries_a_real_risk_sol_field(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 2.0, 0.88, 1.55, _NOW)
        assert abs(position.risk_sol - 0.24) < 1e-9

    def test_close_position_risk_sol_matches_the_open_positions_own_field(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 2.0, 0.88, 1.55, _NOW)
        _closed, trade = close_position(position, 1.0, "manual_exit", _NOW)
        assert abs(trade.risk_sol - position.risk_sol) < 1e-9


class TestStrategyIdentity:
    """"Terminal 2.1" directive, Phase 1, and CEO directive "TradeTown —
    Sniper Strategy Engine + Registry 1.0" — no fabricated strategy
    version. Every position/trade must carry a real, honest identity.
    Without a resolved registry entry (`strategy=None`, every existing
    caller/test unaffected by the later directive), `strategyVersionId`
    stays `None` and `strategyVersionStatus` stays `"unavailable"` —
    exactly the prior behavior. With a real, resolved
    `SniperStrategyDefinition` (the registry directive's own real
    addition), `strategyVersionStatus` honestly becomes `"versioned"`
    for the first time, since a real, deterministic version now
    genuinely exists — see TestOpenPositionWithRegistry below."""

    def test_open_position_carries_real_honest_identity(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        assert position.strategy_id == "memecoin-sniper"
        assert position.strategy_name != ""
        assert position.strategy_version_id is None
        assert position.strategy_version_status == "unavailable"

    def test_closed_trade_carries_the_positions_own_identity_forward(self) -> None:
        """Copied from the position, not independently re-defaulted — so
        a future real versioning system would carry a position's own
        real identity onto its trade record."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        _closed, trade = close_position(position, 1.0, "manual_exit", _NOW)
        assert trade.strategy_id == position.strategy_id
        assert trade.strategy_name == position.strategy_name
        assert trade.strategy_version_id == position.strategy_version_id
        assert trade.strategy_version_status == position.strategy_version_status


class TestOpenPositionWithRegistry:
    """CEO directive "TradeTown — Sniper Strategy Engine + Registry
    1.0" — `open_position(..., strategy=...)` stamps the real, resolved
    registry identity, and only that; a `strategy=None` caller (every
    pre-directive test/caller) is completely unaffected."""

    def test_a_resolved_strategy_stamps_real_identity_and_a_real_version(self) -> None:
        strategy = default_sniper_strategies()[0]
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW, strategy=strategy)
        assert position.strategy_id == strategy.id
        assert position.strategy_name == strategy.name
        assert position.strategy_version_id == strategy.version
        assert position.strategy_version_status == "versioned"

    def test_no_strategy_argument_preserves_the_exact_prior_default_identity(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        assert position.strategy_version_id is None
        assert position.strategy_version_status == "unavailable"

    def test_a_different_registered_strategys_identity_is_stamped_correctly(self) -> None:
        """Proves this reads the REAL resolved strategy's own fields,
        never a hardcoded constant — a sibling strategy's identity must
        appear verbatim, not the canonical memecoin-sniper one."""
        sibling = SniperStrategyDefinition(id="sibling", name="Sibling Strategy", family="test_family", version="7", status="enabled", provenance="hardcoded", createdAt=_NOW)  # type: ignore[arg-type]
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW, strategy=sibling)
        assert position.strategy_id == "sibling"
        assert position.strategy_version_id == "7"

    def test_closed_trade_carries_the_registry_stamped_identity_forward(self) -> None:
        strategy = default_sniper_strategies()[0]
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW, strategy=strategy)
        _closed, trade = close_position(position, 1.0, "manual_exit", _NOW)
        assert trade.strategy_version_id == strategy.version
        assert trade.strategy_version_status == "versioned"

    def test_a_later_version_bump_never_mutates_an_already_closed_historical_trade(self) -> None:
        """Section 7 — "Do not silently rewrite trade.strategy_version
        when the registry version changes." Simulates a future material
        implementation change bumping the registry's own version: a
        trade closed under the OLD version must keep reporting that old
        version forever, even after the registry moves on."""
        v1 = default_sniper_strategies()[0]
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        old_position = open_position(candidate, 1.0, 0.88, 1.55, _NOW, strategy=v1)
        _closed, old_trade = close_position(old_position, 1.0, "manual_exit", _NOW)
        assert old_trade.strategy_version_id == "1"

        v2 = v1.model_copy(update={"version": "2"})  # simulates a future real version bump
        new_candidate = build_candidate("c2", _NOW).model_copy(update={"price_usd": 1.0})
        new_position = open_position(new_candidate, 1.0, 0.88, 1.55, _NOW, strategy=v2)

        # The historical record is untouched — never rewritten in place.
        assert old_trade.strategy_version_id == "1"
        # Only the NEW position picks up the new version.
        assert new_position.strategy_version_id == "2"


class TestTrailingActivatedAt:
    """"Terminal 2.1" directive, Phase 2 — a real timestamp for a
    truthful TRAIL ACTIVATION chart marker."""

    def test_none_before_trailing_activates(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        assert position.trailing_activated_at is None

    def test_set_once_when_trailing_first_activates(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.60, 2.0, _NOW)
        activation_time = "2024-01-01T00:05:00+00:00"
        updated, _exit = manage_position_tick(position, 1.30, 1.0, now=activation_time)  # +30% >= DEFAULT_TRAILING_ACTIVATION_PCT
        assert updated.trailing_active is True
        assert updated.trailing_activated_at == activation_time
        assert updated.trailing_activated_price == 1.30

    def test_never_overwritten_on_later_ticks(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.60, 2.0, _NOW)
        first, _ = manage_position_tick(position, 1.30, 1.0, now="2024-01-01T00:05:00+00:00")
        second, _ = manage_position_tick(first, 1.35, 1.0, now="2024-01-01T00:06:00+00:00")
        assert second.trailing_activated_at == "2024-01-01T00:05:00+00:00"


class TestClosePositionAndFailureCodes:
    def test_close_position_computes_real_r_multiple(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        closed, trade = close_position(position, 0.88, "stop_loss", _NOW)
        assert closed.status == "closed"
        assert trade.r_multiple == -1.0
        assert trade.failure_codes == ["momentum_exhaustion"]

    def test_closed_trade_carries_the_real_stop_target_and_trailing_activation(self) -> None:
        """"Terminal 2.1" directive, Phase 2 — a closed trade's own real
        levels, needed for truthful STOP/TP/TRAIL chart markers on its
        historical chart."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.60, 2.0, _NOW)
        activated, _exit = manage_position_tick(position, 1.30, 1.0, now="2024-01-01T00:05:00+00:00")
        assert activated.trailing_activated_at == "2024-01-01T00:05:00+00:00"
        _closed, trade = close_position(activated, 1.15, "trailing_stop", "2024-01-01T00:06:00+00:00")
        assert trade.stop_price == position.stop_price
        assert trade.target_price == position.target_price

    def test_a_pre_existing_trade_missing_stop_target_fields_still_loads(self) -> None:
        """Real regression this pass caught (and fixed) via its own live
        verification: SniperTrade.stopPrice/targetPrice were briefly
        required fields with no default, which broke loading ANY
        pre-existing save whose permanent sniper_trade_history predated
        them — the exact kind of accidental data-loss bug CLAUDE.md's own
        "never silently rewrite/discard history" principle exists to
        prevent. Confirms a trade dict shaped like OLD save data (no
        stopPrice/targetPrice keys at all) still validates, with an
        honest `None` — never a fabricated price — for both."""
        old_style_trade_dict = {
            "id": "t1",
            "mint": "m",
            "symbol": "X",
            "openedAt": _NOW,
            "closedAt": _NOW,
            "entryPrice": 1.0,
            "exitPrice": 0.88,
            "sizeSol": 1.0,
            "riskSol": 0.12,
            "rMultiple": -1.0,
            "pnlSol": -0.12,
            "maxFavorableExcursionPct": 0.0,
            "maxAdverseExcursionPct": -12.0,
            "holdTimeSeconds": 10.0,
            "exitReason": "stop_loss",
            "failureCodes": ["momentum_exhaustion"],
            "thesis": "x",
            "thesisValidated": False,
            # No stopPrice/targetPrice/trailingActivatedAt/strategyId/etc.
            # keys at all — exactly what an old, pre-this-pass save's
            # sniper_trade_history entries actually look like.
        }
        trade = SniperTrade.model_validate(old_style_trade_dict)
        assert trade.stop_price is None
        assert trade.target_price is None
        assert trade.strategy_id == "memecoin-sniper"  # a real, honest default, not a missing-field crash

    def test_winning_trade_has_no_failure_codes(self) -> None:
        assert derive_failure_code("take_profit", 55.0) == []

    def test_unknown_exit_reason_maps_to_unknown_failure(self) -> None:
        assert derive_failure_code("momentum_failure", -5.0) == ["momentum_exhaustion"]


class TestRiskStateUpdates:
    def test_losing_trade_increases_consecutive_losses(self) -> None:
        risk = SniperRiskState()
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.88, stopPrice=0.88, targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=-1.0, pnlSol=-0.12, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-12.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.consecutive_losses == 1
        assert updated.equity_sol < risk.equity_sol

    def test_winning_trade_resets_consecutive_losses(self) -> None:
        risk = SniperRiskState(consecutiveLosses=2)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.55, stopPrice=0.88, targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=4.6, pnlSol=0.55, maxFavorableExcursionPct=55.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.consecutive_losses == 0

    def test_size_multiplier_never_increases_above_one(self) -> None:
        risk = SniperRiskState(sizeMultiplier=0.5)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.55, stopPrice=0.88, targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=4.6, pnlSol=0.55, maxFavorableExcursionPct=55.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.size_multiplier <= 0.5 or updated.size_multiplier == 1.0

    def test_drawdown_past_6pct_triggers_kill_switch(self) -> None:
        risk = SniperRiskState(equitySol=100.0, peakEquitySol=100.0, killSwitchArmed=True)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.0, stopPrice=0.88, targetPrice=1.55, sizeSol=100.0, riskSol=100.0, rMultiple=-8.0, pnlSol=-8.0, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-100.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.kill_switch_triggered is True
        assert updated.kill_switch_reason is not None

    def test_kill_switch_never_triggers_when_not_armed(self) -> None:
        risk = SniperRiskState(equitySol=100.0, peakEquitySol=100.0, killSwitchArmed=False)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.0, stopPrice=0.88, targetPrice=1.55, sizeSol=100.0, riskSol=100.0, rMultiple=-8.0, pnlSol=-8.0, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-100.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.kill_switch_triggered is False


class TestLiveArming:
    def test_always_blocked_in_this_environment(self) -> None:
        status = evaluate_live_arming()
        assert status.armed is False
        assert len(status.blocking_reasons) > 0

    def test_no_wallet_reason_present_by_default(self) -> None:
        status = evaluate_live_arming()
        assert any("wallet" in r.lower() for r in status.blocking_reasons)

    def test_wallet_reason_drops_once_a_wallet_is_active_but_still_blocked(self) -> None:
        """"Terminal 2.1" directive, Phase 5 — adding a wallet never
        arms live trading; the OTHER real prerequisites (RPC/Jupiter/
        validation) stay unmet regardless."""
        without = evaluate_live_arming(has_active_wallet=False)
        with_wallet = evaluate_live_arming(has_active_wallet=True)
        assert with_wallet.armed is False
        assert len(with_wallet.blocking_reasons) == len(without.blocking_reasons) - 1
        assert not any("no active wallet" in r.lower() for r in with_wallet.blocking_reasons)


class TestLeadsAndLessons:
    def test_generated_leads_are_always_simulated(self) -> None:
        leads = generate_leads(5)
        assert len(leads) == 5
        assert all(lead.data_provenance == "simulated" for lead in leads)

    def test_lesson_requires_minimum_sample_size(self) -> None:
        assert generate_lesson_from_history([], _NOW) is None

    def test_lesson_generated_when_timing_failures_are_worse(self) -> None:
        history = []
        for i in range(15):
            history.append(SniperTrade(id=f"t{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.1, stopPrice=0.88, targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=0.8, pnlSol=0.1, maxFavorableExcursionPct=10.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True))  # type: ignore[call-arg]
        for i in range(10):
            history.append(SniperTrade(id=f"tf{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.95, stopPrice=0.88, targetPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=-0.4, pnlSol=-0.05, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-5.0, holdTimeSeconds=70.0, exitReason="max_hold", failureCodes=["timing_failure"], thesis="x", thesisValidated=False))  # type: ignore[call-arg]
        lesson = generate_lesson_from_history(history, _NOW)
        assert lesson is not None
        assert lesson.sample_size == 10
        assert lesson.data_provenance == "simulated"


class TestTickEngine:
    def test_stopped_engine_makes_no_changes(self) -> None:
        config = SniperEngineConfig(status="stopped")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0)
        assert result.candidates == []
        assert result.positions == []
        assert result.events == []

    def test_running_engine_can_discover_and_populate_leads(self) -> None:
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0)
        assert len(result.leads) > 0

    def test_paused_engine_still_manages_open_positions_but_discovers_nothing(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.99, 1.55, _NOW)
        config = SniperEngineConfig(status="paused")
        risk = SniperRiskState()
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=200.0)
        assert len(result.candidates) == 0
        assert any(p.status == "closed" for p in result.positions) or any(p.hold_time_seconds > 0 for p in result.positions)

    def test_emergency_stop_blocks_new_discovery_even_while_running(self) -> None:
        """CEO directive "TradeTown Ultimate — Master 11-Pillar
        Architecture Directive," Governance milestone — the global
        Emergency Stop must reach Sniper too. seed(7) is a known,
        verified-reliable roll that discovers a candidate under a plain
        "running" engine (see the sibling test above) — with
        emergency_stop_active=True, that same roll must produce nothing."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, emergency_stop_active=True)
        assert result.candidates == []

    def test_emergency_stop_defaults_to_false_and_does_not_change_existing_behavior(self) -> None:
        """Every existing caller/test that hasn't been threaded through
        (the default) must keep discovering exactly as before."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0)
        assert len(result.candidates) == 1

    def test_emergency_stop_does_not_freeze_existing_open_positions(self) -> None:
        """Mirrors app/emergency_stop.py's own real equities scope:
        already-open positions keep being managed (marked-to-market,
        can still exit) even while Emergency Stop is active — only NEW
        entries are blocked, never a full "stopped"-style freeze."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.99, 1.55, _NOW)  # tight stop, guaranteed to trip
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=200.0, emergency_stop_active=True)
        assert any(p.status == "closed" for p in result.positions)
        assert result.candidates == []

    def test_no_strategies_argument_preserves_the_exact_prior_default_behavior(self) -> None:
        """CEO directive "TradeTown — Sniper Strategy Engine + Registry
        1.0" — `strategies=None` (every existing caller/test) must
        discover exactly as before this directive."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0)
        assert len(result.candidates) == 1

    def test_an_enabled_registered_strategy_discovers_and_stamps_real_identity(self) -> None:
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        strategies = default_sniper_strategies()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, strategies=strategies)
        assert len(result.candidates) == 1
        opened = [p for p in result.positions if p.status == "open"]
        for position in opened:
            assert position.strategy_id == SNIPER_STRATEGY_ID
            assert position.strategy_version_status == "versioned"

    def test_a_disabled_strategy_blocks_new_discovery_even_while_running(self) -> None:
        """Section 6 — DISABLED stops new discovery/entries exactly like
        the global Emergency Stop does. seed(7) is a known, verified-
        reliable roll that discovers a candidate when enabled (see the
        sibling test above) — with the ONLY registered strategy
        disabled, that same roll must produce nothing. Uses a single-
        strategy registry (not `default_sniper_strategies()`, which
        now seeds a second, independently-enabled strategy — see
        TestMultiStrategyEnableDisable below for that scenario) to
        isolate exactly the "sole strategy disabled" case this test
        has always covered."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        strategies, error = set_sniper_strategy_status([default_sniper_strategies()[0]], SNIPER_STRATEGY_ID, "disabled")
        assert error is None
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, strategies=strategies)
        assert result.candidates == []

    def test_a_disabled_strategy_does_not_freeze_existing_open_positions(self) -> None:
        """Section 6's explicit rule — DISABLED STRATEGY != DELETE/FREEZE.
        An already-open position must keep being managed/able to exit
        even while its own strategy is disabled. Single-strategy
        registry — see the sibling test above for why."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.99, 1.55, _NOW)  # tight stop, guaranteed to trip
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        strategies, _ = set_sniper_strategy_status([default_sniper_strategies()[0]], SNIPER_STRATEGY_ID, "disabled")
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=200.0, strategies=strategies)
        assert any(p.status == "closed" for p in result.positions)
        assert result.candidates == []

    def test_an_unresolvable_registry_fails_closed_never_falls_back_to_bare_constants(self) -> None:
        """Rule 10 — a real, non-empty registry that simply doesn't
        contain the canonical strategy id (a genuinely corrupted/
        mismatched state) must fail closed for new discovery/entries,
        never silently fall back to the pre-directive bare-constant
        behavior."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        unrelated_strategy = SniperStrategyDefinition(id="unrelated", name="Unrelated", family="test_family", version="1", status="enabled", provenance="hardcoded", createdAt=_NOW)  # type: ignore[arg-type]
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, strategies=[unrelated_strategy])
        assert result.candidates == []

    def test_an_empty_registry_list_also_fails_closed(self) -> None:
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, strategies=[])
        assert result.candidates == []

    def test_emergency_stop_and_disabled_strategy_are_independent_gates(self) -> None:
        """Neither gate can substitute for or bypass the other — both
        must independently block."""
        random.seed(7)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        strategies = default_sniper_strategies()  # enabled
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, emergency_stop_active=True, strategies=strategies)
        assert result.candidates == []

    def test_a_closing_position_produces_a_real_structured_exit_event(self) -> None:
        """Professional Trading Terminal directive, Part VII — the tick
        engine's own events used to be plain formatted strings this pass
        found were generated then immediately discarded by app/nexus.py
        every tick. Confirms they're now real, structured `SniperEvent`s
        with a real mint/symbol/type, not just non-empty text."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0, "mint": "mmm", "symbol": "ZZZ"})
        position = open_position(candidate, 1.0, 0.99, 1.55, _NOW)  # tight stop, guaranteed to trip
        config = SniperEngineConfig(status="paused")
        risk = SniperRiskState()
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=200.0)
        exit_events = [e for e in result.events if e.type == "exit"]
        assert len(exit_events) == 1
        assert exit_events[0].mint == "mmm"
        assert exit_events[0].symbol == "ZZZ"
        assert exit_events[0].timestamp

    def test_open_risk_sol_recomputes_from_real_open_positions_after_a_close(self) -> None:
        """The bug this pass found and fixed: `open_risk_sol` used to
        never be written anywhere, staying at its schema default of 0.0
        forever. Confirms it now tracks reality: a lone open position's
        risk closes out to exactly 0.0 once that position closes."""
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.99, 1.55, _NOW)
        assert position.risk_sol > 0.0
        config = SniperEngineConfig(status="paused")
        risk = SniperRiskState(openRiskSol=position.risk_sol)
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=200.0)
        assert all(p.status == "closed" for p in result.positions)
        assert result.risk_state.open_risk_sol == 0.0

    def test_open_risk_sol_reflects_a_still_open_position(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.5, 5.0, _NOW)  # wide stop/target — won't trip in one small tick
        config = SniperEngineConfig(status="paused")
        risk = SniperRiskState()
        random.seed(1)
        result = tick_sniper_engine(config, risk, [], [position], [], [], [], tick_seconds=1.0)
        assert any(p.status == "open" for p in result.positions)
        assert abs(result.risk_state.open_risk_sol - position.risk_sol) < 1e-6

    def test_a_new_entry_produces_a_sniped_event(self) -> None:
        random.seed(42)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState(equitySol=1000.0)
        candidates: list = []
        positions: list = []
        sniped_events = []
        for _ in range(3000):
            result = tick_sniper_engine(config, risk, candidates, positions, [], [], [], tick_seconds=1.0)
            candidates, positions, risk = result.candidates, result.positions, result.risk_state
            sniped_events.extend(e for e in result.events if e.type == "sniped")
            if sniped_events:
                break
        assert len(sniped_events) > 0
        assert sniped_events[0].mint is not None
        assert sniped_events[0].detail

    def test_never_produces_a_live_data_provenance_anywhere(self) -> None:
        random.seed(3)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState()
        candidates: list = []
        positions: list = []
        trades: list = []
        leads: list = []
        lessons: list = []
        for _ in range(50):
            result = tick_sniper_engine(config, risk, candidates, positions, trades, leads, lessons, tick_seconds=1.0)
            candidates, positions, trades, leads, lessons, risk = result.candidates, result.positions, result.trade_history, result.leads, result.lessons, result.risk_state
        assert all(c.data_provenance == "simulated" for c in candidates)
        assert all(p.data_provenance == "simulated" for p in positions)
        assert all(t.data_provenance == "simulated" for t in trades)
        assert all(lead.data_provenance == "simulated" for lead in leads)


class TestStrategyAcceptsCandidate:
    """CEO directive "TradeTown — Sniper Multi-Strategy Dispatch Proof
    1.0", Section 7 — proves the two registered strategies genuinely
    have DIFFERENT deterministic decision logic, not duplicate labels
    on the same rule. Never touches safety/risk (this function has no
    such parameters at all) — only the pure "should this strategy
    evaluate this candidate" question."""

    def _strategy(self, family: str) -> SniperStrategyDefinition:
        return SniperStrategyDefinition(id="x", name="X", family=family, version="1", status="enabled", provenance="hardcoded", createdAt=_NOW)  # type: ignore[arg-type]

    def _candidate(self, *, classification: str, whale_signal_count: int) -> object:
        return build_candidate("c1", _NOW).model_copy(update={"classification": classification, "whale_signal_count": whale_signal_count})

    def test_strategy_a_accepts_a_qualified_candidate_regardless_of_whale_count(self) -> None:
        strategy_a = self._strategy(SNIPER_STRATEGY_FAMILY)
        candidate = self._candidate(classification="qualified", whale_signal_count=0)
        assert strategy_accepts_candidate(strategy_a, candidate) is True

    def test_strategy_a_rejects_a_merely_watch_classified_candidate(self) -> None:
        strategy_a = self._strategy(SNIPER_STRATEGY_FAMILY)
        candidate = self._candidate(classification="watch", whale_signal_count=5)
        assert strategy_accepts_candidate(strategy_a, candidate) is False

    def test_strategy_b_accepts_a_whale_confirmed_candidate_regardless_of_classification(self) -> None:
        strategy_b = self._strategy(SNIPER_STRATEGY_B_FAMILY)
        candidate = self._candidate(classification="watch", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        assert strategy_accepts_candidate(strategy_b, candidate) is True

    def test_strategy_b_rejects_a_candidate_below_the_whale_threshold(self) -> None:
        strategy_b = self._strategy(SNIPER_STRATEGY_B_FAMILY)
        candidate = self._candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B - 1)
        assert strategy_accepts_candidate(strategy_b, candidate) is False

    def test_a_accepts_and_b_rejects_the_same_candidate(self) -> None:
        """Section 7's own required direction #1 — one real candidate,
        genuinely different verdicts."""
        candidate = self._candidate(classification="high_conviction", whale_signal_count=0)
        assert strategy_accepts_candidate(self._strategy(SNIPER_STRATEGY_FAMILY), candidate) is True
        assert strategy_accepts_candidate(self._strategy(SNIPER_STRATEGY_B_FAMILY), candidate) is False

    def test_b_accepts_and_a_rejects_the_same_candidate(self) -> None:
        """Section 7's own required direction #2 (vice versa) — proves
        this is genuine dispatch, not B being a narrower copy of A."""
        candidate = self._candidate(classification="rejected", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        assert strategy_accepts_candidate(self._strategy(SNIPER_STRATEGY_FAMILY), candidate) is False
        assert strategy_accepts_candidate(self._strategy(SNIPER_STRATEGY_B_FAMILY), candidate) is True

    def test_identical_input_is_deterministic(self) -> None:
        strategy_b = self._strategy(SNIPER_STRATEGY_B_FAMILY)
        candidate = self._candidate(classification="watch", whale_signal_count=3)
        results = {strategy_accepts_candidate(strategy_b, candidate) for _ in range(20)}
        assert results == {True}

    def test_an_unrecognized_strategy_family_fails_closed(self) -> None:
        """Rule 10, generalized to the family level — a corrupted or
        foreign registry entry must never be silently accepted, and
        must never silently fall back to either known family's rule."""
        unknown = self._strategy("some_future_family_nobody_implemented_yet")
        candidate = self._candidate(classification="high_conviction", whale_signal_count=99)
        assert strategy_accepts_candidate(unknown, candidate) is False


class TestMultiStrategyDispatchInTick:
    """CEO directive "TradeTown — Sniper Multi-Strategy Dispatch Proof
    1.0" — proves the real `tick_sniper_engine()` dispatch LOOP (not
    just the isolated pure function above) routes a controlled
    candidate to the correct strategy and stamps the resulting
    position with that strategy's own real identity. Monkeypatches
    `build_candidate()` at its call site inside app.memecoin_sniper so
    the discovered candidate is controlled and deterministic — the
    same style tests/test_nexus.py already uses to prove real wiring —
    and forces the discovery roll via `random.random` (never touching
    `generate_leads()`'s own internal draws, which call methods on the
    module's private `Random` instance directly, not the rebound
    module-level name)."""

    def _fixed_candidate(self, **overrides: object) -> object:
        base = build_candidate("cand-fixed", _NOW).model_copy(
            update={
                "price_usd": 1.0,
                "safety_status": "safe_enough",
                "data_quality": "sufficient",
                "timing_state": "entry_window",
                "rug_risk": "low",
                "creator_risk": "weak_signal",
                "opportunity_score": 65.0,
                "classification": "watch",
                "whale_signal_count": 0,
            }
        )
        return base.model_copy(update=overrides)

    def _tick_with_fixed_candidate(self, monkeypatch, candidate: object, strategies: list) -> object:
        monkeypatch.setattr("app.memecoin_sniper.build_candidate", lambda *a, **k: candidate)
        monkeypatch.setattr("random.random", lambda: 0.0)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState(equitySol=1000.0)
        return tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, strategies=strategies)

    def test_a_whale_confirmed_non_qualified_candidate_opens_under_strategy_b_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        candidate = self._fixed_candidate(classification="watch", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, default_sniper_strategies())
        opened = [p for p in result.positions if p.status == "open"]
        assert len(opened) == 1
        assert opened[0].strategy_id == SNIPER_STRATEGY_B_ID

    def test_a_qualified_non_whale_confirmed_candidate_opens_under_strategy_a_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=0)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, default_sniper_strategies())
        opened = [p for p in result.positions if p.status == "open"]
        assert len(opened) == 1
        assert opened[0].strategy_id == SNIPER_STRATEGY_ID

    def test_when_both_would_accept_registry_order_gives_strategy_a_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Section 6 — one canonical dispatch boundary, not a random or
        ambiguous pick: the first enabled, accepting strategy in
        registry order always wins."""
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, default_sniper_strategies())
        opened = [p for p in result.positions if p.status == "open"]
        assert len(opened) == 1
        assert opened[0].strategy_id == SNIPER_STRATEGY_ID

    def test_neither_strategy_accepting_produces_no_entry_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        candidate = self._fixed_candidate(classification="watch", whale_signal_count=0)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, default_sniper_strategies())
        assert not any(p.status == "open" for p in result.positions)
        assert not any(e.type == "sniped" for e in result.events)

    def test_disabling_strategy_a_lets_strategy_b_alone_produce_the_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SAFETY test matrix #23-26 — B enabled alone must still be
        able to produce a real, correctly-stamped entry; A being
        disabled must not block B."""
        strategies, error = set_sniper_strategy_status(default_sniper_strategies(), SNIPER_STRATEGY_ID, "disabled")
        assert error is None
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, strategies)
        opened = [p for p in result.positions if p.status == "open"]
        assert len(opened) == 1
        assert opened[0].strategy_id == SNIPER_STRATEGY_B_ID

    def test_disabling_strategy_b_leaves_strategy_a_unaffected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        strategies, error = set_sniper_strategy_status(default_sniper_strategies(), SNIPER_STRATEGY_B_ID, "disabled")
        assert error is None
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=0)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, strategies)
        opened = [p for p in result.positions if p.status == "open"]
        assert len(opened) == 1
        assert opened[0].strategy_id == SNIPER_STRATEGY_ID

    def test_both_disabled_blocks_discovery_entirely(self, monkeypatch: pytest.MonkeyPatch) -> None:
        strategies, _ = set_sniper_strategy_status(default_sniper_strategies(), SNIPER_STRATEGY_ID, "disabled")
        strategies, error = set_sniper_strategy_status(strategies, SNIPER_STRATEGY_B_ID, "disabled")
        assert error is None
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, strategies)
        assert result.candidates == []

    def test_a_candidate_that_fails_the_shared_firewall_opens_no_position_for_either_strategy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SAFETY test matrix #29-34 — the accepting strategy still has
        to clear the exact same, unmodified firewall; acceptance alone
        never authorizes an entry."""
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B, rug_risk="high")
        result = self._tick_with_fixed_candidate(monkeypatch, candidate, default_sniper_strategies())
        assert not any(p.status == "open" for p in result.positions)
        no_trade_events = [e for e in result.events if e.type == "no_trade"]
        assert len(no_trade_events) == 1
        assert no_trade_events[0].block_reason == "risk_profile"

    def test_emergency_stop_blocks_the_dispatch_loop_even_when_both_would_accept(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SAFETY test matrix #35-36 — Emergency Stop is independent of
        and takes priority over strategy identity."""
        candidate = self._fixed_candidate(classification="high_conviction", whale_signal_count=MIN_WHALE_SIGNALS_FOR_STRATEGY_B)
        monkeypatch.setattr("app.memecoin_sniper.build_candidate", lambda *a, **k: candidate)
        monkeypatch.setattr("random.random", lambda: 0.0)
        config = SniperEngineConfig(status="running")
        risk = SniperRiskState(equitySol=1000.0)
        result = tick_sniper_engine(config, risk, [], [], [], [], [], tick_seconds=1.0, emergency_stop_active=True, strategies=default_sniper_strategies())
        assert result.candidates == []


class TestUpdateSniperEngineRequestCamelCase:
    """CEO directive "UI / Governance / Travel Mode Hardening" — the
    reported "COPY OFF cannot be clicked to turn on" bug traced to
    exactly one root cause: UpdateSniperEngineRequest.copy_trading_enabled
    (app/routers/sniper.py) had no Field(alias="copyTradingEnabled"),
    unlike every other camelCase-serialized field in this codebase's
    request/response models. The real frontend
    (SniperApp.tsx's toggle()) always sends {"copyTradingEnabled": ...}
    — that JSON key never bound to the snake_case field, so
    GameState.update_sniper_engine_config()'s `if copy_trading_enabled is
    not None` branch never fired and the toggle silently no-opped."""

    def test_camel_case_copy_trading_enabled_key_populates_the_field(self) -> None:
        from app.routers.sniper import UpdateSniperEngineRequest

        payload = UpdateSniperEngineRequest.model_validate({"copyTradingEnabled": True})
        assert payload.copy_trading_enabled is True

    def test_snake_case_key_still_works_too(self) -> None:
        from app.routers.sniper import UpdateSniperEngineRequest

        payload = UpdateSniperEngineRequest.model_validate({"copy_trading_enabled": True})
        assert payload.copy_trading_enabled is True

    def test_omitted_field_defaults_to_none_not_false(self) -> None:
        from app.routers.sniper import UpdateSniperEngineRequest

        payload = UpdateSniperEngineRequest.model_validate({"turbo": True})
        assert payload.copy_trading_enabled is None


def _pnl_trade(trade_id: str, closed_at: str, pnl_sol: float, symbol: str = "X") -> SniperTrade:
    return SniperTrade(
        id=trade_id, mint="m", symbol=symbol, openedAt=closed_at, closedAt=closed_at, entryPrice=1.0, exitPrice=1.0 + pnl_sol,
        stopPrice=0.8, targetPrice=1.5, sizeSol=1.0, riskSol=0.1, rMultiple=pnl_sol / 0.1, pnlSol=pnl_sol,
        maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit",
        failureCodes=[], thesis="x", thesisValidated=True,
    )


class TestBuildSniperPnlHistory:
    """"Terminal 2.2" directive, Part X/XI — the real, oldest-first
    cumulative realized P&L curve, built fresh from the same
    trade_history build_engine_status_read() already reads for the
    "Performance (Today)" card. Realized-only: no unrealized/equity
    component, no interpolation, no fabricated points."""

    def test_empty_history_yields_empty_points(self) -> None:
        assert build_sniper_pnl_history([]) == []

    def test_single_trade_yields_one_point_with_matching_cumulative(self) -> None:
        trade = _pnl_trade("t1", "2026-01-01T00:00:00+00:00", 0.5)
        points = build_sniper_pnl_history([trade])
        assert len(points) == 1
        assert points[0].trade_id == "t1"
        assert points[0].realized_pnl_sol == 0.5
        assert points[0].cumulative_realized_pnl_sol == 0.5

    def test_cumulative_sum_accrues_across_wins_and_losses_in_time_order(self) -> None:
        trades = [
            _pnl_trade("t3", "2026-01-03T00:00:00+00:00", -0.2),
            _pnl_trade("t1", "2026-01-01T00:00:00+00:00", 0.5),
            _pnl_trade("t2", "2026-01-02T00:00:00+00:00", 0.3),
        ]
        points = build_sniper_pnl_history(trades)
        # Re-ordered oldest-first by closedAt, regardless of input order.
        assert [p.trade_id for p in points] == ["t1", "t2", "t3"]
        assert [p.cumulative_realized_pnl_sol for p in points] == [0.5, 0.8, 0.6]

    def test_matches_the_same_sum_build_engine_status_read_uses_for_todays_pnl(self) -> None:
        """The Performance (Today) card and the P&L chart must never
        silently disagree — both read the exact same trade_history."""
        from datetime import datetime, timezone

        from app.memecoin_sniper import build_engine_status_read

        today_iso = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        trades = [_pnl_trade("t1", today_iso, 0.4), _pnl_trade("t2", today_iso, -0.1)]
        status = build_engine_status_read(
            SniperEngineConfig(), SniperRiskState(), [], trades, today_start_iso=today_iso,
        )
        points = build_sniper_pnl_history(trades)
        assert points[-1].cumulative_realized_pnl_sol == status.today_pnl_sol

    def test_never_includes_an_unrealized_or_equity_field(self) -> None:
        """This is a realized-only curve — it must not silently gain a
        mark-to-market/equity field later without an explicit schema
        change (which would be its own reviewed decision, not a default)."""
        point = build_sniper_pnl_history([_pnl_trade("t1", "2026-01-01T00:00:00+00:00", 0.1)])[0]
        assert set(point.model_dump().keys()) == {"closed_at", "trade_id", "symbol", "realized_pnl_sol", "cumulative_realized_pnl_sol"}
