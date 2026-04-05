# qbrain v1 design (approved)

- Single SQLite DB (`data/qbrain.db`) with FTS5 + embeddings table.
- Python monolith: shared core used by Typer CLI + FastAPI API.
- No markdown export layer in v1.
- OpenAI embeddings as default provider.
- Flex citations mode (notes can exist without citations).

## Initial scope

- CLI: init, ingest, search, ask, serve
- API: /health, /ingest, /search, /ask
- Quake-first ingestion from URLs/files

## Core tables

- `sources`, `documents`, `entities`, `notes`, `links`, `embeddings`, `jobs`
- `documents_fts` for BM25/keyword retrieval

## Next implementation iteration

- richer entity extraction
- graph endpoints
- better ask synthesis with citations/ranking controls
