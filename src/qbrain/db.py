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


def init_db() -> None:
    from . import schema

    conn = connect()
    conn.executescript(schema.SQL)
    conn.commit()
    conn.close()
