# Outil : PostgreSQL

Choix **actuel** et **requis** pour les métadonnées.

## Frontière

| Élément | Emplacement actuel | Rôle |
|---------|--------------------|------|
| Migrations SQL applicatives | dépôt `flux-de-fichiers` / `migrations/` | schéma métier, SQLx |
| Service Compose `db` | dépôt applicatif `compose.yaml` | runtime local / labo |
| Modèles partageables | `apps/postgresql/deploy/` (ce dépôt) | documentation et futurs artefacts de déploiement |

Aucune migration de données n’est effectuée par ce squelette. Aucune alternative
de base n’est proposée ni installée.
