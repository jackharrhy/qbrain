from __future__ import annotations

import re
from urllib.parse import urljoin

URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


def extract_links(raw_text: str, base_url: str | None = None) -> list[str]:
    links: set[str] = set()

    for m in URL_RE.finditer(raw_text or ""):
        links.add(m.group(0).strip())

    for m in MD_LINK_RE.finditer(raw_text or ""):
        links.add(m.group(1).strip())

    cleaned: list[str] = []
    for link in links:
        if base_url and link.startswith("/"):
            link = urljoin(base_url, link)
        cleaned.append(link)

    # deterministic order for stable outputs
    return sorted(set(cleaned))
