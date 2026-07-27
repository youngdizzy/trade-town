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
from app.models import Base, SaveBackup, SaveGame
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
