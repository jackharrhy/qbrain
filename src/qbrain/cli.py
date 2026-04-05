from __future__ import annotations

import json

import typer
import uvicorn

from .ask import ask
from .db import init_db
from .ingest import ingest_source
from .search import search_fts

app = typer.Typer(help="qbrain CLI")


@app.command()
def init() -> None:
    init_db()
    typer.echo("initialized qbrain db")


@app.command()
def ingest(source_ref: str) -> None:
    init_db()
    out = ingest_source(source_ref)
    typer.echo(json.dumps(out, indent=2))


@app.command()
def search(query: str, limit: int = 10) -> None:
    init_db()
    out = search_fts(query, limit=limit)
    typer.echo(json.dumps(out, indent=2))


@app.command(name="ask")
def ask_cmd(question: str) -> None:
    init_db()
    out = ask(question)
    typer.echo(json.dumps(out, indent=2))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8099) -> None:
    uvicorn.run("qbrain.api:app", host=host, port=port, reload=False)
