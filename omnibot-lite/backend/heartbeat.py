"""Passe de maintenance HEARTBEAT périodique : fusion des journaux quotidiens dans
MEMORY.md via memory_replace (backend OpenAI-compatible uniquement).

Adapté de app/backend/heartbeat_service.py du projet OmniBot (branche Gemini retirée).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, Optional

import llm_client
from persona import (
    build_composed_system_instruction,
    get_heartbeat_state,
    list_all_device_ids_for_heartbeat,
    read_heartbeat_instructions,
    read_persona_markdown,
    replace_memory_markdown,
    set_heartbeat_state,
    tail_recent_daily_logs,
)

MEMORY_REPLACE_DECLARATION = {
    "name": "memory_replace",
    "description": (
        "Replace the entire MEMORY.md file with updated curated markdown. "
        "Use when consolidating daily logs or fixing memory (MEMORY.md only in this maintenance pass). "
        "Max size enforced server-side."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "Full new body for MEMORY.md (complete file).",
            },
        },
        "required": ["markdown"],
    },
}


def _base_rules_for_heartbeat() -> str:
    return (
        "Tu es le cerveau de maintenance du hub pour ce bot. Suis HEARTBEAT.md et lis "
        "RECENT_DAILY_LOGS dans le message user. Tu ne peux modifier que MEMORY.md (via "
        "memory_replace). N'utilise pas soul_replace dans cette passe ; SOUL, IDENTITY, "
        "USER et TOOLS sont hors sujet. N'invente aucun fait. Sois concis : l'humain ne "
        "voit pas ce tour."
    )


def _run_heartbeat_sync(device_id: str, sys_instr: str, user_msg: str) -> bool:
    tools = llm_client.tools_from_declarations([MEMORY_REPLACE_DECLARATION])
    msgs: list[dict] = [
        {"role": "system", "content": sys_instr},
        {"role": "user", "content": user_msg},
    ]
    memory_updated = False
    for _ in range(5):
        reply = llm_client.complete_blocking(msgs, tools)
        calls = reply.get("tool_calls") or []
        msgs.append({"role": "assistant", "content": reply.get("content") or "", "tool_calls": calls})
        if not calls:
            break
        for tc in calls:
            fn = tc.get("function") or {}
            if fn.get("name") != "memory_replace":
                result: dict = {"ok": False, "error": "unknown function"}
            else:
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = replace_memory_markdown(device_id, str(args.get("markdown") or ""))
                memory_updated = memory_updated or bool(result.get("ok"))
            msgs.append(
                {"role": "tool", "tool_call_id": tc.get("id", ""), "content": json.dumps(result)}
            )
    return memory_updated


async def run_heartbeat_tick(device_id: str) -> bool:
    """Une passe de maintenance. Renvoie True si MEMORY.md a été mis à jour."""
    hb_text = read_heartbeat_instructions(device_id)
    logs_tail = tail_recent_daily_logs(device_id)
    memory_current = read_persona_markdown(device_id, "memory")

    user_msg = (
        "Lance ta passe HEARTBEAT maintenant.\n\n"
        f"=== HEARTBEAT_MD ===\n{hb_text}\n\n"
        f"=== RECENT_DAILY_LOGS ===\n{logs_tail}\n\n"
        f"=== CURRENT_MEMORY_MD ===\n{memory_current}\n"
    )
    sys_instr = build_composed_system_instruction(
        device_id,
        _base_rules_for_heartbeat(),
        for_heartbeat_maintenance=True,
    )
    try:
        updated = await asyncio.get_running_loop().run_in_executor(
            None, partial(_run_heartbeat_sync, device_id, sys_instr, user_msg)
        )
        set_heartbeat_state(
            device_id,
            last_run_utc=datetime.now(timezone.utc).isoformat(),
            last_memory_updated=updated,
        )
        return updated
    except Exception as e:
        print(f"[heartbeat] device_id={device_id!r} erreur : {e}")
        set_heartbeat_state(
            device_id,
            last_run_utc=datetime.now(timezone.utc).isoformat(),
            last_error=str(e),
        )
        return False


async def heartbeat_supervisor_loop(
    get_bot_settings_fn: Callable[[str], dict[str, Any]],
    turn_locks: dict[str, asyncio.Lock],
    on_event: Optional[Callable[[str, bool], Any]] = None,
) -> None:
    """Se réveille toutes les 60 s ; lance une passe par bot dont l'intervalle est échu."""
    while True:
        try:
            await asyncio.sleep(60.0)
            for device_id in list_all_device_ids_for_heartbeat():
                bs = get_bot_settings_fn(device_id)
                if not bs.get("heartbeat_enabled", True):
                    continue
                interval_min = max(1, int(bs.get("heartbeat_interval_minutes", 60) or 60))
                st = get_heartbeat_state(device_id)
                last = st.get("last_run_utc")
                now = datetime.now(timezone.utc)
                need = False
                if not last:
                    need = True
                else:
                    try:
                        lp = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                        if lp.tzinfo is None:
                            lp = lp.replace(tzinfo=timezone.utc)
                        if (now - lp).total_seconds() >= interval_min * 60:
                            need = True
                    except Exception:
                        need = True
                if not need:
                    continue
                lock = turn_locks.setdefault(device_id, asyncio.Lock())
                async with lock:
                    if on_event is not None:
                        on_event(device_id, True)
                    updated = await run_heartbeat_tick(device_id)
                    if on_event is not None:
                        on_event(device_id, updated)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[heartbeat] superviseur : {e}")
            await asyncio.sleep(5.0)
