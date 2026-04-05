from __future__ import annotations

import os
import struct

import httpx

OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


def embed_text(text: str, model: str | None = None) -> tuple[str, list[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = model or os.getenv("QBRAIN_EMBED_MODEL", "text-embedding-3-small")

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            OPENAI_EMBED_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        vec = data["data"][0]["embedding"]
        return model, vec


def vec_to_blob(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)
