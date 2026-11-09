# Contrat opérations et argv sûr (v1 / v1.1)

## Schémas

| Fichier | Rôle |
|---------|------|
| `schema/operation.v1.schema.json` | Opération v1 (conservé, modèle Backend) |
| `schema/command-argv.v1.schema.json` | argv v1 (conservé) |
| `schema/operation.v1.1.schema.json` | Opération durcie (#40) |
| `schema/command-argv.v1.1.schema.json` | argv durci (#40) |
| `plugins/remux-mkv.example/operations/remux.json` | Exemple **1.1.0** |
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
