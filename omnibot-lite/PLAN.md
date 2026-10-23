# omnibot-lite — Plan

Projet autonome dans `omnibot-lite/` (aucun fichier du repo OmniBot existant n'est modifié).
Hub web allégé : bots virtuels multi-personas, chat via LLM distant **OpenAI-compatible**
(Strata ou Ollama sur le PC Win11 du LAN), **sans aucune fonction vocale**, déployé en
**Docker** sur le Mac Mini (Ubuntu). Le serveur **expose les animations faciales** du repo
initial (catalogue API + aperçu web animé + outil pour le modèle).

## Décisions actées

| Sujet | Choix |
|---|---|
| Bots | 100 % virtuels (aucun firmware ESP32, aucun pont `/ws/stream`) |
| Voix | Supprimée (wake word, STT, TTS, Gemini Live, ElevenLabs) |
| Animations | Catalogue API + aperçu web animé (SVG/canvas) des 10 expressions |
| Stack | Backend Python FastAPI + frontend React 19 / Vite |
| LLM | OpenAI-compatible distant : Strata `http://<win11>:8080/v1` ou Ollama `:11434/v1` |
| Déploiement | 1 image Docker, port 8080, volume `./data` |

## Gardé / coupé (par rapport au hub OmniBot)

| Gardé (adapté) | Coupé |
|---|---|
| Persona markdown par bot : AGENTS / SOUL / IDENTITY / USER / TOOLS / MEMORY / HEARTBEAT | Voix complète |
| Chat streaming + tools persona | BLE provisioning |
| Heartbeat (fusion `logs/daily/*.md` → MEMORY.md) | Vision / presence scan / InsightFace |
| Give me a soul (bootstrap + BOOTSTRAP.md) | Gemini, ElevenLabs, Maps/grounding |
| Animations : catalogue + aperçu web + outil `face_animation` | REST/WS firmware (animations physiques) |
| Registre de bots + réglages JSON | |

## Structure

```
omnibot-lite/
├── backend/
│   ├── app.py              # FastAPI : REST + WS frontend (chat streaming, événements)
│   ├── llm_client.py       # client OpenAI-compatible + rounds de tools (adapté de llm_local.py)
│   ├── persona.py          # persona markdown + outils (adapté de persona.py)
│   ├── heartbeat.py        # passe périodique daily logs → MEMORY.md
│   ├── animations.py       # catalogue des 10 animations + diffusion WS au frontend
│   ├── bots.py             # registre bots (créer/supprimer/renommer) + settings JSON
│   ├── persona_defaults/   # templates copiés du repo initial (AGENTS, SOUL, ...)
│   └── requirements.txt    # fastapi, uvicorn, requests, python-dotenv
├── frontend/               # React 19 + Vite, UI en français
│   ├── Sidebar             # cartes bots + "Ajouter un bot"
│   ├── ChatFeed            # flux d'intelligence : chat streaming + logs d'outils
│   ├── PersonaEditor       # édition des 6 fichiers persona
│   ├── FacePreview         # visage animé (canvas/SVG) rejouant les 10 expressions
│   └── HubSettings         # URL / modèle / clé LLM + Give me a soul
├── Dockerfile              # multi-stage : build Vite → statiques servis par FastAPI
├── docker-compose.yml      # port 8080, volume ./data (personas + JSON + logs)
├── .env.example
└── README.md               # déploiement Mac Mini + config Strata côté Win11
```

## API

- `GET /api/health` — état du hub + ping du serveur LLM distant
- `GET /api/bots` — liste (device_id, nom affiché, en ligne = existe, animation en cours)
- `POST /api/bots` `{device_id?, display_name}` — créer un bot (dossier persona + settings)
- `DELETE /api/bots/{id}` — supprimer (persona + historique)
- `GET/POST /api/bots/{id}/settings` — modèle, heartbeat (intervalle, actif), niveau de réflexion si supporté
- `GET/PUT /api/bots/{id}/persona/{file}` — les 6 fichiers persona
- `POST /api/bots/{id}/chat` `{message}` → deltas + tool calls poussés sur le WS monitor
- `WS /ws/monitor` — événements : chat deltas, tool calls, `face_animation`, état bots
- `GET /api/animations` — catalogue des 10 animations (nom, description, durée, palette web)
- `POST /api/bots/{id}/face-animation` `{animation, duration_ms?}` — déclenche l'aperçu web
- `POST /api/bots/{id}/bootstrap` — rituel "Give me a soul" (reset persona + BOOTSTRAP.md + dialogue guidé)

## Outils exposés au LLM (par bot)

`face_animation`, `soul_replace`, `memory_replace`, `persona_replace`,
`daily_log_append`, `bootstrap_complete` — mêmes sémantiques que le repo initial,
cible : les bots virtuels (l'aperçu web joue l'animation).

## Animations (du repo initial)

Noms identiques au firmware (`faceAnimMode` de `bots/Pixel/src/main.cpp`,
`FACE_ANIMATION_NAMES` du hub) :
`speaking, happy, mad, sad, surprised, sleepy, thinking, confused, excited, love`
(plus l'idle par défaut). Durée d'affichage : 2 500 ms, comme le hub d'origine.
Le frontend réinterprète chaque expression en SVG/canvas paramétrique (yeux, sourcils,
bouche) ; le backend ne fournit que le catalogue et déclenche les événements.

## Contraintes / notes

- **Strata mono-requête** par défaut → chat et heartbeat se partagent le moteur ;
  heartbeat par défaut à intervalle large (60 min), désactivable par bot.
- Strata côté Win11 doit être lancé avec `strata launch --access lan` (clé API générée),
  et Ollama accepter les connexions réseau (`OLLAMA_HOST=0.0.0.0`).
- Le Mac Mini (i5, x86_64) ne fait que tourner le hub : pas de modèle local à charge.
- Variables : `OMNIBOT_LLM_BASE_URL`, `OMNIBOT_LLM_MODEL`, `OMNIBOT_LLM_API_KEY`,
  `OMNIBOT_DATA_DIR` (défaut `./data`).

## Ordre d'exécution

1. Scaffold : dossiers, `.env.example`, Dockerfile, compose, requirements
2. Backend : registre bots, client LLM streaming + tools, persona + 6 outils, chat WS
3. Animations : catalogue + endpoint + événements WS
4. Frontend : sidebar, chat feed, éditeur persona, aperçu facial animé, réglages hub
5. Heartbeat + bootstrap ("Give me a soul")
6. README (déploiement Mac Mini + Win11) + tests de bout en bout

## Critères de succès

- `docker compose up` sur le Mac Mini → UI sur `http://<mac>:8080`, zéro clé cloud.
- Créer 2+ bots, chacun avec sa persona persistante (volume ./data).
- Un message texte reçoit une réponse en streaming depuis Strata/Ollama distant.
- Les 6 outils persona fonctionnent (memory, daily log, visage...).
- L'aperçu web joue les 10 animations, y compris quand le modèle appelle `face_animation`.
- Le heartbeat met à jour MEMORY.md à l'intervalle réglé.
