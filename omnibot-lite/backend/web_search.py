"""Outil web_search pour omnibot-lite : recherche web live via l'API Tavily.

Activé seulement quand TAVILY_API_KEY est défini (sinon l'outil n'est pas
proposé au LLM). L'URL de l'API est écrasable via TAVILY_SEARCH_URL (tests).

Le CLI `tvly` n'est PAS utilisé ici : c'est un outil pour agent de codage ;
le runtime du hub passe directement par l'API REST Tavily.
"""

from __future__ import annotations

import os
from typing import Any

import requests

DEFAULT_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_SNIPPET_MAX_CHARS = 500


WEB_SEARCH_DECLARATION = {
    "name": "web_search",
    "description": (
        "Cherche sur le web des informations actuelles que tu ne peux pas connaître : "
        "actualités, prix, versions de logiciels, météo, faits récents. Renvoie une réponse "
        "synthétique et des résultats (titre, URL, extrait). Cite les URL des sources dans "
        "ta réponse quand tu utilises cet outil."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Requête de recherche, courte et précise.",
            },
            "max_results": {
                "type": "integer",
                "description": "Nombre de résultats souhaités, de 1 à 8 (défaut 5).",
            },
        },
        "required": ["query"],
    },
}


def api_key() -> str:
    return (os.environ.get("TAVILY_API_KEY") or "").strip()


def is_enabled() -> bool:
    return bool(api_key())


def _search_url() -> str:
    return (os.environ.get("TAVILY_SEARCH_URL") or "").strip() or DEFAULT_TAVILY_SEARCH_URL


def execute(args: dict[str, Any]) -> dict[str, Any]:
    """Exécute une recherche Tavily ; blocant (à appeler via to_thread)."""
    key = api_key()
    if not key:
        return {"ok": False, "error": "TAVILY_API_KEY non configurée côté hub"}
    query = str(args.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "query vide"}
    try:
        n = int(args.get("max_results") or 5)
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(8, n))

    try:
        r = requests.post(
            _search_url(),
            headers={"Authorization": f"Bearer {key}"},
            json={"query": query, "max_results": n, "include_answer": True},
            timeout=20,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": f"requête Tavily impossible : {e}"}
    if r.status_code != 200:
        return {"ok": False, "error": f"Tavily a répondu HTTP {r.status_code}"}
    try:
        data = r.json()
    except ValueError:
        return {"ok": False, "error": "réponse Tavily illisible"}

    results = [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "snippet": str(item.get("content") or "")[:_SNIPPET_MAX_CHARS],
        }
        for item in (data.get("results") or [])[:n]
    ]
    return {
        "ok": True,
        "query": query,
        "answer": str(data.get("answer") or ""),
        "results": results,
    }
