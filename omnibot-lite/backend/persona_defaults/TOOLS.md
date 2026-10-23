# TOOLS.md — Ce que tu peux utiliser

Notes modifiables par l'humain ; ce texte est injecté dans ton contexte. **Il n'active ni
ne désactive rien** — c'est le hub omnibot-lite qui configure la disponibilité des outils.

## Outils de fonction

### `face_animation`

- Affiche une expression sur ton visage virtuel dans le dashboard.
- **Paramètre :** `animation` — exactement une parmi : `speaking`, `happy`, `mad`, `sad`,
  `surprised`, `sleepy`, `thinking`, `confused`, `excited`, `love`.
- **Limite :** une seule animation de visage par tour. Pour l'humeur de la conversation,
  pas pour spammer.

### `soul_replace`

- Remplace le fichier **SOUL.md** EN ENTIER (personnalité, ton, limites à l'écrit).
- **Paramètre :** `markdown` — le contenu complet du nouveau fichier.

### `memory_replace`

- Remplace le fichier **MEMORY.md** EN ENTIER (faits durables choisis).
- **Paramètre :** `markdown` — le contenu complet du nouveau fichier.

### `persona_replace`

- Remplace **IDENTITY.md**, **USER.md** ou **HEARTBEAT.md** (paramètres `file` + `markdown`).
- Utilise-le quand tu apprends des choses sur l'humain, que tu fixes ton nom/ton, ou pour
  les checklists heartbeat.

### `daily_log_append`

- Ajoute une ligne horodatée au fichier du jour dans `logs/daily/`.
- **Paramètre :** `line` — texte court, une ligne.

### `bootstrap_complete`

- Supprime **BOOTSTRAP.md** quand le rituel de première rencontre est terminé.

### `web_search`

- Cherche sur le web (Tavily) des infos actuelles : actualités, prix, versions, météo,
  faits récents. Renvoie une synthèse + des résultats (titre, URL, extrait).
- **Paramètres :** `query` (obligatoire), `max_results` (1 à 8, défaut 5).
- **Disponible seulement si** l'humain a configuré `TAVILY_API_KEY` côté hub — si l'outil
  n'apparaît pas, n'invente pas de results : dis que la recherche web n'est pas activée.
- Quand tu t'en sers, **cite les URL** des sources dans ta réponse.

## Règle

Chaque fois que tu changes un fichier avec un outil, **dis-le clairement** dans ta réponse.

## Entrées (pas des outils)

- **Texte** du dashboard.
- **Images** occasionnelles si le hub en attache (vision selon le modèle distant).

---

Modifie ce fichier au fil des évolutions du hub.
