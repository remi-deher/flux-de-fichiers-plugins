# Déploiement PostgreSQL (modèles)

Ces fichiers sont des **exemples illustratifs** dérivés de la configuration
actuelle du dépôt applicatif. La source de vérité opérationnelle reste :

- `flux-de-fichiers/compose.yaml` (service `db`)
- `flux-de-fichiers/deploy/init-postgres.sh`
- `flux-de-fichiers/deploy/pg_hba.conf`

Aucune copie n’a été retirée du dépôt applicatif. Une éventuelle bascule des
artefacts de déploiement vers ce dépôt devra être coordonnée avec #10 et ne
doit pas casser le labo Compose existant.
