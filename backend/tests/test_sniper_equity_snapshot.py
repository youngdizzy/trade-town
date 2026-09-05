"""Covers "Equity Snapshot Telemetry 1.0" — the real, periodic
mark-to-market equity reading for the Memecoin Sniper
(app/memecoin_sniper.py::build_sniper_equity_snapshot /
append_sniper_equity_snapshot / sniper_equity_snapshot_id), plus its
wiring into app/nexus.py's real tick. Not a second P&L/portfolio engine
— both inputs (SniperRiskState.equity_sol, SniperPosition.pnl_sol) are
already real and already authoritative; this only combines and
timestamps them."""
from __future__ import annotations

import math

from app.memecoin_sniper import (
    append_sniper_equity_snapshot,
    build_sniper_equity_snapshot,
    sniper_equity_snapshot_id,
    update_risk_state_after_trade,
)
from app.nexus import MAX_SNIPER_EQUITY_SNAPSHOTS, tick as nexus_tick
from app.schemas import SniperEngineConfig, SniperPosition, SniperRiskState, SniperTrade
from app.state import default_state

_NOW = "2026-01-01T00:00:00+00:00"


def _position(*, pnl_sol: float, status: str = "open") -> SniperPosition:
    return SniperPosition(
        id=f"pos-{pnl_sol}", mint="m", symbol="MEWPEPE", entryPrice=0.0001, currentPrice=0.00012, sizeSol=1.0,
        stopPrice=0.000088, targetPrice=0.000155, openedAt=_NOW, status=status, pnlSol=pnl_sol, pnlPct=pnl_sol * 100, riskSol=0.012,  # type: ignore[arg-type]
    )


def _trade(*, pnl_sol: float) -> SniperTrade:
    return SniperTrade(
        id="t1", mint="m", symbol="MEWPEPE", openedAt=_NOW, closedAt=_NOW, entryPrice=0.0001,
        exitPrice=0.00012 if pnl_sol >= 0 else 0.00008, stopPrice=0.000088, targetPrice=0.000155, sizeSol=1.0,
        riskSol=0.012, rMultiple=pnl_sol / 0.012 if pnl_sol else 0.0, pnlSol=pnl_sol, maxFavorableExcursionPct=0.0,
        maxAdverseExcursionPct=0.0, holdTimeSeconds=10.0, exitReason="take_profit" if pnl_sol >= 0 else "stop_loss", thesis="x",
    )


class TestSniperEquitySnapshotId:
    def test_deterministic_not_random(self):
        assert sniper_equity_snapshot_id(1, 2, 3) == sniper_equity_snapshot_id(1, 2, 3)

    def test_distinct_instants_get_distinct_ids(self):
        assert sniper_equity_snapshot_id(1, 2, 3) != sniper_equity_snapshot_id(1, 2, 4)

    def test_zero_padded_for_stable_lexical_ordering_within_reasonable_ranges(self):
        assert sniper_equity_snapshot_id(1, 2, 3) == "00001-02-03"


