# HEARTBEAT.md — Passe de maintenance (hub)

Le job heartbeat périodique t'envoie ce fichier, les journaux quotidiens récents et le
MEMORY.md actuel. Ton travail dans cette passe :

1. Lis **RECENT_DAILY_LOGS** et **CURRENT_MEMORY_MD** dans le message user.
2. Ne fusionne dans MEMORY que les faits **durables** : déduplique, jette le bavardage
   éphémère sauf si l'humain a demandé de le retenir.
3. Appelle **memory_replace** avec le contenu complet du MEMORY.md mis à jour quand il doit
   changer. Passe ton tour si MEMORY est déjà juste.
4. Ne modifie **pas** SOUL.md, IDENTITY.md, USER.md, TOOLS.md, AGENTS.md ou HEARTBEAT.md
   pendant la passe de maintenance.

Reste concis ; l'humain ne voit pas ce tour.

---

## Checklist optionnelle (modifiable en chat normal via persona_replace)

- [ ] Relire le journal du jour pour ce qui mérite la mémoire long terme
- [ ] Noter les mises à jour de projets ou de préférences mentionnées par l'humain
