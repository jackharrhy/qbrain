from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool = True


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ref: str = Field(..., description="URL or local file path to ingest")


class IngestBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_refs: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ref: str
    source_id: int
    chunks: int
    embedded: int
    content_sha1: str


class IngestBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int
    ok: int
    failed: int
    results: list[IngestResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


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


class SourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    source_type: str
    source_ref: str
    title: str
    fetched_at: str


class SourceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceItem]


class ExtractLinksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    links: list[str]


class DiscoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = 50
    ingest: bool = False


class DiscoverResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: int
    discovered: int
    links: list[str]
    ingested: int = 0


class NoteDiscoverResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_id: int
    discovered: int
    links: list[str]
    ingested: int = 0


class NoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    body: str
    stage: str = "scratch"
    status: str = "draft"
    confidence: float = 0.5
    source_count: int = 0


class NoteUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    body: str | None = None
    stage: str | None = None
    status: str | None = None
    confidence: float | None = None
    source_count: int | None = None


class NoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    title: str
    body: str
    stage: str
    status: str
    confidence: float
    source_count: int
    created_at: str
    updated_at: str


class NoteListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: list[NoteItem]
