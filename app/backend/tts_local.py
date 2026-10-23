"""Local text-to-speech (Kokoro) for the local LLM backend. Output: PCM s16le mono 24 kHz.

Env: OMNIBOT_TTS_LANG (Kokoro lang code, default "f" = French), OMNIBOT_TTS_VOICE (default ff_siwis).
"""

from __future__ import annotations

import os
import re
import threading
from typing import Any, Iterator

import numpy as np

SAMPLE_RATE = 24000

_pipeline: Any = None
_lock = threading.Lock()
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def _load_pipeline():
    global _pipeline
    with _lock:
        if _pipeline is not None:
            return _pipeline
        try:
            from kokoro import KPipeline
        except ImportError as e:
            raise RuntimeError("kokoro is not installed (pip install kokoro soundfile)") from e
        _pipeline = KPipeline(lang_code=(os.environ.get("OMNIBOT_TTS_LANG") or "f").strip())
        return _pipeline


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text or "") if s.strip()]


def synthesize_pcm(text: str) -> Iterator[bytes]:
    """Blocking generator of PCM chunks for one piece of text."""
    voice = (os.environ.get("OMNIBOT_TTS_VOICE") or "ff_siwis").strip()
    for _gs, _ps, audio in _load_pipeline()(text, voice=voice):
        if audio is None:
            continue
        arr = np.asarray(audio, dtype=np.float32)
        yield (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
