"""Covers app/travel_mode.py — Design Bible Chapter 73.5, Mobile Command
Center & Remote Operations. Travel Mode composes with Chapter 75's own
derived-override seam rather than inventing a fourth tightening
mechanic — every test here checks that composition, never a fabricated
standalone posture. See the module's own docstring for the full honesty
boundary.
"""
from __future__ import annotations

from app.portfolio import default_portfolio
from app.risk_engine import default_risk_limits
from app.schemas import CeoDecisionRecord, GatekeeperRejection, MemoryRecord, PaperTrade, RiskWarning, TravelModeSettings, TravelModeState
from app.travel_mode import (
    SETTINGS_PCT_CEILING,
    SETTINGS_PCT_FLOOR,
    TRAVEL_MODE_CONFIDENCE_BONUS,
    activate_travel_mode,
    apply_travel_mode_tightening,
    deactivate_travel_mode,
    generate_travel_mode_briefing,
    should_auto_activate,
    travel_mode_confidence_bonus,
    update_travel_mode_settings,
)


def _state(**overrides: object) -> TravelModeState:
    base = TravelModeState()
    return base.model_copy(update=overrides) if overrides else base


class TestActivateDeactivate:
    def test_manual_activation_sets_real_fields(self) -> None:
        updated, memory = activate_travel_mode(_state(), source="manual", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=1000)
        assert updated.active is True
        assert updated.activation_source == "manual"
        assert updated.activated_sim_minutes == 1000
        assert updated.deactivated_at is None
        assert memory.category == "alert"
        assert memory.title == "Travel Mode activated"
        assert "manually activated" in memory.body

    def test_auto_activation_names_the_real_inactivity_threshold(self) -> None:
        state = _state(settings=TravelModeSettings(autoActivateAfterMinutes=90))
        _updated, memory = activate_travel_mode(state, source="auto_inactivity", now_iso="2026-01-01T00:00:00Z", now_sim_minutes=1000)
        assert "90 simulated minutes" in memory.body

    def test_deactivation_clears_active_and_source(self) -> None:
        active = _state(active=True, activation_source="manual", activated_at="2026-01-01T00:00:00Z")
        updated, memory = deactivate_travel_mode(active, now_iso="2026-01-02T00:00:00Z")
        assert updated.active is False
        assert updated.activation_source is None
        assert updated.deactivated_at == "2026-01-02T00:00:00Z"
        assert memory.title == "Travel Mode deactivated"


class TestSettingsClamping:
    def test_values_within_bounds_are_kept(self) -> None:
        updated = update_travel_mode_settings(_state(), {"position_size_cap_pct": 60.0})
        assert updated.settings.position_size_cap_pct == 60.0

    def test_values_above_ceiling_are_clamped(self) -> None:
        updated = update_travel_mode_settings(_state(), {"position_size_cap_pct": 200.0, "daily_risk_cap_pct": 999.0})
        assert updated.settings.position_size_cap_pct == SETTINGS_PCT_CEILING
        assert updated.settings.daily_risk_cap_pct == SETTINGS_PCT_CEILING

    def test_values_below_floor_are_clamped(self) -> None:
        updated = update_travel_mode_settings(_state(), {"position_size_cap_pct": 1.0})
        assert updated.settings.position_size_cap_pct == SETTINGS_PCT_FLOOR

    def test_auto_activate_minutes_are_clamped(self) -> None:
        updated = update_travel_mode_settings(_state(), {"auto_activate_after_minutes": 5000})
        assert updated.settings.auto_activate_after_minutes == 240

    def test_notification_sensitivity_passes_through(self) -> None:
        updated = update_travel_mode_settings(_state(), {"notification_sensitivity": "critical_only"})
        assert updated.settings.notification_sensitivity == "critical_only"


