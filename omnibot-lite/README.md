# omnibot-lite

> Schéma d'architecture, rôles des fichiers et table de debug : voir [ARCHITECTURE.md](ARCHITECTURE.md).

Hub web de **bots virtuels à personnalité** (style OpenClaw : SOUL / IDENTITY / USER /
MEMORY / HEARTBEAT…), propulsé par un serveur LLM **OpenAI-compatible distant**
(Strata ou Ollama sur ton PC Windows 11 du LAN). **Zéro voix, zéro cloud, zéro firmware.**
Le serveur expose les **10 animations faciales** du projet OmniBot d'origine, rejouées
sur un visage animé dans le navigateur.

Déployé en **Docker** sur le Mac Mini (Ubuntu) ; l'interface est en français.

---

## 1. Préparer le serveur LLM (PC Windows 11)

### Option A — Strata (recommandée)

```powershell
strata launch --access lan
```

- note l'IP du PC (ex. `192.168.1.10`) et le **port 8080** ;
- `--access lan` génère une **clé API** (à recopier dans les réglages du hub) ;
- Strata accepte **n'importe quel nom de modèle** (mets `default` ou le nom que tu veux).

⚠️ Strata ne traite **qu'une requête à la fois** par défaut : garde un intervalle de
heartbeat large (60 min par défaut) pour ne pas le faire se battre avec le chat.

### Option B — Ollama

```powershell
# PowerShell, à lancer une fois (persistant) :
setx OLLAMA_HOST 0.0.0.0
# puis relancer Ollama
```

API : `http://<ip-win11>:11434/v1`, modèle : celui que tu as `pull` (ex. `qwen3:14b`).

---

## 2. Déployer sur le Mac Mini (Ubuntu, Docker déjà installé)

```bash
git clone <repo> && cd OmniBot/omnibot-lite   # ou copier le dossier omnibot-lite/
cp .env.example .env                          # puis éditer .env
docker compose up -d --build
```

Le hub n'est **pas exposé au LAN** (pas d'authentification) : il écoute sur
`127.0.0.1:8000` sur le Mac Mini. Accès via Tailscale serve, une fois pour toutes :

```bash
tailscale serve --bg --https=11443 http://127.0.0.1:8000
```

Puis ouvrir **https://macmini.<tailnet>.ts.net:11443** depuis n'importe quel appareil
du tailnet (ou `http://127.0.0.1:8000` directement sur le Mac Mini).

Le volume `./data` contient tout l'état (personas, journaux, historiques, réglages,
clé LLM) — sauvegardable/copiable tel quel.

### Config LLM

