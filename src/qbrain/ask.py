from __future__ import annotations

import os

import httpx

from .search import search_fts


def ask(question: str, limit: int = 8) -> dict:
    hits = search_fts(question, limit=limit)
    context = "\n\n".join(
        [f"[{i+1}] {h['source_ref']}#chunk{h['chunk_index']}\n{h['snippet']}" for i, h in enumerate(hits)]
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"answer": "OPENAI_API_KEY missing; retrieval-only mode.", "hits": hits}

    prompt = (
        "You are answering from qbrain retrieval context. "
        "Be concise and include reference numbers [n].\n\n"
        f"Question: {question}\n\nContext:\n{context}"
    )

    with httpx.Client(timeout=60) as client:
        r = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"]

    return {"answer": answer, "hits": hits}
