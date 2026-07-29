"""Covers app/persistence.py — added for v0.6.2's persistence fix.

Exercises the real SQLAlchemy/SQLite layer end-to-end (a temp on-disk
database per test, not an in-memory fake), because the bug being fixed
here — old saves getting silently discarded on any schema change — only
shows up when data actually round-trips through SQLite the same way
`main.py`'s startup does.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db
import app.persistence as persistence
from app.models import Base, SaveBackup, SaveGame, SaveModule
from app.save_modules import ALL_MODULES
from app.schemas import EntityTransform, TimeState
from app.state import default_state


@pytest.fixture()
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Points app.db / app.persistence at an isolated on-disk SQLite file
    for the duration of one test, so tests never touch the real dev DB and
    never interfere with each other."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", session_local)
    monkeypatch.setattr(persistence, "get_session", session_local)

    db.init_db()
    return db_path


def test_load_returns_none_on_a_fresh_database(temp_db):
    assert persistence.load_save() is None


def test_persist_then_load_round_trips_real_state(temp_db):
    state = default_state().model_copy(
        update={
            "time": TimeState(day=12, hour=14, minute=30),
            "player": EntityTransform(scene="BrainRoomScene", x=144, y=96, facing="up"),
        }
    )
    persistence.persist_save(state)

    loaded = persistence.load_save()
    assert loaded is not None
    assert loaded.time.day == 12
    assert loaded.player.scene == "BrainRoomScene"
    assert loaded.player.x == 144


def test_migration_recovers_an_old_save_missing_a_newer_field(temp_db):
    """Simulates exactly the bug this file fixes: a save written before a
    field existed. Rather than being silently discarded and overwritten
    (the old behavior), it must be recovered with its real data intact and
    the missing field filled in from defaults."""
    old_style = default_state().model_dump(by_alias=True)
    old_style["time"] = {"day": 47, "hour": 9, "minute": 15}
    old_style["player"] = {"scene": "TradingFloorScene", "x": 200, "y": 80, "facing": "down"}
    del old_style["companyScore"]  # simulates a pre-v0.5 save, before companyScore existed

    session = db.SessionLocal()
    try:
        session.add(SaveGame(slot="default", data=json.dumps(old_style)))
        session.commit()
    finally:
        session.close()

    recovered = persistence.load_save()
    assert recovered is not None
    assert recovered.time.day == 47
    assert recovered.player.scene == "TradingFloorScene"
    assert recovered.company_score is not None  # filled in from defaults, not fabricated real data


def test_corrupted_save_is_backed_up_not_destroyed(temp_db):
    session = db.SessionLocal()
    try:
        session.add(SaveGame(slot="default", data="not valid json at all {{{"))
        session.commit()
    finally:
        session.close()

    assert persistence.load_save() is None  # signals "start fresh" to the caller

    session = db.SessionLocal()
    try:
        backups = session.query(SaveBackup).filter_by(reason="pre_fresh_fallback").all()
        assert len(backups) == 1
        assert backups[0].data == "not valid json at all {{{"
    finally:
        session.close()


def test_periodic_backups_are_capped(temp_db):
    for day in range(persistence.MAX_PERIODIC_BACKUPS + 5):
        state = default_state().model_copy(update={"time": TimeState(day=day + 1, hour=0, minute=0)})
        persistence.persist_save(state)

    session = db.SessionLocal()
    try:
        count = session.query(SaveBackup).filter_by(reason="periodic").count()
        assert count == persistence.MAX_PERIODIC_BACKUPS
    finally:
        session.close()


class TestPersistModules:
    """v0.7 Save Architecture Redesign Phase 2 — the real primary write/read
    path (see persist_modules()/load_modules()'s own docstrings)."""

    def test_load_modules_returns_none_on_a_fresh_database(self, temp_db):
        assert persistence.load_modules() is None

    def test_persist_then_load_modules_round_trips_real_state(self, temp_db):
        state = default_state().model_copy(
            update={
                "time": TimeState(day=12, hour=14, minute=30),
                "player": EntityTransform(scene="BrainRoomScene", x=144, y=96, facing="up"),
            }
        )
        results = persistence.persist_modules(state)
        assert {r.name for r in results} == set(ALL_MODULES)
        assert all(r.ok for r in results)
        assert all(r.bytes_written > 0 for r in results)  # first write: nothing to skip yet

        loaded = persistence.load_modules()
        assert loaded is not None
        assert loaded.time.day == 12
        assert loaded.player.scene == "BrainRoomScene"
        assert loaded.player.x == 144

    def test_persisting_unchanged_state_twice_skips_every_module(self, temp_db):
        state = default_state()
        persistence.persist_modules(state)
        results = persistence.persist_modules(state)  # nothing changed since the first call
        assert all(r.ok for r in results)
        assert all(r.bytes_written == 0 for r in results)  # this is the real "only save what changed" win

    def test_changing_one_module_only_rewrites_that_module(self, temp_db):
        state = default_state()
        persistence.persist_modules(state)

        changed = state.model_copy(update={"player": EntityTransform(scene="CeoOfficeScene", x=1, y=1, facing="down")})
        results = persistence.persist_modules(changed)
        by_name = {r.name: r for r in results}
        assert by_name["settings"].bytes_written > 0  # player lives in the settings module
        assert by_name["research"].bytes_written == 0
        assert by_name["employees"].bytes_written == 0
        assert by_name["trade_history"].bytes_written == 0

    def test_a_corrupted_module_row_recovers_from_defaults_not_a_full_reset(self, temp_db):
        state = default_state().model_copy(update={"time": TimeState(day=30, hour=6, minute=0)})
        persistence.persist_modules(state)

        session = db.SessionLocal()
        try:
            row = session.query(SaveModule).filter_by(slot="default", module="research").one()
            row.data = "not valid json at all {{{"
            session.commit()
        finally:
            session.close()

        recovered = persistence.load_modules()
        assert recovered is not None
        # The real, undamaged data in every other module survives...
        assert recovered.time.day == 30
        # ...while only the corrupted module falls back to real defaults (not
        # the real seeded research this save actually had, which is exactly
        # what's expected — that module's own row was destroyed — but a
        # sane, valid default rather than a crash or a full-state reset).
        assert len(recovered.research) == len(default_state().research)

    def test_load_state_migrates_a_legacy_single_blob_save_exactly_once(self, temp_db):
        legacy = default_state().model_copy(update={"time": TimeState(day=88, hour=3, minute=0)})
        persistence.persist_save(legacy)  # the pre-Phase-2 write path
        assert persistence.load_modules() is None  # no module rows exist yet

        migrated = persistence.load_state()
        assert migrated is not None
        assert migrated.time.day == 88

        session = db.SessionLocal()
        try:
            count = session.query(SaveModule).filter_by(slot="default").count()
            assert count == len(ALL_MODULES)  # the migration actually wrote module rows
        finally:
            session.close()

        # Second call reads the now-existing module rows, not the legacy row again.
        again = persistence.load_state()
        assert again is not None
        assert again.time.day == 88

    def test_load_state_returns_none_on_a_fresh_database(self, temp_db):
        assert persistence.load_state() is None


def test_add_missing_columns_alters_a_table_created_by_an_older_version(tmp_path: Path):
    """Simulates upgrading an existing deployment's database: a `saves`
    table that predates the `schema_version` column. `init_db()` must add
    it via ALTER TABLE rather than requiring a fresh database."""
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE saves (id INTEGER PRIMARY KEY, slot VARCHAR(64) UNIQUE, data TEXT, updated_at DATETIME)"
    )
    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    original_engine = db.engine
    db.engine = engine
    try:
        Base.metadata.create_all(bind=engine)  # save_backups is brand new, created here
        db._add_missing_columns()

        conn = sqlite3.connect(str(db_path))
        columns = {row[1] for row in conn.execute("PRAGMA table_info(saves)")}
        conn.execute("INSERT INTO saves (slot, data, schema_version) VALUES ('default', '{}', 1)")
        conn.commit()
        conn.close()
        assert "schema_version" in columns
    finally:
        db.engine = original_engine