class TestTighteningComposesRatherThanDuplicates:
    def test_inactive_travel_mode_leaves_limits_untouched(self) -> None:
        limits = default_risk_limits()
        tightened = apply_travel_mode_tightening(limits, _state(active=False))
        assert tightened == limits

    def test_active_travel_mode_scales_by_the_ceo_configured_factors(self) -> None:
        limits = default_risk_limits()
        state = _state(active=True, settings=TravelModeSettings(positionSizeCapPct=50.0, dailyRiskCapPct=50.0))
        tightened = apply_travel_mode_tightening(limits, state)
        assert tightened.risk_per_trade_pct == round(limits.risk_per_trade_pct * 0.5, 2)
        assert tightened.max_position_pct == round(limits.max_position_pct * 0.5, 2)

    def test_max_open_positions_is_halved_with_a_floor_of_one(self) -> None:
        limits = default_risk_limits().model_copy(update={"max_open_positions": 1})
        tightened = apply_travel_mode_tightening(limits, _state(active=True))
        assert tightened.max_open_positions == 1

    def test_confidence_bonus_is_zero_when_inactive(self) -> None:
        assert travel_mode_confidence_bonus(_state(active=False)) == 0.0

    def test_confidence_bonus_is_the_disclosed_constant_when_active(self) -> None:
        assert travel_mode_confidence_bonus(_state(active=True)) == TRAVEL_MODE_CONFIDENCE_BONUS


class TestShouldAutoActivate:
    def test_never_fires_when_already_active(self) -> None:
        state = _state(active=True, settings=TravelModeSettings(autoActivateEnabled=True, autoActivateAfterMinutes=60))
        assert should_auto_activate(state, last_ceo_decision_sim_minutes=0, now_sim_minutes=1000) is False

    def test_never_fires_when_the_ceo_never_opted_in(self) -> None:
        state = _state(settings=TravelModeSettings(autoActivateEnabled=False))
        assert should_auto_activate(state, last_ceo_decision_sim_minutes=0, now_sim_minutes=100000) is False

    def test_never_fires_with_no_real_decision_timestamp_on_record(self) -> None:
        state = _state(settings=TravelModeSettings(autoActivateEnabled=True))
        assert should_auto_activate(state, last_ceo_decision_sim_minutes=None, now_sim_minutes=100000) is False

    def test_fires_once_the_real_inactivity_threshold_is_crossed(self) -> None:
        state = _state(settings=TravelModeSettings(autoActivateEnabled=True, autoActivateAfterMinutes=60))
        assert should_auto_activate(state, last_ceo_decision_sim_minutes=0, now_sim_minutes=60) is True

    def test_does_not_fire_before_the_threshold(self) -> None:
        state = _state(settings=TravelModeSettings(autoActivateEnabled=True, autoActivateAfterMinutes=60))
        assert should_auto_activate(state, last_ceo_decision_sim_minutes=0, now_sim_minutes=59) is False


