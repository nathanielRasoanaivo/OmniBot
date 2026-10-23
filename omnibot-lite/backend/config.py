"""Configuration du hub omnibot-lite : dossier de données + réglages LLM."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent

try:  # .env optionnel à côté du backend (dev local)
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def _resolve_data_dir() -> Path:
    env = (os.environ.get("OMNIBOT_DATA_DIR") or "").strip()
    if env:
        p = Path(env).expanduser()
    else:
        p = BASE_DIR / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


DATA_DIR: Path = _resolve_data_dir()

# Réglages LLM modifiables via l'UI (hub_settings.json), valeurs d'environnement comme défauts.
HUB_SETTINGS_FILE = DATA_DIR / "hub_settings.json"

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "default"

_settings_cache: tuple[float, dict[str, Any]] | None = None
_settings_lock = threading.Lock()


def _read_hub_settings() -> dict[str, Any]:
    global _settings_cache
    with _settings_lock:
        try:
            mtime = HUB_SETTINGS_FILE.stat().st_mtime
        except OSError:
            _settings_cache = None
            return {}
        if _settings_cache and _settings_cache[0] == mtime:
            return _settings_cache[1]
        try:
            data = json.loads(HUB_SETTINGS_FILE.read_text(encoding="utf-8"))
            data = data if isinstance(data, dict) else {}
        except Exception:
            data = {}
        _settings_cache = (mtime, data)
        return data


def update_hub_settings(**updates: Any) -> dict[str, Any]:
    """Fusionne et écrit hub_settings.json ; renvoie les réglages complets."""
    global _settings_cache
    with _settings_lock:
        try:
            cur = json.loads(HUB_SETTINGS_FILE.read_text(encoding="utf-8"))
            cur = cur if isinstance(cur, dict) else {}
        except Exception:
            cur = {}
        cur.update({k: v for k, v in updates.items() if v is not None})
        HUB_SETTINGS_FILE.write_text(json.dumps(cur, indent=2), encoding="utf-8")
        _settings_cache = (HUB_SETTINGS_FILE.stat().st_mtime, cur)
        return cur


def llm_base_url() -> str:
    s = _read_hub_settings()
    v = str(s.get("llm_base_url") or "").strip() or (os.environ.get("OMNIBOT_LLM_BASE_URL") or DEFAULT_BASE_URL)
    return v.strip().rstrip("/")


def llm_model() -> str:
    s = _read_hub_settings()
    v = str(s.get("llm_model") or "").strip()
    if not v:
        v = (os.environ.get("OMNIBOT_LLM_MODEL") or "").strip()
    return v or DEFAULT_MODEL


def llm_api_key() -> str:
    s = _read_hub_settings()
    v = str(s.get("llm_api_key") or "").strip()
    if not v:
        v = (os.environ.get("OMNIBOT_LLM_API_KEY") or "").strip()
    return v


def hub_settings_public() -> dict[str, Any]:
    """Réglages pour l'UI ; la clé n'est renvoyée que masquée."""
    key = llm_api_key()
    return {
        "llm_base_url": llm_base_url(),
        "llm_model": llm_model(),
        "llm_api_key_set": bool(key),
        "llm_api_key_masked": (key[:4] + "…" + key[-4:]) if len(key) > 8 else ("•" * len(key) if key else ""),
    }
