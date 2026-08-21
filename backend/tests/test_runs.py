"""Covers CEO directive "Proper Multi-Run / Save Isolation System" —
app/persistence.py's run registry (list_runs/register_run/
ensure_default_run_registered/get_active_run_id/set_active_run_pointer)
and app/state.py's GameState.switch_run()/create_run().

Exercises the real SQLAlchemy/SQLite layer end-to-end via an isolated
on-disk temp database per test (same convention as test_persistence.py),
never the real dev/production save.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db
import app.persistence as persistence
from app.state import GameState, default_state


@pytest.fixture()
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Points app.db / app.persistence at an isolated on-disk SQLite file
    for the duration of one test, and resets the mutable active-slot
    pointer to DEFAULT_SLOT before and after — monkeypatch auto-reverts
    the attribute, so this never leaks into another test file."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", session_local)
    monkeypatch.setattr(persistence, "get_session", session_local)
    monkeypatch.setattr(persistence, "SLOT", persistence.DEFAULT_SLOT)

    db.init_db()
    return db_path


class TestEnsureDefaultRunRegistered:
    def test_a_genuinely_fresh_database_registers_nothing(self, temp_db) -> None:
        persistence.ensure_default_run_registered()
        assert persistence.list_runs() == []

    def test_an_existing_pre_multi_run_save_is_registered_as_original_run(self, temp_db) -> None:
        state = default_state().model_copy(update={})
        persistence.persist_modules(state)  # simulates a save written before this feature existed

        persistence.ensure_default_run_registered()

        runs = persistence.list_runs()
        assert len(runs) == 1
        assert runs[0].run_id == persistence.DEFAULT_SLOT
        assert runs[0].display_name == "Original Run"

    def test_is_idempotent_a_second_call_does_not_duplicate_the_run(self, temp_db) -> None:
        persistence.persist_modules(default_state())
        persistence.ensure_default_run_registered()
        persistence.ensure_default_run_registered()

        assert len(persistence.list_runs()) == 1

    def test_never_mutates_the_active_slot_pointer_as_a_side_effect(self, temp_db) -> None:
        persistence.persist_modules(default_state())
        persistence.set_active_slot("some-other-run")

        persistence.ensure_default_run_registered()

        assert persistence.get_active_slot() == "some-other-run"


class TestListRuns:
    def test_current_day_is_read_live_from_the_real_world_module(self, temp_db) -> None:
        persistence.set_active_slot("run-a")
        state = default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 47})})
        persistence.persist_modules(state)
        persistence.register_run("run-a", "Run A")

        runs = persistence.list_runs()
        assert runs[0].current_day == 47

    def test_a_run_with_no_world_module_yet_reads_an_honest_none_never_a_fabricated_day(self, temp_db) -> None:
        persistence.register_run("run-empty", "Empty Run")

        runs = persistence.list_runs()
        assert runs[0].current_day is None

    def test_reading_a_different_slot_never_disturbs_the_active_slot_pointer(self, temp_db) -> None:
        persistence.set_active_slot("run-a")
        persistence.persist_modules(default_state())
        persistence.register_run("run-a", "Run A")

        persistence.set_active_slot("run-b")
        persistence.list_runs()  # reads run-a's world module internally

        assert persistence.get_active_slot() == "run-b"


class TestGameStateCreateRun:
    def test_creates_a_fresh_run_starting_at_day_one(self, temp_db) -> None:
        gs = GameState()
        state, run_id = asyncio.run(gs.create_run("New Run"))
        assert state.time.day == 1
        assert run_id != persistence.DEFAULT_SLOT

    def test_persists_and_registers_the_new_run_for_real(self, temp_db) -> None:
        gs = GameState()
        _, run_id = asyncio.run(gs.create_run("New Run"))

        runs = persistence.list_runs()
        assert any(r.run_id == run_id and r.display_name == "New Run" for r in runs)
        assert persistence.get_active_slot() == run_id

    def test_the_run_being_left_behind_is_persisted_first_never_lost(self, temp_db) -> None:
        gs = GameState()
        gs.data = gs.data.model_copy(update={"time": gs.data.time.model_copy(update={"day": 1192})})
        persistence.register_run(persistence.DEFAULT_SLOT, "Original Run")

        asyncio.run(gs.create_run("New Run"))

        original = persistence.read_module_for_slot(persistence.DEFAULT_SLOT, "world")
        assert original is not None
        assert original["time"]["day"] == 1192

    def test_two_rapid_sequential_create_run_calls_produce_two_distinct_uncorrupted_runs(self, temp_db) -> None:
        gs = GameState()

        async def _create_both() -> tuple[str, str]:
            (_, run_a), (_, run_b) = await asyncio.gather(gs.create_run("Run A"), gs.create_run("Run B"))
            return run_a, run_b

        run_a, run_b = asyncio.run(_create_both())
        assert run_a != run_b
        runs = {r.run_id: r for r in persistence.list_runs()}
        assert runs[run_a].current_day == 1
        assert runs[run_b].current_day == 1


class TestGameStateSwitchRun:
    def test_switching_loads_the_target_runs_real_state(self, temp_db) -> None:
        gs = GameState()
        persistence.set_active_slot("run-a")
        run_a_state = default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 1192})})
        persistence.persist_modules(run_a_state)
        persistence.register_run("run-a", "Run A")
        persistence.set_active_slot(persistence.DEFAULT_SLOT)  # simulate a different run currently active

        loaded = asyncio.run(gs.switch_run("run-a"))
        assert loaded.time.day == 1192
        assert persistence.get_active_slot() == "run-a"

    def test_switching_away_persists_the_run_being_left_first(self, temp_db) -> None:
        gs = GameState()
        persistence.register_run(persistence.DEFAULT_SLOT, "Original Run")
        persistence.set_active_slot("run-b")
        persistence.persist_modules(default_state())  # run-b's own real initial state
        persistence.register_run("run-b", "Run B")
        persistence.set_active_slot(persistence.DEFAULT_SLOT)  # back to the run gs is "on" before switching

        gs.data = gs.data.model_copy(update={"time": gs.data.time.model_copy(update={"day": 55})})
        asyncio.run(gs.switch_run("run-b"))

        left_behind = persistence.read_module_for_slot(persistence.DEFAULT_SLOT, "world")
        assert left_behind is not None
        assert left_behind["time"]["day"] == 55

    def test_switching_to_a_nonexistent_run_fails_safely_no_mutation(self, temp_db) -> None:
        gs = GameState()
        persistence.set_active_slot(persistence.DEFAULT_SLOT)
        persistence.persist_modules(default_state())

        with pytest.raises(ValueError):
            asyncio.run(gs.switch_run("does-not-exist"))

        # Active slot reverted -- never left pointed at a run with no data.
        assert persistence.get_active_slot() == persistence.DEFAULT_SLOT
        # The real state in memory is untouched too.
        assert gs.data.time.day == default_state().time.day

    def test_run_a_and_run_b_stay_fully_independent_across_two_switches(self, temp_db) -> None:
        gs = GameState()
        persistence.set_active_slot("run-a")
        a_state = default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 10})})
        persistence.persist_modules(a_state)
        persistence.register_run("run-a", "Run A")

        persistence.set_active_slot("run-b")
        b_state = default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 200})})
        persistence.persist_modules(b_state)
        persistence.register_run("run-b", "Run B")

        # gs is currently "on" run-b's data in memory; switch to A, back to B.
        gs.data = b_state
        loaded_a = asyncio.run(gs.switch_run("run-a"))
        assert loaded_a.time.day == 10
        loaded_b = asyncio.run(gs.switch_run("run-b"))
        assert loaded_b.time.day == 200

        # Saving while on run-a never touched run-b's own data, and vice versa.
        a_on_disk = persistence.read_module_for_slot("run-a", "world")
        b_on_disk = persistence.read_module_for_slot("run-b", "world")
        assert a_on_disk is not None and a_on_disk["time"]["day"] == 10
        assert b_on_disk is not None and b_on_disk["time"]["day"] == 200

    def test_switching_touches_last_played_at(self, temp_db) -> None:
        gs = GameState()
        persistence.set_active_slot("run-a")
        persistence.persist_modules(default_state())
        persistence.register_run("run-a", "Run A")
        persistence.set_active_slot(persistence.DEFAULT_SLOT)
        before = next(r for r in persistence.list_runs() if r.run_id == "run-a").last_played_at

        asyncio.run(gs.switch_run("run-a"))

        after = next(r for r in persistence.list_runs() if r.run_id == "run-a").last_played_at
        assert after >= before


class TestServerRestartPreservesAllRuns:
    def test_both_runs_are_still_readable_from_a_fresh_process_level_read(self, temp_db) -> None:
        persistence.set_active_slot("run-a")
        persistence.persist_modules(default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 5})}))
        persistence.register_run("run-a", "Run A")

        persistence.set_active_slot("run-b")
        persistence.persist_modules(default_state().model_copy(update={"time": default_state().time.model_copy(update={"day": 99})}))
        persistence.register_run("run-b", "Run B")

        # Simulates a restart: nothing in-memory carries over, only the on-disk DB.
        persistence.set_active_slot(persistence.DEFAULT_SLOT)
        runs = {r.run_id: r.current_day for r in persistence.list_runs()}
        assert runs == {"run-a": 5, "run-b": 99}

    def test_the_active_run_pointer_itself_survives_a_restart(self, temp_db) -> None:
        persistence.register_run("run-a", "Run A")
        persistence.set_active_run_pointer("run-a")

        # A fresh read of the pointer, as main.py's lifespan() does on boot.
        assert persistence.get_active_run_id() == "run-a"
