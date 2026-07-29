from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SaveGame(Base):
    """Single-row-per-slot persisted save. v0.1 only ever uses the 'default' slot."""

    __tablename__ = "saves"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String(64), unique=True, index=True, default="default")
    data: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Which persistence.SCHEMA_VERSION this row was last written under —
    # diagnostic only (lets an operator see at a glance whether the live
    # row required migration on its last load), not read by any migration
    # logic itself. Nullable because rows written before this column
    # existed (any save made before v0.6.2) simply have no value here.
    schema_version: Mapped[int | None] = mapped_column(default=None, nullable=True)


class SaveModule(Base):
    """v0.7 — Save Architecture Redesign Phase 2. One row per (slot, module)
    — see app/save_modules.py for the module map. Replaces `SaveGame` as the
    live persistence target; `SaveGame`/`SaveBackup` stay in place unchanged
    so the one-time migration in persistence.py can still read an existing
    single-blob save written by an older version of this app.

    `data_hash` is a SHA-256 of `data`, stored redundantly so
    persist_modules() can check whether a module actually changed without
    reading back its (potentially large) `data` column first — see
    persist_modules()'s own docstring for why this is the real "only save
    what changed" mechanism, not client-side dirty-tracking.
    """

    __tablename__ = "save_modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String(64), index=True, default="default")
    module: Mapped[str] = mapped_column(String(64))
    data: Mapped[str] = mapped_column(Text)
    data_hash: Mapped[str] = mapped_column(String(64))
    module_version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("slot", "module", name="uq_save_modules_slot_module"),)


class SaveBackup(Base):
    """Rolling history of persisted saves, plus a permanent record of any
    raw payload that failed to load — see persistence.py's `load_save()`.
    Never written to directly by request handlers; only persistence.py
    touches this table. Restoring a backup is a manual operation (copy a
    row's `data` back into `saves.data`) — there is intentionally no
    "restore" API endpoint, since an accidental one-click restore is its
    own data-loss risk."""

    __tablename__ = "save_backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot: Mapped[str] = mapped_column(String(64), index=True, default="default")
    # 'periodic' - a routine snapshot taken alongside a normal persist_save().
    # 'pre_fresh_fallback' - the raw payload that failed to load/migrate,
    #   preserved before the live row was reset to a fresh default state.
    reason: Mapped[str] = mapped_column(String(32))
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
