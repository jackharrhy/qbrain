from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from .api_models import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    SearchHit,
    SearchResponse,
)
from .ask import ask
from .db import connect, init_db
from .ingest import ingest_source
from .search import search_fts

app = FastAPI(title="qbrain", version="0.1.0")

INTER_FONT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap"
HTMX_CDN = "https://unpkg.com/htmx.org@1.9.12"


def _render_markdown(md_text: str) -> str:
    try:
        from markdown_it import MarkdownIt

        return MarkdownIt("commonmark", {"html": False, "linkify": True}).render(md_text)
    except Exception:
        # ultra-safe fallback if markdown parser is unavailable
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
      body {{ font-family: Inter, system-ui, sans-serif; max-width: 920px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
      h1 {{ margin: 0 0 1rem; font-size: 1.6rem; }}
      input[type=search] {{ width: 100%; padding: .7rem .9rem; border-radius: .6rem; border: 1px solid #9994; font: inherit; }}
      .card {{ border: 1px solid #9994; border-radius: .7rem; padding: .75rem .9rem; margin: .7rem 0; }}
      .muted {{ opacity: .75; font-size: .92rem; }}
      a {{ text-decoration: none; }}
      code {{ background: #9992; padding: .1rem .3rem; border-radius: .3rem; }}
    </style>
  </head>
  <body>{body}</body>
</html>"""


def _required_mutation_token() -> str:
    # User-requested default for quick hardening; override via env in production.
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


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.post(
    "/ingest",
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


@app.get("/search", response_model=SearchResponse, tags=["query"])
def search(
    q: Annotated[str, Query(min_length=1, description="FTS query string")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SearchResponse:
    hits = [SearchHit(**row) for row in search_fts(q, limit=limit)]
    return SearchResponse(results=hits)


@app.post("/ask", response_model=AskResponse, tags=["query"])
def ask_route(inp: AskRequest) -> AskResponse:
    out = ask(inp.question)
    hits = [SearchHit(**row) for row in out.get("hits", [])]
    return AskResponse(answer=out.get("answer", ""), hits=hits)


@app.get("/ui", response_class=HTMLResponse, tags=["ui"])
def ui_home() -> HTMLResponse:
    body = """
    <h1>qbrain</h1>
    <p class='muted'>Search sources and chunks. Click a source to view raw markdown rendered as HTML.</p>
    <input
      type='search'
      name='q'
      placeholder='Search (e.g. quake movement idtech2)'
      hx-get='/ui/search'
      hx-trigger='keyup changed delay:250ms'
      hx-target='#results'
      hx-swap='innerHTML'
    />
    <div id='results' class='muted' style='margin-top:1rem'>Start typing to search…</div>
    """
    return HTMLResponse(_base_shell(body, title="qbrain · search"))


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
