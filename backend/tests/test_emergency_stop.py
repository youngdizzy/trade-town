"""Covers app/emergency_stop.py's pure state-transition functions directly
— app/state.py's TestActivateAndResumeEmergencyStop and
TestSubmitCeoDecisionEmergencyStopGuard cover the full lock-guarded,
memory-logging integration; these tests pin the transition logic itself.
"""
from __future__ import annotations

from app.emergency_stop import activate_emergency_stop, resume_trading
from app.schemas import EmergencyStopState


class TestActivateEmergencyStop:
    def test_activates_from_inactive(self) -> None:
        new_state, error = activate_emergency_stop(EmergencyStopState(), now_iso="2026-01-01T00:00:00+00:00")
        assert error is None
        assert new_state.active is True
        assert new_state.activated_at == "2026-01-01T00:00:00+00:00"

    def test_rejects_activating_when_already_active(self) -> None:
        already_active = EmergencyStopState(active=True, activatedAt="2026-01-01T00:00:00+00:00")
        new_state, error = activate_emergency_stop(already_active, now_iso="2026-01-02T00:00:00+00:00")
        assert error is not None
        assert new_state == already_active


class TestResumeTrading:
    def test_resumes_from_active(self) -> None:
        active = EmergencyStopState(active=True, activatedAt="2026-01-01T00:00:00+00:00")
        new_state, error = resume_trading(active)
        assert error is None
        assert new_state.active is False
        assert new_state.activated_at is None

    def test_rejects_resuming_when_not_active(self) -> None:
        inactive = EmergencyStopState()
        new_state, error = resume_trading(inactive)
        assert error is not None
        assert new_state == inactive
