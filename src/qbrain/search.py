from __future__ import annotations

import re

from .db import connect


def _fts_escape_term(term: str) -> str:
    # Keep only word-ish characters for robust natural-language matching.
    cleaned = re.sub(r"[^\w]+", "", term, flags=re.UNICODE)
    if not cleaned:
        return ""
    # Double quotes are escaped by doubling.
    cleaned = cleaned.replace('"', '""')
    return f'"{cleaned}"'


def _to_fts_query(query: str) -> str:
    terms = [_fts_escape_term(t) for t in query.split()]
    terms = [t for t in terms if t]
    if not terms:
        return '"*"'
    return " OR ".join(terms)


def search_fts(query: str, limit: int = 10) -> list[dict]:
    conn = connect()
    fts_query = _to_fts_query(query)
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
        (fts_query, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
