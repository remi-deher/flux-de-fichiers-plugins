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

## Variables de flux et modèles

Le cœur rend les modèles `{$expr}` des réglages d'un bloc avant de construire l'`argv` (binaire) ou l'entrée JSON (script) ; les `defaults` du contrat ne sont jamais rendus. `{$expr|défaut}` utilise `défaut` si la valeur est absente ou vide, `{{$` produit le littéral `{$`, et une chaîne réduite à un seul jeton garde son type JSON.

- Variables intrinsèques : `file.name`, `file.stem`, `file.ext`, `file.dir`, `file.size` (fichier de travail courant), `source.name`, `library.id`, `library.name`, `worker.name`, `job.id`, `flow.id`, et pendant le flux d'échec seulement `error.code`, `error.message`.
- Variables personnalisées : `vars.<nom>`, écrites par le bloc `essentiel.set-variable` ou par la sortie `variables` d'un script (schéma `1.1`, voir [le plugin Scripts](../plugins/scripts/README.md)). Elles suivent la tâche lors d'un relais.
- Les blocs HTTP gardent en plus `context.*`, `setting.*`, `config.*` et `var.*` (variables locales extraites entre étapes, à ne pas confondre avec `vars.*`).
- Une valeur rendue reste un scalaire d'`argv` : un caractère de contrôle (`\0`, `\r`, `\n`) est refusé, et aucun chemin `filePath` ne provient d'une variable.
