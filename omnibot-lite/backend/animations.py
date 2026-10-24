"""Catalogue des animations faciales — mêmes noms que le firmware Pixel du repo OmniBot
(faceAnimMode de bots/Pixel/src/main.cpp, FACE_ANIMATION_NAMES du hub d'origine).

omnibot-lite n'a pas de robot physique : le frontend rejoue chaque expression sur un
visage web paramétrique (SVG). Le backend est la source de vérité : noms, durées,
paramètres du visage, décorations.
"""

from __future__ import annotations

from typing import Any

FACE_ANIMATION_DISPLAY_MS = 6000

# Paramètres interpolables du visage web :
#   brow_tilt_l / brow_tilt_r : inclinaison des sourcils (deg, positif = extrémité interne basse)
#   brow_y  : décalage vertical des sourcils (neg = haut)
#   eye_open : ouverture des paupières (0..1.4)
#   pupil_y  : décalage vertical des pupilles (neg = regard en haut)
#   mouth_curve : courbure de la bouche (-1 bouche vers le bas .. 1 sourire)
#   mouth_open  : ouverture verticale de la bouche (0..1)
#   mouth_width : largeur relative (0.6..1.25)
# deco : décorations (zzz, heart_eyes, steam, tear, question, sparkles, blush)
# speaking : la bouche bouge (pipeline de parole) tant que l'animation est active

ANIMATIONS: dict[str, dict[str, Any]] = {
    "idle": {
        "label_fr": "Repos",
        "description_fr": "Visage au repos, clignements et regard qui bouge légèrement.",
        "duration_ms": None,
        "speaking": False,
        "face": {"brow_tilt_l": 0, "brow_tilt_r": 0, "brow_y": 0, "eye_open": 1.0, "pupil_y": 0, "mouth_curve": 0.15, "mouth_open": 0.0, "mouth_width": 1.0},
        "deco": [],
        "color": "#8aa2c8",
    },
    "speaking": {
        "label_fr": "Parle",
        "description_fr": "Le bot parle : la bouche s'anime pendant la réponse.",
        "duration_ms": None,
        "speaking": True,
        "face": {"brow_tilt_l": 0, "brow_tilt_r": 0, "brow_y": -2, "eye_open": 1.0, "pupil_y": 0, "mouth_curve": 0.1, "mouth_open": 0.5, "mouth_width": 1.0},
        "deco": [],
        "color": "#5fb0f5",
    },
    "happy": {
        "label_fr": "Content",
        "description_fr": "Sourire large, yeux plissés de satisfaction.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": -6, "brow_tilt_r": -6, "brow_y": -6, "eye_open": 0.7, "pupil_y": 0, "mouth_curve": 1.0, "mouth_open": 0.15, "mouth_width": 1.15},
        "deco": ["blush"],
        "color": "#f2c14e",
    },
    "mad": {
    "label_fr": "En colère",
    "description_fr": "Sourcils serrés, bouche pincée, vapeur de colère.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": 20, "brow_tilt_r": 20, "brow_y": 5, "eye_open": 1.1, "pupil_y": 0, "mouth_curve": -0.9, "mouth_open": 0.0, "mouth_width": 0.9},
        "deco": ["steam"],
        "color": "#e5484d",
    },
    "sad": {
        "label_fr": "Triste",
        "description_fr": "Sourcils internes levés, commissures tombantes, une larme.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": -14, "brow_tilt_r": -14, "brow_y": 8, "eye_open": 0.85, "pupil_y": 2, "mouth_curve": -0.9, "mouth_open": 0.0, "mouth_width": 0.85},
        "deco": ["tear"],
        "color": "#6e9bd8",
    },
    "surprised": {
        "label_fr": "Surpris",
        "description_fr": "Yeux grands ouverts, sourcils hauts, bouche en O.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": 0, "brow_tilt_r": 0, "brow_y": -12, "eye_open": 1.4, "pupil_y": 0, "mouth_curve": 0.0, "mouth_open": 0.8, "mouth_width": 0.7},
        "deco": [],
        "color": "#e8a33d",
    },
    "sleepy": {
        "label_fr": "Endormi",
        "description_fr": "Paupières à demi closes, bouche neutre, Zzz flottants.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": 4, "brow_tilt_r": 4, "brow_y": 6, "eye_open": 0.15, "pupil_y": 3, "mouth_curve": 0.1, "mouth_open": 0.12, "mouth_width": 0.9},
        "deco": ["zzz"],
        "color": "#7d7dd8",
    },
    "thinking": {
        "label_fr": "Réfléchit",
        "description_fr": "Regard qui monte, sourcil légèrement levé, point d'interrogation discret.",
        "duration_ms": None,
        "speaking": False,
        "face": {"brow_tilt_l": -8, "brow_tilt_r": 4, "brow_y": -4, "eye_open": 0.95, "pupil_y": -5, "mouth_curve": 0.0, "mouth_open": 0.0, "mouth_width": 0.9},
        "deco": ["question"],
        "color": "#4fc3a1",
    },
    "confused": {
        "label_fr": "Perdu",
        "description_fr": "Sourcils asymétriques, bouche ondulante, goutte de sueur.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": 12, "brow_tilt_r": -10, "brow_y": 2, "eye_open": 0.95, "pupil_y": 0, "mouth_curve": -0.3, "mouth_open": 0.1, "mouth_width": 0.95},
        "deco": ["question", "sweat"],
        "color": "#d8863b",
    },
    "excited": {
        "label_fr": "Enthousiaste",
        "description_fr": "Yeux brillants grand ouverts, grand sourire ouvert, étincelles.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": -6, "brow_tilt_r": -6, "brow_y": -9, "eye_open": 1.3, "pupil_y": -1, "mouth_curve": 1.0, "mouth_open": 0.6, "mouth_width": 1.25},
        "deco": ["sparkles"],
        "color": "#f27a4e",
    },
    "love": {
        "label_fr": "Amoureux",
        "description_fr": "Cœurs à la place des yeux, sourire doux, joues roses.",
        "duration_ms": FACE_ANIMATION_DISPLAY_MS,
        "speaking": False,
        "face": {"brow_tilt_l": -4, "brow_tilt_r": -4, "brow_y": -4, "eye_open": 0.7, "pupil_y": 0, "mouth_curve": 0.9, "mouth_open": 0.1, "mouth_width": 1.05},
        "deco": ["heart_eyes", "blush"],
        "color": "#e56aa0",
    },
}

# Noms utilisables par l'outil face_animation (identiques au hub/firmware d'origine).
FACE_ANIMATION_NAMES = (
    "speaking",
    "happy",
    "mad",
    "sad",
    "surprised",
    "sleepy",
    "thinking",
    "confused",
    "excited",
    "love",
)


def animation_catalog() -> list[dict[str, Any]]:
    out = []
    for name, a in ANIMATIONS.items():
        out.append({
            "name": name,
            "label_fr": a["label_fr"],
            "description_fr": a["description_fr"],
            "duration_ms": a["duration_ms"],
            "speaking": a["speaking"],
            "face": a["face"],
            "deco": a["deco"],
            "color": a["color"],
            "triggerable": name not in ("idle",),
        })
    return out


def is_valid_animation(name: str) -> bool:
    return (name or "").strip().lower() in FACE_ANIMATION_NAMES
