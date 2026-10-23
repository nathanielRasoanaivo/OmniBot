"""Local web search tool (SearXNG JSON API) for the local LLM backend.

Enabled when OMNIBOT_SEARXNG_URL is set, e.g. http://127.0.0.1:8080
(SearXNG needs `json` listed under `search.formats` in its settings.yml).
"""

from __future__ import annotations

import os
from typing import Any

import requests

MAX_RESULTS = 5
SNIPPET_CHARS = 400

WEB_SEARCH_DECLARATION = {
    "name": "web_search",
    "description": (
        "Search the web for current or factual information you do not know. "
        "Returns numbered sources; cite them in the answer as [1], [2]."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Concise search query."},
        },
        "required": ["query"],
    },
}


def searxng_url() -> str:
    return (os.environ.get("OMNIBOT_SEARXNG_URL") or "").strip().rstrip("/")


def is_enabled() -> bool:
    return bool(searxng_url())


def search(query: str) -> dict[str, Any]:
    """Blocking search. Returns {"ok", "results": [{n, title, uri, snippet}]} or {"ok": False, "error"}."""
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty query"}
    try:
        r = requests.get(
            f"{searxng_url()}/search",
            params={"q": q, "format": "json", "language": "auto"},
            timeout=15,
        )
        r.raise_for_status()
        raw = r.json().get("results") or []
    except (requests.RequestException, ValueError) as e:
        return {"ok": False, "error": f"search failed: {e}"}

    results = []
    for item in raw:
        uri = str(item.get("url") or "").strip()
        if not uri:
            continue
        results.append(
            {
                "n": len(results) + 1,
                "title": str(item.get("title") or "Web source").strip(),
                "uri": uri,
                "snippet": str(item.get("content") or "").strip()[:SNIPPET_CHARS],
            }
        )
        if len(results) >= MAX_RESULTS:
            break
    return {"ok": True, "query": q, "results": results}