class TestBuildSniperEquitySnapshot:
    """Part XVIII differential checks A-J (subset directly testable at
    this pure-function level; restart/save-load are covered separately
    below)."""

    def test_a_no_positions_equity_equals_realized_only(self):
        risk = SniperRiskState(equitySol=10.0)
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, [], sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.realized_equity_sol == 10.0
        assert snap.unrealized_pnl_sol == 0.0
        assert snap.total_equity_sol == 10.0
        assert snap.open_position_count == 0

    def test_b_one_profitable_open_position_adds_to_equity(self):
        risk = SniperRiskState(equitySol=100.0)
        positions = [_position(pnl_sol=1.0)]
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, positions, sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.realized_equity_sol == 100.0
        assert snap.unrealized_pnl_sol == 1.0
        assert snap.total_equity_sol == 101.0
        assert snap.open_position_count == 1

    def test_c_one_losing_open_position_subtracts_from_equity(self):
        risk = SniperRiskState(equitySol=100.0)
        positions = [_position(pnl_sol=-2.0)]
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, positions, sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.unrealized_pnl_sol == -2.0
        assert snap.total_equity_sol == 98.0

    def test_d_position_closes_profitably_realized_absorbs_it_no_double_count(self):
        """Starting equity 100 SOL, open position +1 SOL unrealized ->
        equity 101. Trade closes at +1 SOL: risk_state.equity_sol becomes
        101 (realized), and the position no longer appears in the open
        list, so unrealized returns to 0 — total stays ~101, never 102."""
        risk_before = SniperRiskState(equitySol=100.0)
        before = build_sniper_equity_snapshot(SniperEngineConfig(), risk_before, [_position(pnl_sol=1.0)], sim_day=1, sim_hour=0, sim_minute=0)
        assert before.total_equity_sol == 101.0

        trade = _trade(pnl_sol=1.0)
        risk_after = update_risk_state_after_trade(risk_before, trade, _NOW)
        after = build_sniper_equity_snapshot(SniperEngineConfig(), risk_after, [], sim_day=1, sim_hour=0, sim_minute=5)
        assert after.realized_equity_sol == 101.0
        assert after.unrealized_pnl_sol == 0.0
        assert after.total_equity_sol == 101.0

    def test_e_position_closes_at_a_loss(self):
        risk_before = SniperRiskState(equitySol=100.0)
        trade = _trade(pnl_sol=-3.0)
        risk_after = update_risk_state_after_trade(risk_before, trade, _NOW)
        after = build_sniper_equity_snapshot(SniperEngineConfig(), risk_after, [], sim_day=1, sim_hour=0, sim_minute=5)
        assert after.total_equity_sol == 97.0

    def test_f_multiple_open_positions_sum_correctly(self):
        risk = SniperRiskState(equitySol=50.0)
        positions = [_position(pnl_sol=1.0), _position(pnl_sol=-0.5), _position(pnl_sol=2.0)]
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, positions, sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.unrealized_pnl_sol == 2.5
        assert snap.total_equity_sol == 52.5
        assert snap.open_position_count == 3

    def test_g_zero_pnl(self):
        risk = SniperRiskState(equitySol=10.0)
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, [_position(pnl_sol=0.0)], sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.total_equity_sol == 10.0

    def test_h_negative_total_equity_is_not_clamped_or_hidden(self):
        """A real, honest reading even if the account is genuinely
        underwater — never silently floored at 0."""
        risk = SniperRiskState(equitySol=1.0)
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, [_position(pnl_sol=-5.0)], sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.total_equity_sol == -4.0

    def test_closed_positions_never_contribute_to_unrealized(self):
        risk = SniperRiskState(equitySol=10.0)
        positions = [_position(pnl_sol=5.0, status="closed"), _position(pnl_sol=1.0, status="open")]
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), risk, positions, sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.unrealized_pnl_sol == 1.0

    def test_mode_mirrors_real_engine_config_mode(self):
        risk = SniperRiskState()
        snap = build_sniper_equity_snapshot(SniperEngineConfig(mode="dry_run"), risk, [], sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.mode == "dry_run"

    def test_data_provenance_always_simulated(self):
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(), [], sim_day=1, sim_hour=0, sim_minute=0)
        assert snap.data_provenance == "simulated"

    def test_equity_is_never_nan_or_infinite(self):
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(equitySol=0.0), [], sim_day=1, sim_hour=0, sim_minute=0)
        assert not math.isnan(snap.total_equity_sol)
        assert not math.isinf(snap.total_equity_sol)

    def test_snapshot_fields_are_only_ever_real_inputs_no_fabricated_extras(self):
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(), [], sim_day=1, sim_hour=0, sim_minute=0)
        assert set(snap.model_dump().keys()) == {
            "id", "sim_day", "sim_hour", "sim_minute", "timestamp", "realized_equity_sol",
            "unrealized_pnl_sol", "total_equity_sol", "open_position_count", "mode", "data_provenance",
        }


