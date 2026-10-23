# Plan : backend LLM local

Objectif : faire tourner le hub sans cloud sur un PC Windows 11 (RTX 5060 Ti 16 Go, 64 Go DDR4, Ryzen 5700X).
Gemini reste disponible comme backend optionnel ; le local devient le choix par défaut possible.

## Décisions

| Sujet | Choix |
|---|---|
| Gemini | Conservé, interchangeable via `OMNIBOT_LLM_BACKEND=gemini\|openai_compat` |
| Serveur de modèles | Ollama (API compatible OpenAI sur `http://127.0.0.1:11434/v1`) |
| Ordre | Chat texte, heartbeat, recherche web, voix |
| Langue | Français |

## État actuel (dépendances Gemini)

| Fonction | Fichier | API |
|---|---|---|
| Chat texte en streaming + tools | `app/backend/app.py` (~2340-2500) | `chats.create`, `send_message_stream` |
| Voix temps réel | `app/backend/gemini_live_session.py` | `aio.live.connect` |
| Heartbeat (mémoire) | `app/backend/heartbeat_service.py` | `chats.create`, `send_message` |
| Recherche web + citations | `app/backend/grounding_extract.py` | outil `google_search` |

Déjà local : wake word (OpenWakeWord), VAD (webrtcvad), visages (InsightFace), persona (markdown).
Client unique : `hub_config.get_genai_client()`.

## Avancement

| Étape | Statut |
|---|---|
| 1-2 Chat texte local (`app/backend/llm_local.py`, dispatch dans `app.py`) | fait, testé contre un faux serveur |
| 3 Heartbeat local | fait, non testé en réel |
| 4 Recherche web (`web_search.py`, SearXNG via `OMNIBOT_SEARXNG_URL`) | fait, testé contre un faux SearXNG |
| 6a STT local (`stt_local.py`, faster-whisper) pour les tours vocaux | fait, non testé (faster-whisper non installable ici) |
| 5, 6b (TTS local), 7, 8 | à faire |

Variables : `OMNIBOT_LLM_BACKEND`, `OMNIBOT_LLM_BASE_URL`, `OMNIBOT_LLM_MODEL`, `OMNIBOT_LLM_API_KEY` (voir `.env.example`).
En mode local, Gemini Live est désactivé et les tours audio/vidéo ne sont pas pris en charge (texte et images seulement).

## Étapes

1. **Abstraction `LLMBackend`** (`app/backend/llm_backend.py`) : interface de chat en streaming avec tools ;
   implémentations Gemini (code existant) et OpenAI-compatible. Sélection par variable d'environnement.
2. **Chat texte** : `app.py` passe par `LLMBackend`. Les `FunctionDeclaration` (format OpenAPI) sont converties en `tools` OpenAI.
3. **Heartbeat** : même backend ; seul l'outil `memory_replace` est exposé.
4. **Recherche web** : outil `web_search` custom (SearXNG ou Brave) ; citations reconstruites à la place du grounding Google.
5. **Vision** : frames envoyées en `image_url` si le modèle local est multimodal.
6. **Voix locale** : pipeline VAD → faster-whisper (CUDA) → LLM en streaming → TTS local (Kokoro/Piper) par phrase,
   en gardant les événements WebSocket actuels vers le frontend.
7. **UI / setup** : la clé Gemini devient optionnelle ; ajout de l'URL et du nom de modèle local (Hub settings, FirstRunSetup).
8. **Docs** : README (prérequis, installation d'Ollama, variables).

## Budget VRAM (16 Go)

| Brique | Cible | VRAM approx. |
|---|---|---|
| LLM chat + vision + tools | modèle 12-14B Q4, contexte 8-16k | 9-11 Go |
| STT | faster-whisper large-v3-turbo | ~2 Go |
| TTS | Kokoro / Piper | < 1 Go |

Les modèles précis sont à valider par test (appel de fonctions, qualité en français).

## Critères de réussite

- Un message texte reçoit une réponse en streaming sans clé Gemini ni accès réseau.
- Les 6 outils persona (`face_animation`, `soul_replace`, `memory_replace`, `persona_replace`, `daily_log_append`, `bootstrap_complete`) fonctionnent.
- Le heartbeat met à jour `MEMORY.md`.
- Le comportement avec `OMNIBOT_LLM_BACKEND=gemini` reste inchangé.
