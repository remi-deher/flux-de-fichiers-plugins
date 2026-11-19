# Interfaces d’outils (contrat applicatif)

Objectif : permettre plus tard de **choisir** un outil de traitement ou de stockage
sans coupler le cœur applicatif à une CLI précise. Le remuxer validé est MKVToolNix ; les métadonnées applicatives reposent sur SQLite local (`/config/flux.db`).

Ces interfaces sont décrites pour l’intégration future dans le dépôt applicatif.
Elles ne sont **pas** implémentées ici.

## `Remuxer`

Responsabilité : remuxage sans réencodage d’un conteneur média.

| Élément | Valeur actuelle |
|---------|-----------------|
| Implémentation | MKVToolNix (`mkvmerge`) |
| Invocation | Option B — binaire autonome hors image (`host-binary` + `distribution.v1.json`) |
| Fiche catalogue | `mkvtoolnix` |

Opérations minimales à prévoir côté application :

1. `probe_or_prepare(input_path) -> RemuxPlan` (optionnel selon l’outil).
2. `remux(plan, output_path) -> RemuxResult` (chemins, code retour, journal).
3. `supports(capability)` pour refuser tôt un format non géré.

Adaptation actuelle : le module applicatif qui invoque `mkvmerge` devient
l’unique adaptateur `Remuxer` ; le reste du worker dépend de l’interface, pas de
la CLI. Aucune autre implémentation n’est validée.

## `MetadataStore` (archive historique)

Responsabilité : persistance des métadonnées (jobs, baux, état) — le socle applicatif utilise SQLite local (`/config/flux.db`, ADR 0001).

| Élément | Valeur |
|---------|--------|
| Implémentation historique | PostgreSQL via SQLx |
| Archive | `examples/legacy/postgresql/` (hors catalogue actif) |

Frontière stricte :

- **Migrations applicatives** (`flux-de-fichiers/migrations/`) : schéma métier.
- **Modèles historiques** (`pg_hba`, TLS) : archivés sous `examples/legacy/postgresql/deploy/`.

## `MediaProbe` (FFmpeg distribué)

| Élément | Valeur |
|---------|--------|
| Implémentation | FFmpeg / ffprobe |
| Invocation | Option B — binaire autonome |
| Fiche | `ffmpeg` |
| Rôle validé | Médias synthétiques de tests / analyse |
| Non validé | Remux / MP4 production (`examples/pending/`) |

## `NodeTelemetryProbe`

| Élément | Valeur |
|---------|--------|
| Implémentation | `flux-telemetry` (interne) |
| Invocation | Option B — binaire autonome, préférer préchargement offline |
| Fiche | `telemetrie` |
| Métriques | CPU, RAM, GPU, stockage |

## Capacités futures (non validées)

Le schéma réserve `capability: transcode | analyze | other`. FFmpeg n’est pas
le remuxer production ; MKVToolNix reste le choix remux.
