# Démarrer OmniBot en 100 % local

Mode sans cloud : LLM via Ollama, voix via faster-whisper + Kokoro, recherche via SearXNG (optionnelle).
Contexte et état d'avancement : [`docs/LOCAL_LLM_PLAN.md`](docs/LOCAL_LLM_PLAN.md).

> Le code a été écrit sans pouvoir installer les dépendances (proxy bloquant PyPI) : seul le chat
> et la recherche ont été testés contre de faux serveurs. Les étapes 4 à 7 ci-dessous sont les
> premiers vrais tests.

## 1. Prérequis (avec Internet, une seule fois)

- Python 3.10+ et Node.js LTS
- [Ollama](https://ollama.com) : `winget install Ollama.Ollama`
- **espeak-ng** (requis par Kokoro sur Windows) : `winget install eSpeak-NG.eSpeak-NG`
- Un casque avec micro (évite que le micro capte les haut-parleurs)
- Optionnel : Docker pour SearXNG

Au premier usage, les modèles se téléchargent (Ollama, faster-whisper, Kokoro, wake word,
InsightFace). Lance une fois avec Internet ; ensuite tout fonctionne hors ligne.

## 2. Installer

```powershell
git pull
.\scripts\install.ps1
.\app\backend\.venv\Scripts\pip install faster-whisper kokoro soundfile
```

`faster-whisper` et `kokoro` sont aussi dans `app/backend/requirements.txt` ; la ligne `pip` ci-dessus
sert si l'installation a déjà eu lieu avant.

## 3. Modèle de langage

```powershell
ollama pull qwen3:14b
ollama list          # le serveur répond sur http://127.0.0.1:11434
```

`qwen3:14b` est un défaut à valider (appels d'outils, qualité en français). Alternatives à essayer
si besoin : un autre modèle 12-14B en Q4. Changer de modèle : `OMNIBOT_LLM_MODEL`.

## 4. Configurer

Copier `app/backend/.env.example` vers `app/backend/.env` et décommenter :

```ini
OMNIBOT_LLM_BACKEND=openai_compat
OMNIBOT_LLM_BASE_URL=http://127.0.0.1:11434/v1
OMNIBOT_LLM_MODEL=qwen3:14b
OMNIBOT_STT_LANGUAGE=fr
# OMNIBOT_SEARXNG_URL=http://127.0.0.1:8080   # si SearXNG est lancé
```

Variables PowerShell possibles à la place : `$env:OMNIBOT_LLM_BACKEND = "openai_compat"`.

## 5. Lancer

```powershell
.\scripts\start.ps1
```

Dashboard : http://127.0.0.1:5173 — API : http://127.0.0.1:8000.
Vérifier le mode : `http://127.0.0.1:8000/api/hub/status` doit afficher `"llm_backend": "openai_compat"`
et `"llm_server_reachable": true`. L'écran de clé Gemini ne doit pas apparaître.

## 6. Tests, dans cet ordre

1. **Chat texte** : ouvrir un bot dans le dashboard, envoyer un message. La réponse doit streamer.
2. **Outils** : demander « change ton visage en joyeux » (`face_animation`), puis « retiens que j'aime le café »
   (outils persona / mémoire).
3. **Heartbeat** : dans *Pixel bot*, régler l'intervalle à 1 minute ; `MEMORY.md` doit être mis à jour
   après quelques échanges (logs : `[Omnibot/heartbeat]`).
4. **Micro du PC sans robot** : *Hub settings → voice source → browser*, autoriser le micro, dire le mot
   d'éveil puis une phrase. Attendu dans les logs : `[stt] '...'`, la réponse streamée, puis la voix dans le dashboard.
5. **Recherche web** (si SearXNG) : poser une question d'actualité ; les sources apparaissent sous la réponse.

## 7. Dépannage

| Symptôme | Piste |
|---|---|
| `llm_server_reachable: false` | Ollama n'est pas lancé, ou `OMNIBOT_LLM_BASE_URL` incorrecte |
| `LLM server HTTP 400/404` | Nom de modèle inexact (`ollama list`) ; modèle sans support des outils |
| Pas de réaction au mot d'éveil | Seuil `OMNIBOT_WAKE_THRESHOLD` (0,55 par défaut) à baisser ; modèle par défaut `hey_jarvis`, ou fournir `pixel.onnx` (`app/backend/models/wake/`) |
| `[stt]` vide ou erreur CUDA | `OMNIBOT_STT_DEVICE=cpu` ; vérifier le pilote NVIDIA |
| `kokoro is not installed` / erreur espeak | Installer espeak-ng, relancer le terminal |
| Pas de son | Le son sort dans le dashboard (onglet ouvert, clic préalable pour autoriser l'audio), pas sur le Pixel |
| Le bot se répond à lui-même | Utiliser un casque |
| Mémoire VRAM saturée | Modèle plus petit, ou `OMNIBOT_STT_MODEL=small` |

## 8. Limites connues

- Gemini Live est désactivé en mode local ; le Pixel et le micro du navigateur passent par STT → LLM → TTS.
- La voix démarre une fois le texte complet (pas de synthèse pendant le streaming).
- Pas de vision en voix (les frames vidéo ne sont pas envoyées au modèle).
- Le modèle local se règle par variables d'environnement, pas dans l'UI.

## 9. Revenir à Gemini

Retirer `OMNIBOT_LLM_BACKEND` (ou la mettre à `gemini`) et renseigner la clé Gemini dans le dashboard.
