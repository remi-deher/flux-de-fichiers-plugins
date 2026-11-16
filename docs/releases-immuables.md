# Releases immuables et chaîne d'intégrité

Ce document décrit comment **Flux de Fichiers** et les dépôts de plugins (officiel
et tiers) garantissent qu'une version publiée ne peut jamais être altérée silencieusement.

## 1. Principe en deux couches

1. **Côté hébergeur GitHub (*Immutable Releases*)** :
   - Activez **Settings → General → Releases → Enable immutable releases** sur le dépôt.
   - Une fois publiée (hors `--draft`), GitHub interdit la modification/suppression des assets
     ainsi que le déplacement du tag Git.
   - Les workflows [build-tools.yml](../.github/workflows/build-tools.yml) et
     [release-catalogue.yml](../.github/workflows/release-catalogue.yml) créent toujours une
     release `--draft`, vérifient l'absence d'une release déjà publiée sous le même tag
     (zéro `--clobber`), téléversent les assets + `SHA256SUMS.txt`, puis publient.

2. **Côté moteur `flux-de-fichiers` (garantie indépendante de l'hébergeur)** :
   - `index.json` à la racine embarque les empreintes SHA-256 de chaque manifeste (`entries[].sha256`)
     et de chaque fichier JSON secondaire (`filesSha256` : `distribution.v1.json`,
     `operations/*.json`, `installation.json`).
   - Lors de la synchronisation et de l'installation d'outils, le central épingle en SQLite
     (`plugin_release_pins`) le couple `(version, sha256)` observé. Si une même version
     réapparaît avec une empreinte différente, la mise à jour est **refusée** et l'ancienne
     copie saine reste active.
   - Avec `PLUGIN_REQUIRE_IMMUTABLE_RELEASES=1`, le central impose en plus :
     - une URL pointant vers un tag/release figé (refus de `/dev/`, `/main/`, `/refs/heads/`) ;
     - la présence de `releaseVersion` et des empreintes SHA-256 sur 100 % des fichiers ;
     - des applications en statut `released` avec URLs figées.

## 2. Cycles de vie : branche de travail vs release publiée

- Sur une **branche de travail** (`dev` / PR), `releaseVersion` reste absent de `index.json`
  tout en conservant les `sha256` et `filesSha256` à jour via `python3 scripts/build_index.py`.
- Au **tag de release** (`catalogue-vX.Y.Z` pour le dépôt officiel, `vX.Y.Z` pour un dépôt tiers),
  `release-catalogue.yml` injecte `releaseVersion` via `--release-version` et contrôle le tout
  avec `check_catalogue.py --strict-immutable`.

## 3. Activer pour un dépôt tiers

Copiez [templates/depot-tiers/.github/workflows/release-catalogue.yml](../templates/depot-tiers/.github/workflows/release-catalogue.yml)
dans votre dépôt et activez **Immutable Releases** dans les paramètres GitHub de votre dépôt.