class TestReturnToOperationsBriefing:
    def _active_state(self) -> TravelModeState:
        return _state(active=True, activation_source="manual", activated_at="2026-01-01T00:00:00Z", activated_sim_minutes=1000)

    def test_summary_names_real_zero_activity_honestly(self) -> None:
        briefing = generate_travel_mode_briefing(
            self._active_state(),
            now_sim_minutes=1500,
            now_iso="2026-01-02T00:00:00Z",
            memory=[],
            ceo_decisions=[],
            gatekeeper_rejections=[],
            risk_warnings=[],
            portfolio=default_portfolio(),
            briefing_id="briefing-1",
        )
        assert briefing.decisions_resolved == 0
        assert briefing.gatekeeper_rejections == 0
        assert briefing.critical_risk_warnings == 0
        assert briefing.circuit_breaker_tier_changes == 0
        assert briefing.realized_pnl == 0.0
        assert "500 simulated minute(s)" in briefing.summary

    def test_counts_only_decisions_resolved_after_activation(self) -> None:
        before = CeoDecisionRecord(
            id="d1", proposalId="p1", symbol="AAPL", category="stock", aiRecommendation="buy", ceoDecision="buy",
            agreedWithAi=True, createdAt="2025-12-31T00:00:00Z", resolvedAt="2025-12-31T23:00:00Z",
        )
        after = CeoDecisionRecord(
            id="d2", proposalId="p2", symbol="MSFT", category="stock", aiRecommendation="sell", ceoDecision="sell",
            agreedWithAi=True, createdAt="2026-01-01T12:00:00Z", resolvedAt="2026-01-01T12:00:00Z",
        )
        briefing = generate_travel_mode_briefing(
            self._active_state(), now_sim_minutes=1500, now_iso="2026-01-02T00:00:00Z", memory=[],
            ceo_decisions=[before, after], gatekeeper_rejections=[], risk_warnings=[], portfolio=default_portfolio(),
            briefing_id="briefing-2",
        )
        assert briefing.decisions_resolved == 1

    def test_counts_only_critical_risk_warnings_in_the_activation_window(self) -> None:
        critical_after = RiskWarning(id="w1", symbol="AAPL", severity="critical", message="x", createdAt="2026-01-01T12:00:00Z")
        info_after = RiskWarning(id="w2", symbol="AAPL", severity="info", message="x", createdAt="2026-01-01T12:00:00Z")
        briefing = generate_travel_mode_briefing(
            self._active_state(), now_sim_minutes=1500, now_iso="2026-01-02T00:00:00Z", memory=[],
            ceo_decisions=[], gatekeeper_rejections=[], risk_warnings=[critical_after, info_after], portfolio=default_portfolio(),
            briefing_id="briefing-3",
        )
        assert briefing.critical_risk_warnings == 1

    def test_counts_only_circuit_breaker_memory_entries_in_the_window(self) -> None:
        tier_change = MemoryRecord(id="m1", category="alert", title="Daily Circuit Breaker escalated to tier1", body="x", timestamp="2026-01-01T12:00:00Z")
        unrelated = MemoryRecord(id="m2", category="alert", title="Trading Mode changed", body="x", timestamp="2026-01-01T12:00:00Z")
        briefing = generate_travel_mode_briefing(
            self._active_state(), now_sim_minutes=1500, now_iso="2026-01-02T00:00:00Z", memory=[tier_change, unrelated],
            ceo_decisions=[], gatekeeper_rejections=[], risk_warnings=[], portfolio=default_portfolio(),
            briefing_id="briefing-4",
        )
        assert briefing.circuit_breaker_tier_changes == 1

    def test_realized_pnl_sums_only_trades_closed_in_the_sim_minute_window(self) -> None:
        portfolio = default_portfolio()
        in_window = PaperTrade(
            id="t1", symbol="AAPL", side="buy", quantity=10.0, entryPrice=100.0, exitPrice=110.0, pnl=100.0, pnlPct=10.0,
            durationMinutes=60, confidence=70.0, reason="x", marketConditions="x", openedAt="2026-01-01T00:00:00Z",
            closedAt="2026-01-01T01:00:00Z", openedSimMinutes=1100, closedSimMinutes=1200,
        )
        out_of_window = in_window.model_copy(update={"id": "t2", "closed_sim_minutes": 500, "pnl": 9999.0})
        portfolio = portfolio.model_copy(update={"trade_history": [in_window, out_of_window]})
        briefing = generate_travel_mode_briefing(
            self._active_state(), now_sim_minutes=1500, now_iso="2026-01-02T00:00:00Z", memory=[],
            ceo_decisions=[], gatekeeper_rejections=[], risk_warnings=[], portfolio=portfolio,
            briefing_id="briefing-5",
        )
        assert briefing.realized_pnl == 100.0

    def test_gatekeeper_rejections_are_windowed_by_sim_minutes_not_iso_time(self) -> None:
        in_window = GatekeeperRejection(
            id="g1", proposalId="p1", symbol="AAPL", ceoChoice="buy", priceAtRejection=100.0, rejectedSimMinutes=1200, createdAt="2026-01-01T00:00:00Z",
        )
        out_of_window = in_window.model_copy(update={"id": "g2", "rejected_sim_minutes": 500})
        briefing = generate_travel_mode_briefing(
            self._active_state(), now_sim_minutes=1500, now_iso="2026-01-02T00:00:00Z", memory=[],
            ceo_decisions=[], gatekeeper_rejections=[in_window, out_of_window], risk_warnings=[], portfolio=default_portfolio(),
            briefing_id="briefing-6",
        )
        assert briefing.gatekeeper_rejections == 1
