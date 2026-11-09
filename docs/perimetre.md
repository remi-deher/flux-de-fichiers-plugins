# Périmètre du dépôt d’outillage

## Inclus

- Catalogue et fiches (`manifest.json`) pour plugins, outils, flux, presets et ressources.
- Schémas versionnés (`schema/`).
- Documentation des interfaces et de l’intégration applicative.
- Modèles d’éléments de déploiement partageables (PostgreSQL), sans bascule forcée.

## Exclus

- Code applicatif Rust (coordinateur, worker, API) — dépôt `flux-de-fichiers`, ticket #10.
- Chargeur / runtime d’exécution des plugins.
- Publication GitHub, commit et push — ticket #12.
- Alternatives non validées à PostgreSQL ou MKVToolNix.
- Secrets, données métier, migrations de données, actions de production.
- Tests ajoutés ou exécutés sans demande explicite.
