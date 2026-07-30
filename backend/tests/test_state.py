"""Covers GameState.apply_client_save() — v0.7 Save Architecture Redesign.
Pins the exact contract this whole redesign depends on: only
player/settings/dialogue_history are ever taken from a client save
request, and MAX_DIALOGUE_HISTORY still truncates server-side regardless
of what a (possibly stale, un-updated) client sends. Each test builds its
own GameState() rather than importing the process-wide app.state.game_state
singleton, so runs stay isolated (same convention as test_time_advance.py).
"""
from __future__ import annotations

import asyncio

from app.schemas import ClientSaveRequest, DialogueHistoryEntry, EntityTransform, SettingsState
from app.state import MAX_DIALOGUE_HISTORY, GameState


def _client_request(*, x: float = 999.0, dialogue_lines: int = 0) -> ClientSaveRequest:
    return ClientSaveRequest(
        player=EntityTransform(scene="BrainRoomScene", x=x, y=42.0, facing="up"),
        settings=SettingsState(
            musicVolume=0.1,
            sfxVolume=0.2,
            autosaveIntervalSec=30,
            showFps=True,
            operatingMode="executive",
            companyPriority="research",
            workMode="rest",
        ),
        dialogueHistory=[
            DialogueHistoryEntry(id=f"line-{i}", speaker="sage", line=f"line {i}", timestamp="2026-01-01T00:00:00+00:00") for i in range(dialogue_lines)
        ],
    )


class TestApplyClientSave:
    def test_player_settings_and_dialogue_history_come_from_the_client(self) -> None:
        state = GameState()
        saved = asyncio.run(state.apply_client_save(_client_request(x=123.0, dialogue_lines=2)))
        assert saved.player.x == 123.0
        assert saved.player.scene == "BrainRoomScene"
        assert saved.settings.operating_mode == "executive"
        assert saved.settings.work_mode == "rest"
        assert len(saved.dialogue_history) == 2

    def test_everything_else_stays_server_authoritative_and_untouched_by_the_request(self) -> None:
        state = GameState()
        before = state.data
        saved = asyncio.run(state.apply_client_save(_client_request()))
        # ClientSaveRequest structurally cannot carry agents/research/decisions/
        # etc. at all — this asserts the real server-authoritative data (whatever
        # GameState started with) survives the call completely unchanged.
        assert saved.agents == before.agents
        assert saved.research == before.research
        assert saved.trade_proposals == before.trade_proposals
        assert saved.time == before.time

    def test_dialogue_history_is_truncated_to_the_same_server_side_cap(self) -> None:
        state = GameState()
        saved = asyncio.run(state.apply_client_save(_client_request(dialogue_lines=MAX_DIALOGUE_HISTORY + 25)))
        assert len(saved.dialogue_history) == MAX_DIALOGUE_HISTORY
        # The most RECENT lines survive, not the oldest — a save should never
        # silently drop what the player just said in favor of ancient history.
        assert saved.dialogue_history[-1].line == f"line {MAX_DIALOGUE_HISTORY + 25 - 1}"

    def test_updated_at_advances_on_every_call(self) -> None:
        state = GameState()
        before = state.data.updated_at
        saved = asyncio.run(state.apply_client_save(_client_request()))
        assert saved.updated_at != before


# v0.7 Feature 49 — Daily Trading Objectives. The first real CEO write
# path for RiskLimits.
class TestUpdateRiskLimits:
    def test_updates_only_the_provided_fields(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(daily_profit_target_pct=5.0))
        assert error is None
        assert saved.risk_limits.daily_profit_target_pct == 5.0
        assert saved.risk_limits.max_daily_loss_pct == before.max_daily_loss_pct
        assert saved.risk_limits.max_trades_per_day == before.max_trades_per_day

    def test_updates_all_five_fields_at_once(self) -> None:
        state = GameState()
        saved, error = asyncio.run(
            state.update_risk_limits(daily_profit_target_pct=4.0, max_daily_loss_pct=6.0, max_trades_per_day=3, risk_per_trade_pct=1.5, max_open_positions=5)
        )
        assert error is None
        assert saved.risk_limits.daily_profit_target_pct == 4.0
        assert saved.risk_limits.max_daily_loss_pct == 6.0
        assert saved.risk_limits.max_trades_per_day == 3
        assert saved.risk_limits.risk_per_trade_pct == 1.5
        assert saved.risk_limits.max_open_positions == 5

    def test_rejects_a_non_positive_value(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(max_trades_per_day=0))
        assert error is not None
        assert saved.risk_limits == before

    def test_rejects_a_call_with_no_fields(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits())
        assert error == "No risk limit changes were provided."
        assert saved is state.data

    def test_extra_fields_on_the_wire_are_ignored_not_rejected(self) -> None:
        """ClientSaveRequest inherits CamelModel's default extra="ignore", so
        an older client still POSTing a full legacy GameSaveState-shaped body
        stays accepted — see docs/API.md's POST /api/save section."""
        payload = ClientSaveRequest.model_validate(
            {
                "player": {"scene": "LobbyScene", "x": 1.0, "y": 2.0, "facing": "down"},
                "settings": SettingsState(
                    musicVolume=0.5,
                    sfxVolume=0.5,
                    autosaveIntervalSec=60,
                    showFps=False,
                ).model_dump(by_alias=True),
                "dialogueHistory": [],
                "agents": {"echo": {"fabricated": "should be ignored, not rejected"}},
                "decisions": ["fabricated", "should be ignored"],
            }
        )
        assert payload.player.scene == "LobbyScene"
