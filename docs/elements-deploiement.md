# Éléments de déploiement

## État

| Artefact | Emplacement | Statut |
|----------|-------------|--------|
| Modèles Postgres historiques (`pg_hba`, init TLS) | `examples/legacy/postgresql/deploy/*.example` | Archive illustrative (SQLite local retenu côté socle) |
| Notes racine | `deploy/README.md` | Point d’entrée |
| Compose applicatif | `flux-de-fichiers/compose.yaml` | Source de vérité (inchangée) |
| Secrets | hors git (`var/secrets/`, fichiers orchestrateur) | Préservés |

## Contraintes

- Pas de publication distante depuis #11.
- Pas d’action TrueNAS / production.
- Image applicative unique (rôle au démarrage) : hors périmètre de modification ici ;
  les outils catalogue documentent les capacités, pas le packaging binaire.
