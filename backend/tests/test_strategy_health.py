"""Covers app/strategy_health.py — the Strategy Health State Machine."""
from __future__ import annotations

from app.strategy_health import RECOVERY_MIN_TRADE_COUNT, RISK_SCALING_FACTOR, evaluate_health_transition


def _clean() -> dict[str, str]:
    return {"performance": "normal", "execution": "normal", "risk": "normal", "regime": "normal"}


def test_no_drift_signal_stays_healthy_with_no_transition_recorded() -> None:
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert state.state == "healthy"
    assert state.risk_scaling_factor == 1.0
    assert state.transitions == []


def test_single_watch_category_transitions_to_watch() -> None:
    severities = {**_clean(), "performance": "watch"}
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=["d1"])
    assert state.state == "watch"
    assert state.risk_scaling_factor == RISK_SCALING_FACTOR["watch"]
    assert len(state.transitions) == 1
    assert state.transitions[0].previous_state == "healthy"
    assert state.transitions[0].new_state == "watch"
    assert state.transitions[0].drift_event_ids == ["d1"]


def test_two_watch_categories_transitions_to_degraded() -> None:
    severities = {**_clean(), "performance": "watch", "execution": "watch"}
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert state.state == "degraded"


def test_single_critical_category_transitions_to_critical() -> None:
    severities = {**_clean(), "risk": "critical"}
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert state.state == "critical"
    assert state.risk_scaling_factor == RISK_SCALING_FACTOR["critical"]


def test_two_critical_categories_transitions_to_suspended() -> None:
    severities = {**_clean(), "risk": "critical", "performance": "critical"}
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert state.state == "suspended"
    assert state.risk_scaling_factor == 0.0


def test_clean_evidence_from_non_healthy_state_enters_recovering_never_healthy_directly() -> None:
    critical = evaluate_health_transition(current=None, strategy_id="s1", current_severities={**_clean(), "risk": "critical"}, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert critical.state == "critical"
    recovering = evaluate_health_transition(current=critical, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=2, triggering_drift_event_ids=[])
    assert recovering.state == "recovering"
    assert recovering.recovery_trade_count == 0


def test_recovering_requires_minimum_real_trade_sample_never_a_single_win() -> None:
    critical = evaluate_health_transition(current=None, strategy_id="s1", current_severities={**_clean(), "risk": "critical"}, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    recovering = evaluate_health_transition(current=critical, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=2, triggering_drift_event_ids=[])
    # One single winning trade is NOT enough.
    still_recovering = evaluate_health_transition(current=recovering, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=1, sim_day=3, triggering_drift_event_ids=[])
    assert still_recovering.state == "recovering"
    assert still_recovering.recovery_trade_count == 1

    # Feed it up to just below the real floor.
    state = still_recovering
    for day in range(4, 3 + RECOVERY_MIN_TRADE_COUNT - 1):
        state = evaluate_health_transition(current=state, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=1, sim_day=day, triggering_drift_event_ids=[])
    assert state.state == "recovering"
    assert state.recovery_trade_count == RECOVERY_MIN_TRADE_COUNT - 1

    healthy = evaluate_health_transition(current=state, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=1, sim_day=100, triggering_drift_event_ids=[])
    assert healthy.state == "healthy"
    assert healthy.risk_scaling_factor == 1.0


def test_relapse_during_recovering_drops_back_to_matching_ladder_state_not_a_special_failure() -> None:
    critical = evaluate_health_transition(current=None, strategy_id="s1", current_severities={**_clean(), "risk": "critical"}, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    recovering = evaluate_health_transition(current=critical, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=2, triggering_drift_event_ids=[])
    relapsed = evaluate_health_transition(current=recovering, strategy_id="s1", current_severities={**_clean(), "performance": "watch"}, new_trades_closed_this_tick=0, sim_day=3, triggering_drift_event_ids=[])
    assert relapsed.state == "watch"
    assert relapsed.recovery_trade_count == 0


def test_health_never_grants_extra_risk_factor_never_exceeds_one() -> None:
    for state_name, factor in RISK_SCALING_FACTOR.items():
        assert 0.0 <= factor <= 1.0, f"{state_name} factor {factor} is outside [0,1]"


def test_unchanged_state_with_no_new_trades_is_a_true_no_op() -> None:
    healthy = evaluate_health_transition(current=None, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    still_healthy = evaluate_health_transition(current=healthy, strategy_id="s1", current_severities=_clean(), new_trades_closed_this_tick=0, sim_day=2, triggering_drift_event_ids=[])
    assert still_healthy is healthy


def test_deterministic_same_inputs_same_output() -> None:
    severities = {**_clean(), "performance": "watch"}
    a = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=["d1"])
    b = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=["d1"])
    assert a.state == b.state
    assert a.risk_scaling_factor == b.risk_scaling_factor


def test_every_transition_carries_real_evidence_never_empty() -> None:
    severities = {**_clean(), "performance": "watch"}
    state = evaluate_health_transition(current=None, strategy_id="s1", current_severities=severities, new_trades_closed_this_tick=0, sim_day=1, triggering_drift_event_ids=[])
    assert len(state.transitions) == 1
    assert state.transitions[0].evidence
    assert state.transitions[0].trigger
