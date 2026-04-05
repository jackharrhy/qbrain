from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(..., description="URL or local file path to ingest")


class IngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str
    source_id: int
    chunks: int
    embedded: int
    content_sha1: str


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    source_ref: str
    chunk_index: int
    snippet: str


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SearchHit]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str


class AskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    hits: list[SearchHit]
