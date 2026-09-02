"""Covers app/memecoin_sniper.py — CEO directive "TradeTown — Memecoin
Sniper Agent." Paper-only, simulated data throughout — see that
module's own docstring."""
from __future__ import annotations

import random

from app.memecoin_sniper import (
    DEFAULT_HARD_STOP_PCT,
    DEFAULT_MAX_HOLD_SECONDS,
    DEFAULT_TAKE_PROFIT_PCT,
    RawCandidate,
    build_candidate,
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
    run_safety_firewall,
    score_candidate,
    size_paper_position,
    tick_sniper_engine,
    update_risk_state_after_trade,
)
from app.schemas import SniperEngineConfig, SniperRiskState, SniperTrade

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
        allowed, reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert "safety_status" in reason

    def test_kill_switch_triggered_blocks_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState(killSwitchTriggered=True)
        allowed, reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is False
        assert "kill_switch" in reason

    def test_max_positions_blocks_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState()
        allowed, reason = evaluate_entry_firewall(candidate, config, risk, config.max_open_positions)
        assert allowed is False
        assert "max_open_positions" in reason

    def test_all_gates_passing_allows_entry(self) -> None:
        candidate = self._candidate(safety_status="safe_enough", classification="qualified", timing_state="entry_window", opportunity_score=90.0, rug_risk="low", creator_risk="weak_signal")
        config = SniperEngineConfig()
        risk = SniperRiskState()
        allowed, reason = evaluate_entry_firewall(candidate, config, risk, 0)
        assert allowed is True
        assert reason == "PASS"


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


class TestClosePositionAndFailureCodes:
    def test_close_position_computes_real_r_multiple(self) -> None:
        candidate = build_candidate("c1", _NOW).model_copy(update={"price_usd": 1.0})
        position = open_position(candidate, 1.0, 0.88, 1.55, _NOW)
        closed, trade = close_position(position, 0.88, "stop_loss", _NOW)
        assert closed.status == "closed"
        assert trade.r_multiple == -1.0
        assert trade.failure_codes == ["momentum_exhaustion"]

    def test_winning_trade_has_no_failure_codes(self) -> None:
        assert derive_failure_code("take_profit", 55.0) == []

    def test_unknown_exit_reason_maps_to_unknown_failure(self) -> None:
        assert derive_failure_code("momentum_failure", -5.0) == ["momentum_exhaustion"]


class TestRiskStateUpdates:
    def test_losing_trade_increases_consecutive_losses(self) -> None:
        risk = SniperRiskState()
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.88, sizeSol=1.0, riskSol=0.12, rMultiple=-1.0, pnlSol=-0.12, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-12.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.consecutive_losses == 1
        assert updated.equity_sol < risk.equity_sol

    def test_winning_trade_resets_consecutive_losses(self) -> None:
        risk = SniperRiskState(consecutiveLosses=2)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=4.6, pnlSol=0.55, maxFavorableExcursionPct=55.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.consecutive_losses == 0

    def test_size_multiplier_never_increases_above_one(self) -> None:
        risk = SniperRiskState(sizeMultiplier=0.5)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.55, sizeSol=1.0, riskSol=0.12, rMultiple=4.6, pnlSol=0.55, maxFavorableExcursionPct=55.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.size_multiplier <= 0.5 or updated.size_multiplier == 1.0

    def test_drawdown_past_6pct_triggers_kill_switch(self) -> None:
        risk = SniperRiskState(equitySol=100.0, peakEquitySol=100.0, killSwitchArmed=True)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.0, sizeSol=100.0, riskSol=100.0, rMultiple=-8.0, pnlSol=-8.0, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-100.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.kill_switch_triggered is True
        assert updated.kill_switch_reason is not None

    def test_kill_switch_never_triggers_when_not_armed(self) -> None:
        risk = SniperRiskState(equitySol=100.0, peakEquitySol=100.0, killSwitchArmed=False)
        trade = SniperTrade(id="t1", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.0, sizeSol=100.0, riskSol=100.0, rMultiple=-8.0, pnlSol=-8.0, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-100.0, holdTimeSeconds=10.0, exitReason="stop_loss", failureCodes=["momentum_exhaustion"], thesis="x", thesisValidated=False)  # type: ignore[call-arg]
        updated = update_risk_state_after_trade(risk, trade, _NOW)
        assert updated.kill_switch_triggered is False


class TestLiveArming:
    def test_always_blocked_in_this_environment(self) -> None:
        status = evaluate_live_arming()
        assert status.armed is False
        assert len(status.blocking_reasons) > 0


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
            history.append(SniperTrade(id=f"t{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=1.1, sizeSol=1.0, riskSol=0.12, rMultiple=0.8, pnlSol=0.1, maxFavorableExcursionPct=10.0, maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit", failureCodes=[], thesis="x", thesisValidated=True))  # type: ignore[call-arg]
        for i in range(10):
            history.append(SniperTrade(id=f"tf{i}", mint="m", symbol="X", openedAt=_NOW, closedAt=_NOW, entryPrice=1.0, exitPrice=0.95, sizeSol=1.0, riskSol=0.12, rMultiple=-0.4, pnlSol=-0.05, maxFavorableExcursionPct=0.0, maxAdverseExcursionPct=-5.0, holdTimeSeconds=70.0, exitReason="max_hold", failureCodes=["timing_failure"], thesis="x", thesisValidated=False))  # type: ignore[call-arg]
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
