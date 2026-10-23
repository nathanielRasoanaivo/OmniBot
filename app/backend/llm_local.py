"""Local LLM backend: any OpenAI-compatible server (Ollama, LM Studio, llama.cpp, vLLM).

Selected with OMNIBOT_LLM_BACKEND=openai_compat. History is kept as OpenAI chat messages.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from functools import partial
from typing import Any, Awaitable, Callable, Optional

import requests

BACKEND_GEMINI = "gemini"
BACKEND_OPENAI_COMPAT = "openai_compat"

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "qwen3:14b"
MAX_HISTORY_MESSAGES = 40
REQUEST_TIMEOUT_S = 300


def backend_name() -> str:
    v = (os.environ.get("OMNIBOT_LLM_BACKEND") or BACKEND_GEMINI).strip().lower()
    return BACKEND_OPENAI_COMPAT if v in (BACKEND_OPENAI_COMPAT, "local", "ollama") else BACKEND_GEMINI


def is_local() -> bool:
    return backend_name() == BACKEND_OPENAI_COMPAT


def base_url() -> str:
    return (os.environ.get("OMNIBOT_LLM_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def model_name() -> str:
    return (os.environ.get("OMNIBOT_LLM_MODEL") or DEFAULT_MODEL).strip()


def _headers() -> dict[str, str]:
    key = (os.environ.get("OMNIBOT_LLM_API_KEY") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def tools_from_declarations(declarations: list[dict]) -> list[dict]:
    """Gemini/OpenAPI function declarations -> OpenAI `tools`."""
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


def user_message_from_content(content: Any) -> dict[str, Any]:
    """Turn a str or a list of str / genai Part into one OpenAI user message (text + images only)."""
    items = content if isinstance(content, list) else [content]
    parts: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, str):
            parts.append({"type": "text", "text": it})
            continue
        blob = getattr(it, "inline_data", None)
        mime = getattr(blob, "mime_type", "") or ""
        data = getattr(blob, "data", None)
        if data and mime.startswith("image/"):
            b64 = base64.b64encode(data).decode("ascii")
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        elif data:
            print(f"[llm-local] dropped unsupported {mime or 'binary'} part (text/image only)")
    if all(p["type"] == "text" for p in parts):
        return {"role": "user", "content": "\n".join(p["text"] for p in parts)}
    return {"role": "user", "content": parts}


def _stream_completion(messages: list[dict], tools: list[dict], model: str):
    """Blocking generator of parsed SSE chunks."""
    body: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
    with requests.post(
        f"{base_url()}/chat/completions",
        json=body,
        headers=_headers(),
        stream=True,
        timeout=REQUEST_TIMEOUT_S,
    ) as r:
        if r.status_code >= 400:
            raise RuntimeError(f"LLM server HTTP {r.status_code}: {r.text[:300]}")
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
    """One non-streaming call; returns the assistant message dict."""
    body: dict[str, Any] = {"model": model or model_name(), "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools
    r = requests.post(
        f"{base_url()}/chat/completions", json=body, headers=_headers(), timeout=REQUEST_TIMEOUT_S
    )
    if r.status_code >= 400:
        raise RuntimeError(f"LLM server HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]


def server_reachable() -> bool:
    try:
        return requests.get(f"{base_url()}/models", headers=_headers(), timeout=1).status_code < 500
    except requests.RequestException:
        return False


async def run_turn(
    *,
    history: list[dict],
    user_message: dict[str, Any],
    system_instruction: str,
    declarations: list[dict],
    execute_tool: Callable[[str, dict], Awaitable[dict]],
    on_delta: Callable[[str], Awaitable[None]],
    max_rounds: int = 6,
) -> tuple[str, list[dict]]:
    """Stream one assistant turn with tool rounds. Returns (text, new_history)."""
    loop = asyncio.get_running_loop()
    tools = tools_from_declarations(declarations)
    model = model_name()
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
            print(f"[llm-local] stream error: {e}", flush=True)
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
            result = await execute_tool(tc["function"]["name"], args if isinstance(args, dict) else {})
            msgs.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)}
            )

    return full_text, _trim(msgs)


def _trim(msgs: list[dict]) -> list[dict]:
    """Keep the last N messages, starting on a user message so tool pairs stay intact."""
    if len(msgs) <= MAX_HISTORY_MESSAGES:
        return msgs
    tail = msgs[-MAX_HISTORY_MESSAGES:]
    for i, m in enumerate(tail):
        if m.get("role") == "user":
            return tail[i:]
    return tail
