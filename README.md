# flux-de-fichiers-plugins

Dépôt d’outillage, de plugins, de flux prédéfinis et de ressources pour
[flux-de-fichiers](https://github.com/remi-deher/flux-de-fichiers).

Ce dépôt est un **catalogue versionné** : manifestes, schémas et exemples
illustratifs. Il ne contient pas de chargeur d’exécution ni de binaire tiers.

## Périmètre

| Zone | Rôle |
|------|------|
| `catalogue/` | Index des fiches disponibles (références, pas de copie des descriptions) |
| `plugins/` | Extensions applicatives (exemples de structure) |
| `tools/` | Outils de traitement et de déploiement (choix actuels : MKVToolNix, PostgreSQL) |
| `flows/` | Flux prédéfinis |
| `presets/` | Profils / réglages nommés |
| `resources/` | Polices, images, audio, couleurs, langues, modèles |
| `schema/` | Contrats JSON Schema versionnés |
| `docs/` | Périmètre, interfaces, intégration, déploiement, limites |
| `deploy/` | Éléments de déploiement partageables (modèles ; source de vérité applicative inchangée) |

## Choix actuels (non négociables sans décision utilisateur)

- **PostgreSQL** : base de métadonnées requise.
- **MKVToolNix** (`mkvmerge`) : remuxage actuel.
- **FFmpeg** : réservé aux médias synthétiques des tests dans le dépôt applicatif ; pas un outil de traitement catalogue ici.

## Documentation

1. [Périmètre](docs/perimetre.md)
2. [Contrat manifeste](docs/contrat-manifeste.md)
3. [Interfaces d’outils](docs/interfaces-outils.md)
4. [Intégration applicative](docs/integration-application.md)
5. [Éléments de déploiement](docs/elements-deploiement.md)
6. [Limites et revue](docs/limites-et-revue.md)


## État

Squelette initial publié sur GitHub. Ce dépôt est maintenant versionné et accessible
à l'URL https://github.com/remi-deher/flux-de-fichiers-plugins.

Préparation DevOps validée (#11), publication effectuée (#12).
