# Contrat distribution d'outils binaires (Option B)

Option B validée utilisateur : les outils s'exécutent comme **binaires
autonomes hors conteneur applicatif**, avec cache nœud et vérification
d'intégrité. Ce dépôt ne livre ni binaire ni installeur — uniquement le contrat.

## Schéma

| Fichier | Rôle |
|---------|------|
| `schema/tool-distribution.v1.schema.json` | Artefacts par arch + politique d'install |
| `tools/*/distribution.v1.json` | Instances déclaratives |

## Champs obligatoires par architecture

Pour `x86_64` et `aarch64` :

1. `archiveUrl` — HTTPS (ou URI illustrative `contract-only`)
2. `archiveFormat` — `tar.gz` | `tar.xz` | `zip`
3. `archiveSha256` — empreinte **obligatoire** (64 hex)
4. `binaryRelativePath` — chemin relatif sans `..`
5. `permissions` — `unixMode` (ex. `0755`), `owner: runtime-user`, `executableBit: true`

Optionnel recommandé : `binarySha256` du fichier extrait.

## Politique d'installation

- `verifySha256BeforeExec: true`
- `refuseMismatchedDigest: true`
- `noShellUnpack: true` (pas de `/bin/sh -c`)
- `executableAllowlist` bornant les noms lancés
- `cacheRootRelative` sous `tools-cache/<outil>/<version>/`

## Manifestes officiels

| Outil | Fiche | Distribution |
|-------|-------|--------------|
| MKVToolNix | `apps/mkvtoolnix/` | remux validé |
| FFmpeg | `apps/ffmpeg/` | tests/analyse ; MP4 prod pending |
| Télémétrie | `apps/internal-telemetry/` | CPU/RAM/GPU/stockage |

`releaseStatus: contract-only` tant que les empreintes/URL ne sont pas celles
d'une release réelle.

## Guide d'usage (futur runtime)

1. Lire `distribution.v1.json` pour le `toolId` + version épinglée.
2. Choisir l'artefact selon l'arch du nœud.
3. Télécharger ou précharger l'archive ; vérifier `archiveSha256`.
4. Extraire sans shell ; vérifier mode/`executableBit` ; optionnellement
   `binarySha256`.
5. Lancer uniquement un nom de `executableAllowlist` via argv paramétré.

Aucun code applicatif n'est ajouté par ce contrat (#41).
