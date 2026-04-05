from __future__ import annotations

from .db import connect


def search_fts(query: str, limit: int = 10) -> list[dict]:
    conn = connect()
    rows = conn.execute(
        """
        SELECT d.id, s.source_ref, d.chunk_index,
               snippet(documents_fts, 0, '[', ']', '…', 20) AS snippet
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        JOIN sources s ON s.id = d.source_id
        WHERE documents_fts MATCH ?
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
