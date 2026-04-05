from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from .db import connect
from .embeddings import embed_text, vec_to_blob


def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        start = end
    return chunks


def _fetch_text(source_ref: str) -> tuple[str, str]:
    if source_ref.startswith("http://") or source_ref.startswith("https://"):
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            r = client.get(source_ref)
            r.raise_for_status()
            return source_ref, r.text

    p = Path(source_ref)
    if not p.exists():
        raise FileNotFoundError(source_ref)
    return p.name, p.read_text(errors="ignore")


def ingest_source(source_ref: str) -> dict:
    title, raw_text = _fetch_text(source_ref)
    source_type = "url" if source_ref.startswith("http") else "file"
    chunks = _chunk_text(raw_text)

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sources(source_type, source_ref, title, raw_text)
        VALUES (?,?,?,?)
        ON CONFLICT(source_ref) DO UPDATE SET
          source_type=excluded.source_type,
          title=excluded.title,
          raw_text=excluded.raw_text,
          fetched_at=(strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        """,
        (source_type, source_ref, title, raw_text),
    )
    source_id = cur.execute(
        "SELECT id FROM sources WHERE source_ref=?", (source_ref,)
    ).fetchone()[0]

    cur.execute("DELETE FROM documents WHERE source_id=?", (source_id,))

    inserted_docs = 0
    embedded_docs = 0

    for i, chunk in enumerate(chunks):
        cur.execute(
            "INSERT INTO documents(source_id, chunk_index, content) VALUES (?,?,?)",
            (source_id, i, chunk),
        )
        doc_id = cur.lastrowid
        inserted_docs += 1
        try:
            model, vec = embed_text(chunk)
            cur.execute(
                "INSERT OR REPLACE INTO embeddings(document_id, model, dims, vector) VALUES (?,?,?,?)",
                (doc_id, model, len(vec), vec_to_blob(vec)),
            )
            embedded_docs += 1
        except Exception:
            # best effort in v1
            pass

    conn.commit()
    conn.close()

    return {
        "source_ref": source_ref,
        "source_id": source_id,
        "chunks": inserted_docs,
        "embedded": embedded_docs,
        "content_sha1": hashlib.sha1(raw_text.encode(errors="ignore")).hexdigest(),
    }
