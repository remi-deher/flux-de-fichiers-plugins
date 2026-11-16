# Contrat distribution des applications binaires (Option B)

Option B validée utilisateur : les outils s'exécutent comme **binaires
autonomes hors conteneur applicatif**, avec cache nœud et vérification
d'intégrité. Ce dépôt porte le contrat ; les archives sont construites par
`.github/workflows/build-tools.yml` et publiées en Release (voir « Construction »).

## Schéma

| Fichier | Rôle |
|---------|------|
| `schema/tool-distribution.v1.schema.json` | Artefacts par arch + politique d'install |
| `apps/*/distribution.v1.json` | Instances déclaratives |

## Champs obligatoires par architecture

Pour `x86_64` et `aarch64` :

1. `archiveUrl` — HTTPS (ou URI illustrative `contract-only`)
2. `archiveFormat` — `tar.gz` | `tar.xz` | `zip`
3. `archiveSha256` — empreinte **obligatoire** (64 hex)
4. `binaryRelativePath` — chemin relatif sans `..`, relatif au dossier d'extraction
   du cache du nœud (`tools-cache/<outil>/<version>/<arch>/bin/`) : `mkvmerge`, pas `bin/mkvmerge`
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

## Construction des artefacts

`.github/workflows/build-tools.yml` (déclenché à la main par outil ou par un push
d'une recette `apps/*/build.json` sur `dev`, voir aussi [releases-immuables.md](releases-immuables.md)) :

1. lit chaque recette `apps/<outil>/build.json`, installe les paquets dans `debian:bookworm`
   (ou compile GPAC pour `mp4box`) sur `x86_64` et `aarch64` ;
2. copie les binaires et leurs bibliothèques hors glibc, fixe le `RUNPATH` à `$ORIGIN/lib`
   (exécutables) et `$ORIGIN` (bibliothèques), et joint un `SOURCES.txt` ;
3. teste les archives sans variable d'environnement dans `debian:bookworm-slim` ;
4. publie `<outil>-linux-<arch>.tar.gz` et `SHA256SUMS.txt` dans une Release **immuable**
   `<releaseTagPrefix>-<toolVersion>` (brouillon puis publication, sans `--clobber`) ;
5. met à jour `apps/*/distribution.v1.json` (y compris `binaries` et `upstreamVersion`),
   régénère `index.json` à la racine et ouvre une Pull Request vers `dev`.

La glibc n'est jamais embarquée : le nœud doit être basé sur Debian bookworm ou plus récent.

