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


def _sql_literal(value: object) -> str:
    """A minimal, deliberately narrow scalar->SQL-literal formatter for
    the handful of default types this codebase's own models actually
    use (int/float/bool/str/None) — see `_add_column`'s docstring for
    why this stays narrow rather than growing into a general-purpose
    SQL literal encoder."""
    if value is None:
        raise ValueError("NULL is not a usable literal for a NOT NULL column's DEFAULT.")
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError(f"No literal SQL form for default value {value!r} of type {type(value)!r}.")


def _add_column(table, column) -> None:  # type: ignore[no-untyped-def]
    """Live end-to-end QA pass (2026-08-26) found the original version of
    this function only ever emitted the column's *type* in the ALTER
    TABLE DDL, silently dropping NOT NULL/default/unique/index —
    meaning a NOT NULL column added to a table with existing rows would
    get a real NULL in every old row despite the model's Python type
    hint promising it's never None, with no error and no backfill. This
    version restores those semantics as far as SQLite's real ALTER TABLE
    limits allow: SQLite can only add a NOT NULL column in the same
    statement as a literal DEFAULT, and can never add a NOT NULL
    constraint after the fact — so a non-nullable column backed by a
    real Python-side default (e.g. `default=lambda: datetime.now(...)`,
    which has no SQL-literal form) is added nullable and then backfilled
    row-by-row with that same default, closing the actual data-integrity
    gap even though SQLite's own schema can't enforce NOT NULL on it
    retroactively. A non-nullable column with no default at all — no
    safe value to backfill with — fails loudly at startup instead of
    silently shipping NULLs into a column nothing expects them in."""
    ddl_type = column.type.compile(engine.dialect)
    literal_default: str | None = None
    callable_default = None
    if not column.nullable:
        if column.server_default is not None:
            literal_default = str(column.server_default.arg)
        elif column.default is not None and column.default.is_scalar:
            literal_default = _sql_literal(column.default.arg)
        elif column.default is not None and column.default.is_callable:
            callable_default = column.default.arg
        else:
            raise RuntimeError(
                f"Cannot safely add non-nullable column {table.name}.{column.name} to an existing table: "
                "no server_default, scalar default, or callable default to backfill existing rows with. "
                "Give this column a real default (or make it nullable) before shipping this migration."
            )

    ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl_type}"
    if literal_default is not None:
        ddl += f" NOT NULL DEFAULT {literal_default}"

    with engine.begin() as conn:
        conn.execute(text(ddl))
        if callable_default is not None:
            try:
                value = callable_default()  # most real callables here (e.g. datetime.now) take no context arg
            except TypeError:
                value = callable_default(None)  # SQLAlchemy's ExecutionContext-taking callable convention
            conn.execute(text(f"UPDATE {table.name} SET {column.name} = :value WHERE {column.name} IS NULL"), {"value": value})
        if column.unique:
            conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table.name}_{column.name}_unique ON {table.name} ({column.name})"))
        elif column.index:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table.name}_{column.name} ON {table.name} ({column.name})"))
    logger.info("Added missing column %s.%s to match the current schema.", table.name, column.name)


def _add_missing_columns() -> None:
    """`Base.metadata.create_all()` only creates tables that don't exist yet —
    it never alters an existing table's columns. That's fine for brand-new
    tables (like `save_backups`), but a column added to an *existing* table
    (like `SaveGame.schema_version`) needs an explicit ALTER TABLE, or every
    query touching that column fails with "no such column" against a
    database created by an older version of this app. Deliberately minimal
    (SQLite's ADD COLUMN, nothing fancier) — this project has one physical
    table per model and no need for a full migration framework like
    Alembic yet. See `_add_column` for how NOT NULL/default/unique/index
    are actually preserved within SQLite's real ALTER TABLE limits."""
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if table.name not in inspector.get_table_names():
            continue  # created fresh by create_all(); no existing columns to reconcile
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            _add_column(table, column)


def init_db() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        if db_path not in (":memory:", ""):
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def get_session() -> Session:
    return SessionLocal()
