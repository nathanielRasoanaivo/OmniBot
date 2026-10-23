"""omnibot-lite — hub web : bots virtuels à persona, chat streaming via LLM
OpenAI-compatible (Strata / Ollama), heartbeat, animations faciales exposées au navigateur.

Aucune voix, aucun Gemini, aucun firmware : tout passe par /chat/completions.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

import bots as bots_mod
import heartbeat
import llm_client
import persona
from animations import (
    FACE_ANIMATION_DISPLAY_MS,
    FACE_ANIMATION_NAMES,
    animation_catalog,
    is_valid_animation,
)
from config import DATA_DIR, hub_settings_public, llm_base_url, llm_model, update_hub_settings

app = FastAPI(title="omnibot-lite")

# ---------------------------------------------------------------------------
# Règles de base injectées (la personnalité vit dans les fichiers persona)
# ---------------------------------------------------------------------------

FACE_ANIMATION_DECLARATION = {
    "name": "face_animation",
    "description": (
        "Affiche une expression sur le visage virtuel du bot dans le dashboard, pour un état "
        "de conversation ou émotionnel uniquement. Passer un seul argument : `animation` = "
        "une des valeurs listées."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "animation": {
                "type": "string",
                "enum": list(FACE_ANIMATION_NAMES),
                "description": "Quelle animation de visage afficher.",
            },
        },
        "required": ["animation"],
    },
}

MEMORY_REPLACE_DECLARATION = {
    "name": "memory_replace",
    "description": (
        "Remplace le fichier MEMORY.md EN ENTIER par une markdown mise à jour (mémoire "
        "long terme choisie). Taille max forcée côté serveur."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "markdown": {"type": "string", "description": "Contenu complet du nouveau MEMORY.md."},
        },
        "required": ["markdown"],
    },
}

_BASE_RULES = (
    "Tu es un bot personnel hébergé par le hub omnibot-lite. Tu n'as pas de corps : ton "
    "visage est un visage virtuel animé dans le dashboard.\n\n"
    "Animation du visage :\n"
    "- Utilise l'outil `face_animation` uniquement pour des états de conversation ou des "
    "émotions. Un seul argument : `animation` = une parmi speaking, happy, mad, sad, "
    "surprised, sleepy, thinking, confused, excited, love. Au plus UNE animation par tour.\n\n"
    "Langue : réponds dans la langue de l'humain (français par défaut)."
)

BOOTSTRAP_BASE_RULES = (
    "Tu pilotes le rituel de naissance d'un bot personnel sans nom ni identité fixés : "
    "n'affirme aucun nom avant que l'humain et toi l'ayez choisi et écrit dans les fichiers "
    "persona.\n\n" + _BASE_RULES
)

BOOTSTRAP_MODE_SYSTEM_SUFFIX = (
    "Le rituel **Give me a soul** est actif. Suis BOOTSTRAP.md ci-dessous. Ne pose qu'une "
    "ou deux questions par réponse, laisse l'humain décider. Mets à jour IDENTITY.md / "
    "USER.md / SOUL.md avec les outils dès que des choix sont faits, et annonce chaque "
    "fichier modifié. Quand le rituel est terminé, appelle bootstrap_complete."
)

# ---------------------------------------------------------------------------
# Connexions frontend (WebSocket /ws/monitor)
# ---------------------------------------------------------------------------


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str)
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Historiques de chat (persistés) + verrous par bot
# ---------------------------------------------------------------------------

HISTORY_DIR = DATA_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

history_by_device: dict[str, list[dict]] = {}
turn_locks: dict[str, asyncio.Lock] = {}
turn_state: dict[str, dict[str, Any]] = {}  # did -> {"turn_id":..., "face_used": bool}


def _history_path(device_id: str):
    return HISTORY_DIR / f"{persona.safe_device_id(device_id)}.json"


def load_history(device_id: str) -> list[dict]:
    if device_id in history_by_device:
        return history_by_device[device_id]
    try:
        data = json.loads(_history_path(device_id).read_text(encoding="utf-8"))
        history_by_device[device_id] = data if isinstance(data, list) else []
    except Exception:
        history_by_device[device_id] = []
    return history_by_device[device_id]


def save_history(device_id: str) -> None:
    try:
        _history_path(device_id).write_text(
            json.dumps(history_by_device.get(device_id, []), ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[history] sauvegarde impossible {device_id!r}: {e}")


def history_for_ui(device_id: str) -> list[dict[str, Any]]:
    """Messages user/assistant textuels seulement, pour affichage."""
    out = []
    for m in load_history(device_id):
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            continue
        out.append({"role": role, "content": content})
    return out


# ---------------------------------------------------------------------------
# Outils persona pour le chat
# ---------------------------------------------------------------------------


def _chat_declarations() -> list[dict]:
    return [
        FACE_ANIMATION_DECLARATION,
        persona.SOUL_REPLACE_DECLARATION,
        MEMORY_REPLACE_DECLARATION,
        persona.PERSONA_REPLACE_DECLARATION,
        persona.DAILY_LOG_APPEND_DECLARATION,
        persona.BOOTSTRAP_COMPLETE_DECLARATION,
    ]


async def _broadcast_face_animation(device_id: str, animation: str, turn_id: Optional[str]) -> None:
    await manager.broadcast({
        "type": "face_animation",
        "device_id": device_id,
        "animation": animation,
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "turn_id": turn_id,
    })


def _make_execute_tool(device_id: str, turn_id: str):
    async def execute_tool(name: str, args: dict) -> dict:
        st = turn_state.setdefault(device_id, {"turn_id": turn_id, "face_used": False})
        if name == "face_animation":
            a = (args.get("animation") or "").strip().lower()
            if not is_valid_animation(a):
                return {"ok": False, "error": f"animation inconnue : {a!r}"}
            if st.get("face_used"):
                return {"ok": False, "reason": "une animation a déjà été jouée ce tour"}
            st["face_used"] = True
            await _broadcast_face_animation(device_id, a, turn_id)
            return {"ok": True, "display": f"animation {a} jouée sur le visage du bot"}
        if name == "soul_replace":
            res = persona.replace_soul_markdown(device_id, str(args.get("markdown") or ""))
            if res.get("ok"):
                await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": "soul"})
            return res
        if name == "memory_replace":
            res = persona.replace_memory_markdown(device_id, str(args.get("markdown") or ""))
            if res.get("ok"):
                await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": "memory"})
            return res
        if name == "persona_replace":
            res = persona.replace_persona_target_markdown(
                device_id, str(args.get("file") or ""), str(args.get("markdown") or "")
            )
            if res.get("ok"):
                await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": res.get("file")})
            return res
        if name == "daily_log_append":
            return persona.append_daily_log_line(device_id, str(args.get("line") or ""))
        if name == "bootstrap_complete":
            return persona.delete_bootstrap_file(device_id)
        return {"ok": False, "error": f"outil inconnu : {name}"}

    return execute_tool


# ---------------------------------------------------------------------------
# Tours de chat (normal + bootstrap)
# ---------------------------------------------------------------------------


async def _run_chat_turn(
    device_id: str,
    turn_id: str,
    user_text: str,
    *,
    bootstrap: bool = False,
) -> None:
    lock = turn_locks.setdefault(device_id, asyncio.Lock())
    try:
        async with lock:
            turn_state[device_id] = {"turn_id": turn_id, "face_used": False}
            await manager.broadcast({
                "type": "processing_started",
                "device_id": device_id,
                "turn_id": turn_id,
                "bootstrap": bootstrap,
            })
            if not llm_client.server_reachable():
                await manager.broadcast({
                    "type": "chat_error",
                    "device_id": device_id,
                    "turn_id": turn_id,
                    "error": f"Serveur LLM injoignable : {llm_base_url()}",
                })
                return

            display_name = (bots_mod.list_known_bots().get(device_id) or {}).get("display_name") or device_id
            base_rules = BOOTSTRAP_BASE_RULES if bootstrap else _BASE_RULES + (
                f"\n\n(Ton nom affiché dans le hub : {display_name})"
            )
            sys_instr = persona.build_composed_system_instruction(
                device_id,
                base_rules,
                extra_system_suffix=BOOTSTRAP_MODE_SYSTEM_SUFFIX if bootstrap else "",
                use_neutral_hub_rules_header=True,
            )

            async def on_delta(piece: str) -> None:
                await manager.broadcast({
                    "type": "chat_delta", "device_id": device_id, "turn_id": turn_id, "text": piece,
                })

            async def on_tool_call(name: str, args: dict) -> None:
                summary = ""
                if name == "face_animation":
                    summary = str(args.get("animation") or "")
                elif name in ("soul_replace", "memory_replace", "persona_replace"):
                    summary = str(args.get("file") or "") or f"{len(str(args.get('markdown') or ''))} octets"
                elif name == "daily_log_append":
                    summary = str(args.get("line") or "")[:120]
                await manager.broadcast({
                    "type": "tool_call", "device_id": device_id, "turn_id": turn_id,
                    "name": name, "summary": summary,
                })

            full_text, new_history = await llm_client.run_turn(
                history=load_history(device_id),
                user_message={"role": "user", "content": user_text},
                system_instruction=sys_instr,
                declarations=_chat_declarations(),
                execute_tool=_make_execute_tool(device_id, turn_id),
                on_delta=on_delta,
                on_tool_call=on_tool_call,
                max_rounds=10 if bootstrap else 6,
            )
            history_by_device[device_id] = new_history
            save_history(device_id)
            await manager.broadcast({
                "type": "chat_done", "device_id": device_id, "turn_id": turn_id, "text": full_text,
            })
    except Exception as e:
        print(f"[chat] erreur tour {device_id!r}: {e}")
        await manager.broadcast({
            "type": "chat_error", "device_id": device_id, "turn_id": turn_id, "error": str(e),
        })
    finally:
        turn_state.pop(device_id, None)


# ---------------------------------------------------------------------------
# Modèles de requêtes
# ---------------------------------------------------------------------------


class CreateBotBody(BaseModel):
    display_name: str


class RenameBotBody(BaseModel):
    display_name: str


class BotSettingsBody(BaseModel):
    model: Optional[str] = None
    heartbeat_enabled: Optional[bool] = None
    heartbeat_interval_minutes: Optional[int] = None


class ChatBody(BaseModel):
    message: str


class FaceAnimationBody(BaseModel):
    animation: str
    duration_ms: Optional[int] = None


class HubSettingsBody(BaseModel):
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# API : statut, bots, réglages
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "llm_base_url": llm_base_url(),
        "llm_model": llm_model(),
        "llm_reachable": llm_client.server_reachable(),
        "llm_models": llm_client.list_models() if llm_client.server_reachable() else [],
        "data_dir": str(DATA_DIR),
    }


@app.get("/api/bots")
async def get_bots():
    return {"bots": bots_mod.list_bots_public()}


@app.post("/api/bots")
async def post_create_bot(body: CreateBotBody):
    bot = bots_mod.create_bot(body.display_name)
    persona.ensure_persona_layout(bot["device_id"])
    await manager.broadcast({"type": "bots_changed"})
    return bot


@app.post("/api/bots/{device_id}/rename")
async def post_rename_bot(device_id: str, body: RenameBotBody):
    meta = bots_mod.rename_bot(device_id, body.display_name)
    if meta is None:
        raise HTTPException(status_code=404, detail="Bot inconnu")
    await manager.broadcast({"type": "bots_changed"})
    return meta


@app.delete("/api/bots/{device_id}")
async def delete_bot(device_id: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    known = bots_mod.list_known_bots()
    known.pop(device_id, None)
    bots_mod._write_json(bots_mod.KNOWN_BOTS_FILE, known)
    settings = bots_mod._read_json(bots_mod.BOT_SETTINGS_FILE)
    settings.pop(device_id, None)
    bots_mod._write_json(bots_mod.BOT_SETTINGS_FILE, settings)
    history_by_device.pop(device_id, None)
    turn_locks.pop(device_id, None)
    try:
        _history_path(device_id).unlink(missing_ok=True)
    except OSError:
        pass
    shutil.rmtree(persona.persona_root_dir(device_id), ignore_errors=True)
    await manager.broadcast({"type": "bots_changed"})
    return {"ok": True}


@app.get("/api/bots/{device_id}/settings")
async def get_bot_settings(device_id: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    return bots_mod.get_bot_settings(device_id)


@app.post("/api/bots/{device_id}/settings")
async def post_bot_settings(device_id: str, body: BotSettingsBody):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    return bots_mod.update_bot_settings(device_id, body.model_dump())


# ---------------------------------------------------------------------------
# API : chat, historique, bootstrap
# ---------------------------------------------------------------------------

_active_turns: dict[str, str] = {}  # device_id -> turn_id en cours


@app.get("/api/bots/{device_id}/history")
async def get_history(device_id: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    return {"messages": history_for_ui(device_id), "processing": device_id in _active_turns}


@app.post("/api/bots/{device_id}/chat")
async def post_chat(device_id: str, body: ChatBody):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide")
    if device_id in _active_turns:
        raise HTTPException(status_code=409, detail="Le bot traite déjà un tour")
    turn_id = f"t{len(_active_turns)}{id(body):x}"
    _active_turns[device_id] = turn_id

    async def _wrapped():
        try:
            await _run_chat_turn(device_id, turn_id, message)
        finally:
            _active_turns.pop(device_id, None)

    asyncio.get_running_loop().create_task(_wrapped())
    return {"ok": True, "turn_id": turn_id}


@app.post("/api/bots/{device_id}/chat/reset")
async def post_chat_reset(device_id: str):
    history_by_device[device_id] = []
    save_history(device_id)
    return {"ok": True}


@app.post("/api/bots/{device_id}/bootstrap")
async def post_bootstrap(device_id: str):
    """Rituel Give me a soul : reset persona, log vierge, BOOTSTRAP.md, premier tour."""
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    if device_id in _active_turns:
        raise HTTPException(status_code=409, detail="Le bot traite déjà un tour")
    persona.reset_persona_markdown_to_templates(device_id)
    persona.clear_daily_logs_and_heartbeat_state(device_id)
    persona.write_bootstrap_markdown(device_id, persona.TEMPLATE_BOOTSTRAP)
    history_by_device[device_id] = []
    save_history(device_id)
    ritual_msg = (
        "L'humain a lancé le rituel **Donne-moi une âme** depuis le hub. "
        "Suis BOOTSTRAP.md ci-dessous et tes instructions de bootstrap.\n\n"
        "=== BOOTSTRAP.md ===\n" + persona.TEMPLATE_BOOTSTRAP
    )
    turn_id = f"b{id(ritual_msg):x}"
    _active_turns[device_id] = turn_id

    async def _wrapped():
        try:
            await _run_chat_turn(device_id, turn_id, ritual_msg, bootstrap=True)
        finally:
            _active_turns.pop(device_id, None)

    asyncio.get_running_loop().create_task(_wrapped())
    return {"ok": True, "turn_id": turn_id}


# ---------------------------------------------------------------------------
# API : persona
# ---------------------------------------------------------------------------


@app.get("/api/persona/{device_id}/status")
async def get_persona_status(device_id: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    return persona.persona_status(device_id)


@app.get("/api/persona/{device_id}/{file}")
async def get_persona_file(device_id: str, file: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    name = persona.parse_persona_api_file(file)
    if name is None:
        raise HTTPException(status_code=400, detail="Fichier persona inconnu")
    return {"file": name, "markdown": persona.read_persona_markdown(device_id, name)}


@app.put("/api/persona/{device_id}/{file}")
async def put_persona_file(device_id: str, file: str, body: dict):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    name = persona.parse_persona_api_file(file)
    if name is None:
        raise HTTPException(status_code=400, detail="Fichier persona inconnu")
    md = str(body.get("markdown") or "")
    if len(md.encode("utf-8")) > persona.PERSONA_MARKDOWN_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Contenu trop volumineux")
    persona.write_persona_markdown(device_id, name, md)
    await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": name})
    return {"ok": True, "bytes": len(md.encode("utf-8"))}


@app.post("/api/bots/{device_id}/reset-persona")
async def post_reset_persona(device_id: str):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    res = persona.reset_persona_markdown_to_templates(device_id)
    await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": "*"})
    return res


# ---------------------------------------------------------------------------
# API : animations
# ---------------------------------------------------------------------------


@app.get("/api/animations")
async def get_animations():
    return {"animations": animation_catalog()}


@app.post("/api/bots/{device_id}/face-animation")
async def post_face_animation(device_id: str, body: FaceAnimationBody):
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    a = (body.animation or "").strip().lower()
    if not is_valid_animation(a) or a == "idle":
        raise HTTPException(status_code=400, detail="Animation inconnue")
    dur = body.duration_ms or FACE_ANIMATION_DISPLAY_MS
    dur = max(250, min(15000, int(dur)))
    await manager.broadcast({
        "type": "face_animation", "device_id": device_id,
        "animation": a, "duration_ms": dur, "turn_id": None,
    })
    return {"ok": True, "animation": a, "duration_ms": dur}


# ---------------------------------------------------------------------------
# API : réglages hub
# ---------------------------------------------------------------------------


@app.get("/api/hub/settings")
async def get_hub_settings():
    return hub_settings_public()


@app.post("/api/hub/settings")
async def post_hub_settings(body: HubSettingsBody):
    update_hub_settings(**body.model_dump())
    return hub_settings_public()


@app.post("/api/bots/{device_id}/heartbeat/run")
async def post_heartbeat_run(device_id: str):
    """Force une passe de heartbeat immédiate (test UI)."""
    if not bots_mod.bot_exists(device_id):
        raise HTTPException(status_code=404, detail="Bot inconnu")
    if device_id in _active_turns:
        raise HTTPException(status_code=409, detail="Le bot traite déjà un tour")
    lock = turn_locks.setdefault(device_id, asyncio.Lock())
    async with lock:
        updated = await heartbeat.run_heartbeat_tick(device_id)
    await manager.broadcast({"type": "persona_file_changed", "device_id": device_id, "file": "memory"})
    return {"ok": True, "memory_updated": updated}


# ---------------------------------------------------------------------------
# WebSocket frontend
# ---------------------------------------------------------------------------


@app.websocket("/ws/monitor")
async def ws_monitor(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Frontend buildé (SPA) — si présent, servi sur la même origine
# ---------------------------------------------------------------------------

import os
from pathlib import Path

STATIC_DIR = Path(
    os.environ.get("OMNIBOT_STATIC_DIR") or (Path(__file__).resolve().parent.parent / "frontend" / "dist")
)

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith("api/") or full_path == "ws":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(STATIC_DIR.resolve())):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")


# ---------------------------------------------------------------------------
# Démarrage
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def on_startup():
    def hb_event(device_id: str, updated: bool) -> None:
        try:
            asyncio.get_running_loop().create_task(
                manager.broadcast({"type": "heartbeat_done", "device_id": device_id, "memory_updated": updated})
            )
        except RuntimeError:
            pass

    app.state.heartbeat_task = asyncio.create_task(
        heartbeat.heartbeat_supervisor_loop(bots_mod.get_bot_settings, turn_locks, hb_event)
    )


@app.on_event("shutdown")
async def on_shutdown():
    task = getattr(app.state, "heartbeat_task", None)
    if task:
        task.cancel()