class TestAppendSniperEquitySnapshot:
    def test_repeated_tick_same_identity_does_not_duplicate(self):
        snap = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(), [], sim_day=1, sim_hour=0, sim_minute=5)
        history = append_sniper_equity_snapshot([], snap, max_snapshots=100)
        history_again = append_sniper_equity_snapshot(history, snap, max_snapshots=100)
        assert len(history_again) == 1

    def test_distinct_ticks_both_appended_in_order(self):
        s1 = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(), [], sim_day=1, sim_hour=0, sim_minute=0)
        s2 = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(equitySol=11.0), [], sim_day=1, sim_hour=0, sim_minute=5)
        history = append_sniper_equity_snapshot([], s1, max_snapshots=100)
        history = append_sniper_equity_snapshot(history, s2, max_snapshots=100)
        assert [s.id for s in history] == [s1.id, s2.id]
        timestamps_are_ordered = all(history[i].sim_minute <= history[i + 1].sim_minute for i in range(len(history) - 1))
        assert timestamps_are_ordered

    def test_fifo_trimmed_at_cap(self):
        history: list = []
        for minute in range(5):
            snap = build_sniper_equity_snapshot(SniperEngineConfig(), SniperRiskState(), [], sim_day=1, sim_hour=0, sim_minute=minute)
            history = append_sniper_equity_snapshot(history, snap, max_snapshots=3)
        assert len(history) == 3
        assert [s.sim_minute for s in history] == [2, 3, 4]

    def test_real_max_snapshots_cap_is_a_positive_bounded_constant(self):
        assert 0 < MAX_SNIPER_EQUITY_SNAPSHOTS <= 100_000


class TestNexusWiring:
    """Wiring into the real app/nexus.py tick — confirms the snapshot is
    actually produced end-to-end, not just reachable as a standalone
    function."""

    def test_running_engine_produces_a_snapshot_on_a_real_tick(self):
        state = default_state().model_copy(update={"sniper_engine_config": SniperEngineConfig(status="paused")})  # type: ignore[arg-type]
        from app.schemas import TimeState

        new_time = TimeState(day=state.time.day, hour=state.time.hour, minute=state.time.minute + 5)
        result = nexus_tick(state, new_time, 5)
        assert len(result.sniper_equity_history) == 1
        assert result.sniper_equity_history[0].sim_minute == new_time.minute

    def test_stopped_engine_produces_no_snapshot(self):
        state = default_state().model_copy(update={"sniper_engine_config": SniperEngineConfig(status="stopped")})  # type: ignore[arg-type]
        from app.schemas import TimeState

        new_time = TimeState(day=state.time.day, hour=state.time.hour, minute=state.time.minute + 5)
        result = nexus_tick(state, new_time, 5)
        assert result.sniper_equity_history == []

    def test_repeated_identical_tick_does_not_duplicate_via_nexus(self):
        """Part XV — feeding the same (state, new_time) into nexus.tick()
        twice must not create two snapshots for the same simulated
        instant, even though this never happens in normal monotonic
        real usage (see sniper_equity_snapshot_id's own docstring)."""
        state = default_state().model_copy(update={"sniper_engine_config": SniperEngineConfig(status="paused")})  # type: ignore[arg-type]
        from app.schemas import TimeState

        new_time = TimeState(day=state.time.day, hour=state.time.hour, minute=state.time.minute + 5)
        once = nexus_tick(state, new_time, 5)
        twice = nexus_tick(once, new_time, 0)
        assert len(twice.sniper_equity_history) == 1

    def test_restart_then_next_tick_appends_not_duplicates(self):
        """Simulates a save/restart cycle: rebuild GameSaveState fresh
        from the persisted sniper_equity_history (as loading a save
        would), then advance one more real tick — must append exactly
        one new snapshot, never re-create the already-persisted one."""
        state = default_state().model_copy(update={"sniper_engine_config": SniperEngineConfig(status="paused")})  # type: ignore[arg-type]
        from app.schemas import TimeState

        t1 = TimeState(day=state.time.day, hour=state.time.hour, minute=state.time.minute + 5)
        after_first_tick = nexus_tick(state, t1, 5)
        assert len(after_first_tick.sniper_equity_history) == 1

        # "Restart": a fresh state object holding the exact same
        # persisted history (what loading a save produces).
        reloaded = after_first_tick.model_copy(update={"time": t1})
        t2 = TimeState(day=t1.day, hour=t1.hour, minute=t1.minute + 5)
        after_second_tick = nexus_tick(reloaded, t2, 5)
        assert len(after_second_tick.sniper_equity_history) == 2
        assert after_second_tick.sniper_equity_history[0].id == after_first_tick.sniper_equity_history[0].id
