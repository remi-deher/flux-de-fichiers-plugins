# Éléments de déploiement partageables (racine)

Point d’entrée pour les artefacts de déploiement qui ne sont pas liés à un
outil unique (orchestration multi-services, notes TrueNAS, etc.).

Pour PostgreSQL, voir `apps/postgresql/deploy/`.

Rien n’est branché automatiquement sur le dépôt applicatif : l’intégration
Compose / middleware TrueNAS reste manuelle et soumise à revue (#12 pour la
publication de ce dépôt).
