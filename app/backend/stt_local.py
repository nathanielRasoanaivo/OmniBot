"""Local speech-to-text (faster-whisper) for the local LLM backend.

Env: OMNIBOT_STT_MODEL (default large-v3-turbo), OMNIBOT_STT_DEVICE (cuda|cpu, default cuda),
OMNIBOT_STT_LANGUAGE (ISO code, default auto-detect).
"""

from __future__ import annotations

import os
import threading
from typing import Any

import numpy as np

_model: Any = None
_lock = threading.Lock()


def _load_model():
    global _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError("faster-whisper is not installed (pip install faster-whisper)") from e
        name = (os.environ.get("OMNIBOT_STT_MODEL") or "large-v3-turbo").strip()
        device = (os.environ.get("OMNIBOT_STT_DEVICE") or "cuda").strip().lower()
        try:
            _model = WhisperModel(
                name, device=device, compute_type="float16" if device == "cuda" else "int8"
            )
        except Exception as e:
            if device == "cpu":
                raise
            print(f"[stt] {device} load failed ({e}); falling back to CPU int8", flush=True)
            _model = WhisperModel(name, device="cpu", compute_type="int8")
        return _model


def transcribe_pcm16(pcm: bytes) -> str:
    """Blocking transcription of 16 kHz mono s16le PCM."""
    if len(pcm) < 3200:  # < 0.1 s
        return ""
    audio = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0
    lang = (os.environ.get("OMNIBOT_STT_LANGUAGE") or "").strip() or None
    segments, _info = _load_model().transcribe(audio, language=lang, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()
