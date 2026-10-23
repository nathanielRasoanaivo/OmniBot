"""Client LLM OpenAI-compatible (Strata, Ollama, LM Studio, vLLM…).

Adapté de app/backend/llm_local.py du projet OmniBot : streaming SSE + rounds
d'appels d'outils, historique en messages OpenAI. Aucune dépendance Gemini.
"""

from __future__ import annotations

import asyncio
import json
from functools import partial
from typing import Any, Awaitable, Callable, Optional

import requests

from config import llm_api_key, llm_base_url, llm_model

MAX_HISTORY_MESSAGES = 40
REQUEST_TIMEOUT_S = 300


def _headers() -> dict[str, str]:
    key = llm_api_key()
    return {"Authorization": f"Bearer {key}"} if key else {}


def tools_from_declarations(declarations: list[dict]) -> list[dict]:
    """Déclarations de fonctions style OpenAPI -> `tools` OpenAI."""
    return [
        {
            "type": "function",
            "function": {
                "name": d["name"],
                "description": d.get("description", ""),
                "parameters": d.get("parameters") or {"type": "object", "properties": {}},
            },
        }
        for d in declarations
    ]


def _stream_completion(messages: list[dict], tools: list[dict], model: str):
    """Générateur bloquant de chunks SSE analysés."""
    body: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
    with requests.post(
        f"{llm_base_url()}/chat/completions",
        json=body,
        headers=_headers(),
        stream=True,
        timeout=REQUEST_TIMEOUT_S,
    ) as r:
        if r.status_code >= 400:
            raise RuntimeError(f"Serveur LLM HTTP {r.status_code} : {r.text[:300]}")
        # Les serveurs SSE (text/event-stream) n'annoncent pas toujours utf-8 ;
        # requests tomberait sinon sur ISO-8859-1 et corromprait les accents.
        r.encoding = "utf-8"
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                continue


def complete_blocking(messages: list[dict], tools: list[dict], model: Optional[str] = None) -> dict[str, Any]:
    """Appel non-streaming ; renvoie le message assistant (dict OpenAI)."""
    body: dict[str, Any] = {"model": model or llm_model(), "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools
    r = requests.post(
        f"{llm_base_url()}/chat/completions", json=body, headers=_headers(), timeout=REQUEST_TIMEOUT_S
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Serveur LLM HTTP {r.status_code} : {r.text[:300]}")
    return r.json()["choices"][0]["message"]


def server_reachable() -> bool:
    try:
        return requests.get(f"{llm_base_url()}/models", headers=_headers(), timeout=3).status_code < 500
    except requests.RequestException:
        return False


def list_models() -> list[str]:
    """Modèles servis (best effort ; Strata accepte n'importe quel nom)."""
    try:
        r = requests.get(f"{llm_base_url()}/models", headers=_headers(), timeout=5)
        r.raise_for_status()
        items = r.json().get("data") or []
        return [str(i.get("id")) for i in items if i.get("id")]
    except Exception:
        return []


async def run_turn(
    *,
    history: list[dict],
    user_message: dict[str, Any],
    system_instruction: str,
    declarations: list[dict],
    execute_tool: Callable[[str, dict], Awaitable[dict]],
    on_delta: Callable[[str], Awaitable[None]],
    on_tool_call: Optional[Callable[[str, dict], Awaitable[None]]] = None,
    max_rounds: int = 6,
) -> tuple[str, list[dict]]:
    """Un tour assistant en streaming avec rounds d'outils. Renvoie (texte, nouvel_historique)."""
    loop = asyncio.get_running_loop()
    tools = tools_from_declarations(declarations)
    model = llm_model()
    msgs = list(history) + [user_message]
    full_text = ""

    for _ in range(max(1, max_rounds)):
        payload = [{"role": "system", "content": system_instruction}] + msgs
        stream = _stream_completion(payload, tools, model)
        text = ""
        calls: dict[int, dict[str, Any]] = {}
        try:
            while True:
                chunk = await loop.run_in_executor(None, partial(next, stream, None))
                if chunk is None:
                    break
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    text += piece
                    full_text += piece
                    await on_delta(piece)
                for tc in delta.get("tool_calls") or []:
                    slot = calls.setdefault(
                        tc.get("index", 0), {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = fn["name"]
                    slot["arguments"] += fn.get("arguments") or ""
        except Exception as e:
            print(f"[llm] erreur de flux : {e}", flush=True)
            if not text and not calls:
                raise
        finally:
            stream.close()

        ordered = [calls[i] for i in sorted(calls) if calls[i]["name"]]
        assistant: dict[str, Any] = {"role": "assistant", "content": text}
        if ordered:
            assistant["tool_calls"] = [
                {
                    "id": c["id"] or f"call_{i}",
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["arguments"] or "{}"},
                }
                for i, c in enumerate(ordered)
            ]
        msgs.append(assistant)
        if not ordered:
            break

        for tc in assistant["tool_calls"]:
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            if on_tool_call is not None:
                await on_tool_call(tc["function"]["name"], args)
            result = await execute_tool(tc["function"]["name"], args)
            msgs.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)}
            )

    return full_text, trim_history(msgs)


def trim_history(msgs: list[dict]) -> list[dict]:
    """Garde les N derniers messages en démarrant sur un message user (paires tool intactes)."""
    if len(msgs) <= MAX_HISTORY_MESSAGES:
        return msgs
    tail = msgs[-MAX_HISTORY_MESSAGES:]
    for i, m in enumerate(tail):
        if m.get("role") == "user":
            return tail[i:]
    return tail
