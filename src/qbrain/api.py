from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, status

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
from .db import init_db
from .ingest import ingest_source
from .search import search_fts

app = FastAPI(title="qbrain", version="0.1.0")


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
