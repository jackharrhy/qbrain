# qbrain

Quake-focused LLM knowledge brain backed by SQLite + FTS5 + embeddings.

For URL ingestion, qbrain prefers Defuddle (`https://defuddle.md/`) to convert pages into cleaner markdown before chunking/embedding.

## Quick start

```bash
uv sync
uv run qbrain init
uv run qbrain ingest https://jackharrhy.dev/quake
uv run qbrain search quake
uv run qbrain serve --host 0.0.0.0 --port 8099
```

UI:
- `/` (primary UI)
- `/ui` (same UI alias)

API:
- `/api/health`
- `/api/search`
- `/api/ask`
- `/api/ingest`

## Env

- `QBRAIN_DB` (default: `data/qbrain.db`)
- `OPENAI_API_KEY` (required for embeddings + ask)
- `QBRAIN_EMBED_MODEL` (default: `text-embedding-3-small`)
- `QBRAIN_API_TOKEN` (required for mutating endpoints like `/ingest`; default fallback: `instagib`)

## API auth (mutation endpoints)

`/api/ingest` requires a token via either:
- `X-API-Token: <token>`
- `Authorization: Bearer <token>`

Example:

```bash
curl -X POST http://127.0.0.1:8099/api/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-API-Token: instagib' \
  -d '{"source_ref":"https://jackharrhy.dev/quake"}'
```

## Docker

```bash
docker build -t ghcr.io/jackharrhy/qbrain:main .
docker run --rm -p 8099:8099 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v $(pwd)/data:/app/data \
  ghcr.io/jackharrhy/qbrain:main
```
