"""Registre des bots virtuels + réglages par bot (JSON sous DATA_DIR)."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR
from animations import is_valid_animation

KNOWN_BOTS_FILE = DATA_DIR / "known_bots.json"
BOT_SETTINGS_FILE = DATA_DIR / "bot_settings.json"

DEFAULT_HEARTBEAT_INTERVAL_MINUTES = 60
DEFAULT_HEARTBEAT_ENABLED = True


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", (name or "").strip().lower())
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "bot"


def _unique_slug(known: dict[str, Any], base: str) -> str:
    slug = base
    n = 2
    while slug in known:
        slug = f"{base}_{n}"
        n += 1
    return slug


def list_known_bots() -> dict[str, Any]:
    return _read_json(KNOWN_BOTS_FILE)


def list_bots_public() -> list[dict[str, Any]]:
    known = list_known_bots()
    settings = _read_json(BOT_SETTINGS_FILE)
    out = []
    for did, meta in sorted(known.items()):
        out.append({
            "device_id": did,
            "display_name": meta.get("display_name") or did,
            "created_utc": meta.get("created_utc"),
            "settings": default_settings(did) | (settings.get(did) or {}),
        })
    return out


def default_settings(device_id: str) -> dict[str, Any]:
    return {
        "model": "",  # vide = modèle global du hub
        "heartbeat_enabled": DEFAULT_HEARTBEAT_ENABLED,
        "heartbeat_interval_minutes": DEFAULT_HEARTBEAT_INTERVAL_MINUTES,
        "default_face": "idle",  # humeur de fond du visage : état vers lequel le bot retombe
    }


def get_bot_settings(device_id: str) -> dict[str, Any]:
    settings = _read_json(BOT_SETTINGS_FILE)
    return default_settings(device_id) | (settings.get(device_id) or {})


def update_bot_settings(device_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    settings = _read_json(BOT_SETTINGS_FILE)
    row = default_settings(device_id) | (settings.get(device_id) or {})
    for k in ("model", "heartbeat_enabled", "heartbeat_interval_minutes", "default_face"):
        if k in updates and updates[k] is not None:
            row[k] = updates[k]
    row["heartbeat_interval_minutes"] = max(5, min(720, int(row.get("heartbeat_interval_minutes") or 60)))
    df = str(row.get("default_face") or "idle").strip().lower()
    row["default_face"] = df if df == "idle" or is_valid_animation(df) else "idle"
    settings[device_id] = row
    _write_json(BOT_SETTINGS_FILE, settings)
    return row


def create_bot(display_name: str) -> dict[str, Any]:
    name = (display_name or "").strip() or "Nouveau bot"
    known = list_known_bots()
    device_id = _unique_slug(known, slugify(name))
    now = datetime.now(timezone.utc).isoformat()
    known[device_id] = {"display_name": name, "created_utc": now}
    _write_json(KNOWN_BOTS_FILE, known)
    update_bot_settings(device_id, {})
    return {
        "device_id": device_id,
        "display_name": name,
        "created_utc": now,
        "settings": get_bot_settings(device_id),
    }


def rename_bot(device_id: str, display_name: str) -> dict[str, Any] | None:
    known = list_known_bots()
    if device_id not in known:
        return None
    known[device_id]["display_name"] = (display_name or "").strip() or device_id
    _write_json(KNOWN_BOTS_FILE, known)
    return known[device_id]


def bot_exists(device_id: str) -> bool:
    return device_id in list_known_bots()
