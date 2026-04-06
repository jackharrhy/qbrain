from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Path, Query, status
from fastapi.responses import HTMLResponse

from .api_models import (
    AskRequest,
    AskResponse,
    DiscoverRequest,
    DiscoverResponse,
    ExtractLinksResponse,
    HealthResponse,
    IngestBatchRequest,
    IngestBatchResponse,
    IngestRequest,
    IngestResponse,
    NoteCreateRequest,
    NoteDiscoverResponse,
    NoteItem,
    NoteListResponse,
    NoteUpdateRequest,
    SearchHit,
    SearchResponse,
    SourceItem,
    SourceListResponse,
)
from .ask import ask
from .db import connect, init_db
from .discover import extract_links
from .ingest import ingest_source
from .search import search_fts

app = FastAPI(title="qbrain", version="0.2.0")

INTER_FONT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap"
HTMX_CDN = "https://unpkg.com/htmx.org@1.9.12"


def _render_markdown(md_text: str) -> str:
    try:
        from markdown_it import MarkdownIt

        return MarkdownIt("commonmark", {"html": False, "linkify": True}).render(md_text)
    except Exception:
        escaped = (
            md_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<pre>{escaped}</pre>"


def _base_shell(body: str, title: str = "qbrain") -> str:
    return f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\"> 
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"{INTER_FONT}\" rel=\"stylesheet\">
    <script src=\"{HTMX_CDN}\"></script>
    <style>
      :root {{ color-scheme: light dark; }}
      body {{ font-family: Inter, system-ui, sans-serif; max-width: 1080px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
      h1 {{ margin: 0 0 1rem; font-size: 1.6rem; }}
      input[type=search] {{ width: 100%; padding: .7rem .9rem; border-radius: .6rem; border: 1px solid #9994; font: inherit; }}
      .layout {{ display: grid; grid-template-columns: 280px 1fr; gap: 1rem; align-items: start; }}
      .card {{ border: 1px solid #9994; border-radius: .7rem; padding: .75rem .9rem; margin: .7rem 0; }}
      .muted {{ opacity: .75; font-size: .92rem; }}
      a {{ text-decoration: none; }}
      code {{ background: #9992; padding: .1rem .3rem; border-radius: .3rem; }}
      .note-row {{ border-bottom: 1px solid #9993; padding: .5rem 0; display:flex; justify-content:space-between; gap:.5rem; }}
      .btn {{ border:1px solid #9994; border-radius:.45rem; padding:.2rem .5rem; font-size:.85rem; }}
      .chips {{ display:flex; gap:.4rem; flex-wrap:wrap; margin:.35rem 0 .6rem; }}
      .chip {{ border:1px solid #9994; border-radius:999px; padding:.12rem .5rem; font-size:.78rem; }}
      @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>{body}</body>
</html>"""


def _required_mutation_token() -> str:
    return os.getenv("QBRAIN_API_TOKEN", "instagib")


def _authorize_mutation(
    x_api_token: str | None,
    authorization: str | None,
) -> None:
    expected = _required_mutation_token()
    provided = x_api_token
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(" ", 1)[1].strip()

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/api/sources", response_model=SourceListResponse, tags=["query"])
def list_sources(
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> SourceListResponse:
    conn = connect()
    rows = conn.execute(
        """
        SELECT id, source_type, source_ref, title, fetched_at
        FROM sources
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return SourceListResponse(sources=[SourceItem(**dict(r)) for r in rows])


@app.post(
    "/api/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    tags=["mutation"],
)
def ingest(
    inp: IngestRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> IngestResponse:
    _authorize_mutation(x_api_token, authorization)
    return IngestResponse(**ingest_source(inp.source_ref))


@app.post(
    "/api/ingest/batch",
    response_model=IngestBatchResponse,
    tags=["mutation"],
)
def ingest_batch(
    inp: IngestBatchRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> IngestBatchResponse:
    _authorize_mutation(x_api_token, authorization)
    results: list[IngestResponse] = []
    errors: list[str] = []
    for ref in inp.source_refs:
        try:
            results.append(IngestResponse(**ingest_source(ref)))
        except Exception as e:
            errors.append(f"{ref}: {e}")
    return IngestBatchResponse(
        total=len(inp.source_refs),
        ok=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )


@app.get("/api/search", response_model=SearchResponse, tags=["query"])
def search(
    q: Annotated[str, Query(min_length=1, description="FTS query string")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SearchResponse:
    hits = [SearchHit(**row) for row in search_fts(q, limit=limit)]
    return SearchResponse(results=hits)


@app.post("/api/ask", response_model=AskResponse, tags=["query"])
def ask_route(inp: AskRequest) -> AskResponse:
    out = ask(inp.question)
    hits = [SearchHit(**row) for row in out.get("hits", [])]
    return AskResponse(answer=out.get("answer", ""), hits=hits)


@app.get(
    "/api/extract-links/{source_id}",
    response_model=ExtractLinksResponse,
    tags=["query"],
)
def extract_links_from_source(
    source_id: Annotated[int, Path(ge=1)],
) -> ExtractLinksResponse:
    conn = connect()
    row = conn.execute(
        "SELECT source_ref, raw_text FROM sources WHERE id=?",
        (source_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return ExtractLinksResponse(
        links=extract_links(row["raw_text"], base_url=row["source_ref"])
    )


@app.post(
    "/api/discover/from-source/{source_id}",
    response_model=DiscoverResponse,
    tags=["mutation"],
)
def discover_from_source(
    source_id: Annotated[int, Path(ge=1)],
    inp: DiscoverRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> DiscoverResponse:
    _authorize_mutation(x_api_token, authorization)

    conn = connect()
    row = conn.execute(
        "SELECT source_ref, raw_text FROM sources WHERE id=?",
        (source_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")

    links = extract_links(row["raw_text"], base_url=row["source_ref"])[: inp.limit]
    ingested = 0
    if inp.ingest:
        for link in links:
            try:
                ingest_source(link)
                ingested += 1
            except Exception:
                pass

    return DiscoverResponse(
        source_id=source_id,
        discovered=len(links),
        links=links,
        ingested=ingested,
    )


@app.post(
    "/api/discover/from-note/{note_id}",
    response_model=NoteDiscoverResponse,
    tags=["mutation"],
)
def discover_from_note(
    note_id: Annotated[int, Path(ge=1)],
    inp: DiscoverRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> NoteDiscoverResponse:
    _authorize_mutation(x_api_token, authorization)

    conn = connect()
    row = conn.execute("SELECT body FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")

    links = extract_links(row["body"])[: inp.limit]
    ingested = 0
    if inp.ingest:
        for link in links:
            try:
                ingest_source(link)
                ingested += 1
            except Exception:
                pass

    return NoteDiscoverResponse(
        note_id=note_id,
        discovered=len(links),
        links=links,
        ingested=ingested,
    )


@app.get("/api/notes", response_model=NoteListResponse, tags=["query"])
def list_notes(
    stage: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> NoteListResponse:
    conn = connect()
    sql = (
        "SELECT id,title,body,stage,status,confidence,source_count,created_at,updated_at "
        "FROM notes"
    )
    where = []
    params: list[object] = []
    if stage:
        where.append("stage=?")
        params.append(stage)
    if status_filter:
        where.append("status=?")
        params.append(status_filter)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return NoteListResponse(notes=[NoteItem(**dict(r)) for r in rows])


@app.post("/api/notes", response_model=NoteItem, tags=["mutation"])
def create_note(
    inp: NoteCreateRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> NoteItem:
    _authorize_mutation(x_api_token, authorization)
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO notes(title, body, stage, status, confidence, source_count)
        VALUES (?,?,?,?,?,?)
        """,
        (inp.title, inp.body, inp.stage, inp.status, inp.confidence, inp.source_count),
    )
    note_id = cur.lastrowid
    row = conn.execute(
        "SELECT id,title,body,stage,status,confidence,source_count,created_at,updated_at FROM notes WHERE id=?",
        (note_id,),
    ).fetchone()
    conn.commit()
    conn.close()
    return NoteItem(**dict(row))


@app.patch("/api/notes/{note_id}", response_model=NoteItem, tags=["mutation"])
def update_note(
    note_id: Annotated[int, Path(ge=1)],
    inp: NoteUpdateRequest,
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> NoteItem:
    _authorize_mutation(x_api_token, authorization)

    updates = {k: v for k, v in inp.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = "__NOW__"
    set_parts = []
    params: list[object] = []
    for k, v in updates.items():
        if k == "updated_at":
            set_parts.append("updated_at=(strftime('%Y-%m-%dT%H:%M:%SZ','now'))")
        else:
            set_parts.append(f"{k}=?")
            params.append(v)

    params.append(note_id)

    conn = connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE notes SET {', '.join(set_parts)} WHERE id=?", tuple(params))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    row = conn.execute(
        "SELECT id,title,body,stage,status,confidence,source_count,created_at,updated_at FROM notes WHERE id=?",
        (note_id,),
    ).fetchone()
    conn.commit()
    conn.close()
    return NoteItem(**dict(row))


@app.post("/api/notes/{note_id}/promote", response_model=NoteItem, tags=["mutation"])
def promote_note(
    note_id: Annotated[int, Path(ge=1)],
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> NoteItem:
    _authorize_mutation(x_api_token, authorization)
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE notes
        SET stage='research',
            status='reviewed',
            updated_at=(strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        WHERE id=?
        """,
        (note_id,),
    )
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    row = conn.execute(
        "SELECT id,title,body,stage,status,confidence,source_count,created_at,updated_at FROM notes WHERE id=?",
        (note_id,),
    ).fetchone()
    conn.commit()
    conn.close()
    return NoteItem(**dict(row))


@app.get("/api/review/queue", response_model=NoteListResponse, tags=["query"])
def review_queue(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> NoteListResponse:
    conn = connect()
    rows = conn.execute(
        """
        SELECT id,title,body,stage,status,confidence,source_count,created_at,updated_at
        FROM notes
        WHERE stage='scratch' OR confidence < 0.6 OR source_count = 0
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return NoteListResponse(notes=[NoteItem(**dict(r)) for r in rows])


@app.get("/", response_class=HTMLResponse, tags=["ui"])
@app.get("/ui", response_class=HTMLResponse, tags=["ui"])
def ui_home() -> HTMLResponse:
    body = """
    <h1>qbrain</h1>
    <p class='muted'>Search at top. Notes in sidebar. Main panel for results/source view.</p>
    <input
      type='search'
      name='q'
      placeholder='Search (e.g. quake movement idtech2)'
      hx-get='/ui/search'
      hx-trigger='keyup changed delay:250ms'
      hx-target='#mainview'
      hx-swap='innerHTML'
    />

    <div class='layout' style='margin-top:1rem'>
      <aside class='card'>
        <h3 style='margin:.2rem 0 .6rem'>Published notes</h3>
        <div id='notelist-published' hx-get='/ui/notes?stage=research' hx-trigger='load' hx-swap='innerHTML'>
          <div class='muted'>Loading notes…</div>
        </div>

        <details style='margin-top:.8rem'>
          <summary class='muted' style='cursor:pointer'>Scratch / drafts</summary>
          <div id='notelist-scratch' hx-get='/ui/notes?stage=scratch' hx-trigger='revealed' hx-swap='innerHTML' style='margin-top:.4rem'>
            <div class='muted'>Expand to load drafts…</div>
          </div>
        </details>
      </aside>
      <main id='mainview' class='card'>
        <div class='muted'>Start typing to search…</div>
      </main>
    </div>
    """
    return HTMLResponse(_base_shell(body, title="qbrain"))


@app.get("/ui/search", response_class=HTMLResponse, tags=["ui"])
def ui_search(
    q: Annotated[str, Query(min_length=1, description="FTS query")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HTMLResponse:
    hits = search_fts(q, limit=limit)
    if not hits:
        return HTMLResponse("<div class='muted'>No matches.</div>")

    parts: list[str] = []
    for h in hits:
        parts.append(
            (
                "<div class='card'>"
                f"<div><a href='/ui/source/{h['id']}'><strong>{h['source_ref']}</strong></a> "
                f"<span class='muted'>chunk {h['chunk_index']}</span></div>"
                f"<div style='margin-top:.45rem'>{h['snippet']}</div>"
                "</div>"
            )
        )
    return HTMLResponse("\n".join(parts))


@app.get("/ui/notes", response_class=HTMLResponse, tags=["ui"])
def ui_notes(
    stage: Annotated[str, Query()] = "scratch",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> HTMLResponse:
    conn = connect()
    rows = conn.execute(
        """
        SELECT id, title, stage, status, updated_at
        FROM notes
        WHERE stage = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (stage, limit),
    ).fetchall()
    conn.close()

    if not rows:
        label = "published" if stage == "research" else "draft"
        return HTMLResponse(f"<div class='muted'>No {label} notes yet.</div>")

    out: list[str] = []
    for r in rows:
        title = (r['title'] or f"note #{r['id']}").strip()
        out.append(
            "<div class='note-row'>"
            f"<span title='{title}'>{title[:46]}</span>"
            f"<a class='btn' hx-get='/ui/note/{r['id']}' hx-target='#mainview' hx-swap='innerHTML'>view</a>"
            "</div>"
        )
    return HTMLResponse("\n".join(out))


@app.get('/ui/note/{note_id}', response_class=HTMLResponse, tags=['ui'])
def ui_note(note_id: int) -> HTMLResponse:
    conn = connect()
    row = conn.execute(
        """
        SELECT id,title,body,stage,status,confidence,source_count,updated_at
        FROM notes
        WHERE id = ?
        """,
        (note_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail='Note not found')

    rendered = _render_markdown(row['body'])
    body = (
        f"<h2 style='margin:.2rem 0'>{row['title']}</h2>"
        "<div class='chips'>"
        f"<span class='chip'>stage: {row['stage']}</span>"
        f"<span class='chip'>status: {row['status']}</span>"
        f"<span class='chip'>confidence: {float(row['confidence']):.2f}</span>"
        f"<span class='chip'>sources: {row['source_count']}</span>"
        "</div>"
        f"<article>{rendered}</article>"
    )
    return HTMLResponse(body)


@app.get("/ui/source/{doc_id}", response_class=HTMLResponse, tags=["ui"])
def ui_source(doc_id: int) -> HTMLResponse:
    conn = connect()
    row = conn.execute(
        """
        SELECT d.id, d.chunk_index, d.content, s.source_ref, s.raw_text
        FROM documents d
        JOIN sources s ON s.id = d.source_id
        WHERE d.id = ?
        """,
        (doc_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Document chunk not found")

    rendered = _render_markdown(row["raw_text"])
    body = (
        f"<h1>Source view</h1>"
        f"<p class='muted'><a href='/ui'>← back</a> · <code>{row['source_ref']}</code></p>"
        f"<article class='card'>{rendered}</article>"
    )
    return HTMLResponse(_base_shell(body, title="qbrain · source"))
