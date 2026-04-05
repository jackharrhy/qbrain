from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .ask import ask
from .db import init_db
from .ingest import ingest_source
from .search import search_fts

app = FastAPI(title="qbrain", version="0.1.0")


class IngestIn(BaseModel):
    source_ref: str


class AskIn(BaseModel):
    question: str


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/ingest")
def ingest(inp: IngestIn) -> dict:
    return ingest_source(inp.source_ref)


@app.get("/search")
def search(q: str, limit: int = 10) -> dict:
    return {"results": search_fts(q, limit=limit)}


@app.post("/ask")
def ask_route(inp: AskIn) -> dict:
    return ask(inp.question)