Deux façons (la UI prime sur l'environnement) :

- **.env / compose** : `OMNIBOT_LLM_BASE_URL`, `OMNIBOT_LLM_MODEL`, `OMNIBOT_LLM_API_KEY` ;
- **UI → ⚙ Règlages du hub** : URL, modèle, clé + bouton **Tester** (vert = joignable).

Exemples d'URL :

| Serveur | URL |
|---|---|
| Strata (Win11, `--access lan`) | `http://192.168.1.10:8080/v1` |
| Ollama (Win11, `OLLAMA_HOST=0.0.0.0`) | `http://192.168.1.10:11434/v1` |

---

## 3. Utilisation

### Recherche web (optionnelle — `web_search`)

Les bots peuvent chercher des infos actuelles sur le web via **Tavily**. C'est désactivé
par défaut. Pour l'activer :

1. Créer une clé gratuite sur <https://app.tavily.com>.
2. La mettre dans le fichier `.env` à côté de `docker-compose.yml` :
   ```
   TAVILY_API_KEY=tvly-...
   ```
3. Relancer : `docker compose up -d` (rebuild inutile, seule l'env change).

Une fois la clé présente, l'outil `web_search` est proposé au LLM à chaque tour de chat ;
sans clé il n'apparaît pas et les bots n'y ont pas accès. Le CLI `tvly` (outil pour agent
de codage) n'est **pas** utilisé par le hub : le runtime passe directement par l'API REST.


1. **+ Nouveau bot** dans la barre latérale.
2. Bouton **✨ Donne-moi une âme** (barre du haut) : réinitialise la persona et lance le
   rituel de naissance (BOOTSTRAP) — le bot se présente et découvre qui il est avec toi.
3. Chat normal : réponses en streaming, le bot peut appeler ses outils (visible en
   pastilles vertes dans le flux).
4. **Panneau visage** à droite : le visage animé rejoue l'expression courante. Le modèle
   déclenche les animations via son outil `face_animation` ; les pastilles colorées
   permettent aussi de les tester à la main. Les 10 animations :
   `speaking, happy, mad, sad, surprised, sleepy, thinking, confused, excited, love`.
5. **⚙ Réglages** (par bot) : nom, modèle (vide = modèle du hub), heartbeat
   (activation + intervalle, test immédiat), persona (édition des 7 fichiers markdown),
   reset persona, suppression du bot.

### Heartbeat

Passe de maintenance périodique par bot : le hub envoie les journaux quotidiens
(`logs/daily/*.md`) au modèle, qui fusionne les faits durables dans **MEMORY.md**
(outil `memory_replace` uniquement). Par défaut toutes les 60 min, désactivable par bot.

---

## 4. Développement local (sans Docker)

```bash
# Terminal 1 — backend (port 8080)
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
OMNIBOT_LLM_BASE_URL=http://<ip-win11>:8080/v1 .venv/bin/uvicorn app:app --port 8080

# Terminal 2 — frontend Vite (proxy /api + /ws vers 8080)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

### Tests de bout en bout (sans GPU ni LLM réel)

```bash
bash scripts/smoke.sh
```

Lance un **faux serveur OpenAI-compatible** (`scripts/fake_llm_server.py`) + le hub,
puis vérifie : health, catalogue d'animations, création de bot, persona, chat streaming
avec tool call `face_animation`, événements WebSocket, historique persisté, réglages,
suppression.

---

## 5. API (résumé)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | état du hub + ping du serveur LLM |
| GET/POST | `/api/bots` | liste / création de bots |
| POST/DELETE | `/api/bots/{id}/rename`, `/api/bots/{id}` | renommer / supprimer |
| GET/POST | `/api/bots/{id}/settings` | modèle, heartbeat |
| POST | `/api/bots/{id}/chat` `{message}` | lance un tour (streaming via WS) |
| GET | `/api/bots/{id}/history` | messages persistés |
| POST | `/api/bots/{id}/chat/reset` | effacer la conversation |
| POST | `/api/bots/{id}/bootstrap` | rituel *Donne-moi une âme* |
| POST | `/api/bots/{id}/heartbeat/run` | passe de heartbeat immédiate |
| GET/PUT | `/api/persona/{id}/{file}` | 7 fichiers markdown (agents, soul, identity, user, tools, memory, heartbeat) |
| POST | `/api/bots/{id}/reset-persona` | écraser par les défauts |
| GET | `/api/animations` | catalogue des 11 expressions (idle + 10) avec paramètres du visage web |
| POST | `/api/bots/{id}/face-animation` | déclencher une animation sur le visage |
| GET/POST | `/api/hub/settings` | URL / modèle / clé LLM |
| WS | `/ws/monitor` | événements : `chat_delta`, `tool_call`, `face_animation`, `chat_done`, … |

Outils exposés au modèle par bot : `face_animation`, `soul_replace`, `memory_replace`,
`persona_replace`, `daily_log_append`, `bootstrap_complete`.

---

## 6. Arborescence

```
omnibot-lite/
├── backend/            # FastAPI (app.py, llm_client.py, persona.py, heartbeat.py,
│   │                   #  animations.py, bots.py, config.py)
│   └── persona_defaults/  # templates français des fichiers persona
├── frontend/           # React 19 + Vite (sidebar, chat, éditeur persona, visage animé)
├── scripts/            # fake_llm_server.py + smoke tests
├── Dockerfile          # build Vite → image Python unique (API + SPA sur :8080)
├── docker-compose.yml  # 127.0.0.1:8000 → 8080 (LAN fermé), volume ./data
└── .env.example
```

## Dépannage

- **Point rouge « serveur LLM injoignable »** : vérifier `strata launch --access lan`,
  le pare-feu Windows (autoriser le port 8080/11434 en réseau *privé*), et l'URL dans
  *Règlages du hub*.
- **Réponses très lentes / erreurs** : Strata est mono-requête — réduis le nombre de bots
  actifs en heartbeat simultanés ou augmente les intervalles.
- **Injoignable depuis le réseau local** : normal, le hub est bindé sur `127.0.0.1:8000`
  (LAN fermé volontairement). Passe par Tailscale serve (`https://macmini…:11443`) ou
  ouvre `http://127.0.0.1:8000` sur le Mac Mini lui-même.
- **Tout est perdu après `docker compose down -v`** : le volume est `./data` (bind mount),
  il ne disparaît qu'avec `-v` ou en supprimant le dossier.
