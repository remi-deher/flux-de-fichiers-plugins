# flux-de-fichiers-plugins

Catalogue déclaratif versionné pour
[Flux de Fichiers](https://github.com/remi-deher/flux-de-fichiers) : fiches de
applications, plugins (et leurs blocs low-code), flows, packs et éléments « Autre ».
Aucun chargeur, installeur, moteur de flows ou binaire tiers n'est livré ici.

## Contrats et compatibilité

- [Catalogue historique](catalogue/index.json) et manifestes v1 conservés à
  l'identique ; les anciennes ressources restent lisibles sans migration.
- [Index complémentaire](examples/catalogue/contracts.v1.json) pour découvrir les nouveaux
  contrats sans modifier les fiches historiques.
- [Guide des versions](docs/contrat-manifeste.md) : schémas 1.0.0, manifestes
  étendus 1.1.0 et versions de contenu distinctes.

## Organisation

| Dossier | Contenu |
| --- | --- |
| `catalogue/` | Index unique des pièces (`index.json`) |
| `apps/` | **Applications** : MKVToolNix, FFmpeg, MP4Box, MediaInfo, télémétrie, PostgreSQL ; fiche + `distribution.v1.json` Option B |
| `plugins/` | **Plugins**, chacun avec ses opérations et ses blocs (`plugins/<nom>/blocks/`) |
| `flows/` | **Flows** : graphes de blocs, dépendant de plugins |
| `packs/` | **Packs** : ensembles d'applications, de plugins, de flows et d'éléments « Autre » |
| `schema/` | JSON Schema Draft 2020-12, références résolues hors réseau |
| `scripts/` | `check_catalogue.py` : contrôle de l'index, des propriétaires et des dépendances |
| `examples/` | Exemples fictifs (`catalogue/` : un exemple par type, dont les éléments « Autre ») et messages d'invocation |
| `deploy/` | Modèles documentaires, sans action sur les déploiements actuels |

Les éléments **Autre** (préréglages, polices, images, musiques, couleurs, langues, modèles)
vivent seuls et sont appelables par un flow ; il n'en existe pour l'instant que des
exemples. Un **bloc** n'existe jamais seul : son fichier est rangé sous son plugin et
son entrée d'index porte `owner`. Une dépendance de plugin vers une application est
une suggestion (`optional`), jamais une obligation.

Contrôle local : `python3 scripts/check_catalogue.py`.

## Parcours de lecture

1. [Outil, plugin, bloc, flow, preset, app et ressource](docs/distinctions-catalogue.md).
2. [Distribution binaires Option B](docs/contrat-distribution-binaires.md).
3. [Macro-blocs composites](docs/contrat-macro-blocs.md).
4. [Opérations et adaptateur argv](docs/contrat-operations-argv.md).
5. [Appels, états et console brute](docs/contrat-invocation-console.md).
6. [Composition des blocs et des flows](docs/contrat-blocks-flows.md).
7. [Installation d'un pack](docs/contrat-packs.md).
8. [Garanties exigées du futur runtime](docs/garanties-execution-v1.md).
9. [Migration schémas v1 → v1.1 (#40)](docs/migration-schemas-v1.1.md).
10. [Diff revue sécurité #40](docs/diff-revue-securite-40.md).
11. [Note de décision et arbitrages ouverts](docs/questions-ouvertes.md).
12. [Relecture statique et limites de la vérification](docs/limites-et-revue.md).

Les schémas `*.v1.schema.json` restent inchangés ; les documents durcis ciblent
`schemaVersion: "1.1.0"` (`*.v1.1.schema.json`).

## Stack et état réel

Le runtime reste dans le dépôt applicatif : Rust, Axum/Tokio, SQLx/SQLite,
Docker et frontend Leptos. MKVToolNix est le remuxer validé, avec sortie MKV ;
FFmpeg reste réservé à la fabrication et à l'analyse des médias synthétiques de
tests. Aucun outil MP4 de production n'est sélectionné par ces contrats.

L'exemple complet commence dans
[le plugin MKV](examples/catalogue/plugins/remux-mkv.example/README.md). La CLI reprend les options
actuelles de `src/media.rs` ; les messages JSON sont fictifs. L'application
actuelle ne lit pas ces définitions et ne capture pas encore stdout/stderr du
remuxage. Aucun code applicatif, build, déploiement ou essai fonctionnel n'est
inclus dans ce travail documentaire (#39).
