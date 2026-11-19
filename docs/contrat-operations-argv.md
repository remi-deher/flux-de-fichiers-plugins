# Contrat opérations et argv sûr (v1 / v1.1)

## Schémas

| Fichier | Rôle |
|---------|------|
| `schema/operation.v1.schema.json` | Opération v1 (conservé, modèle Backend) |
| `schema/command-argv.v1.schema.json` | argv v1 (conservé) |
| `schema/operation.v1.1.schema.json` | Opération durcie (#40) |
| `schema/command-argv.v1.1.schema.json` | argv durci (#40) |
| `examples/catalogue/plugins/remux-mkv.example/operations/remux.json` | Exemple **1.1.0** |
| `docs/migration-schemas-v1.1.md` | Migration |

## Frontière sans shell libre (normative v1.1)

1. `executable` + `argv[]` (sans répéter l'exécutable) ; `shell: false`.
2. `forbidden` obligatoire : shell, interpolation, eval, responseFiles — `const true`.
3. `optionPolicy.mode: closed-list` + `allowedFlags`.
4. `pathPolicy` : refs opaques, deny `..` / symlinks sortants / chemins clients absolus.
5. `$param` dynamiques ; secrets uniquement via `$secretFile` env, jamais argv.
6. `permissions.executableAllowlist` borne `command.executable`.
7. Pas d'héritage d'env global ; `LD_PRELOAD` / `LD_LIBRARY_PATH` exclus.

## MKVToolNix

Codes (doc officielle) : **0** succès ; **1** succès avec avertissements
(`warningValues` / `warningsPreserved`) ; **2** erreur.
Source : https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.exit_codes

## FFmpeg / MP4

`examples/pending/ffmpeg-mp4.pending/` — **pending-decision**, pas production.

## Outils auxiliaires, original et entrées non média

Trois champs, lus par le cœur depuis la version qui les introduit, étendent les runtimes `binary` et `script` :

- **`pathTools`** (`binary`, `script`) : outils du catalogue placés en tête du `PATH` de la commande, pour un outil qui en appelle d'autres (ab-av1 et alass appellent `ffmpeg`, l'OCR enchaîne `mkvextract` et `tesseract`). Ils comptent parmi les outils requis du flux et sont donc installés sur les workers.
- **Chemin `reference`** (`binary`, `{ "param": "reference", "as": "filePath" }`) et **`sourceFile`** (entrée JSON d'un `script`) : fichier d'origine de la tâche, pour comparer un encodage à sa source (VMAF) ou y relire des métadonnées (Dolby Vision, HDR10+).
- **`acceptsNonMedia`** (`script`) : le script accepte une entrée non média (archive). Un flux qui le contient tolère l'échec de la sonde initiale ; lorsqu'un script remplace le fichier de travail sans fournir `mediaInfo`, le nouveau fichier est inspecté.

Les scripts de plugins (`entrypoint` relatif au dossier du plugin) sont testés par `scripts/test_plugin_scripts.py`, avec de faux outils dans le `PATH`.
