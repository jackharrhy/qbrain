from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB = "data/qbrain.db"


def get_db_path() -> str:
    return os.getenv("QBRAIN_DB", DEFAULT_DB)


def connect() -> sqlite3.Connection:
    db_path = Path(get_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_note_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if not cols:
        return
    if "stage" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN stage TEXT NOT NULL DEFAULT 'scratch'")
    if "status" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'")
    if "source_count" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN source_count INTEGER NOT NULL DEFAULT 0")
    if "updated_at" not in cols:
        conn.execute(
            "ALTER TABLE notes ADD COLUMN updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))"
        )


def init_db() -> None:
    from . import schema

    conn = connect()
    conn.executescript(schema.SQL)
    _ensure_note_columns(conn)
    conn.commit()
    conn.close()
