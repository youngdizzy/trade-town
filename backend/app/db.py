from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

logger = logging.getLogger("tradetown.db")

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _add_missing_columns() -> None:
    """`Base.metadata.create_all()` only creates tables that don't exist yet —
    it never alters an existing table's columns. That's fine for brand-new
    tables (like `save_backups`), but a column added to an *existing* table
    (like `SaveGame.schema_version`) needs an explicit ALTER TABLE, or every
    query touching that column fails with "no such column" against a
    database created by an older version of this app. Deliberately minimal
    (SQLite's ADD COLUMN, nothing fancier) — this project has one physical
    table per model and no need for a full migration framework like
    Alembic yet."""
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if table.name not in inspector.get_table_names():
            continue  # created fresh by create_all(); no existing columns to reconcile
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            ddl_type = column.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl_type}"))
            logger.info("Added missing column %s.%s to match the current schema.", table.name, column.name)


def init_db() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        if db_path not in (":memory:", ""):
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def get_session() -> Session:
    return SessionLocal()
