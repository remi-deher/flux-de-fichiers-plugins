# Migration schémas v1 → v1.1 (sécurité #40)

Les schémas `*.v1.schema.json` (modèle Backend #39) **restent inchangés**.
Les garanties P0/P1 de `docs/garanties-execution-v1.md` sont portées par des
schémas **additifs** `*.v1.1.schema.json` qui prolongent la même forme JSON
(toolId, fileRef, console-capture imbriquée, DAG flow).

Tout nouveau document catalogue doit cibler `schemaVersion: "1.1.0"`.

## Correspondance

| Domaine | v1 (conservé) | v1.1 (normatif durci) |
|---------|---------------|------------------------|
| Commande argv | `command-argv.v1.schema.json` | `command-argv.v1.1.schema.json` |
| Opération | `operation.v1.schema.json` | `operation.v1.1.schema.json` |
| Console | `console-capture.v1.schema.json` | `console-capture.v1.1.schema.json` |
| Invocation | `invocation.v1.schema.json` | `invocation.v1.1.schema.json` |
| Bloc | `block.v1.schema.json` | `block.v1.1.schema.json` |
| Flow | `flow.v1.schema.json` | `flow.v1.1.schema.json` |

## Changements obligatoires pour migrer un document 1.0.0 → 1.1.0

1. `schemaVersion` → `"1.1.0"` (opération `version` / block / flow aussi).
2. **command** : ajouter `forbidden` (tous `const true`), `pathPolicy`,
   `optionPolicy` (liste fermée + `forbidDoubleDashSeparator`) ;
   `shell: false` conservé ; **ne pas** répéter `executable` dans `argv`.
3. **permissions** : remplacer les booléens libres par
   `inputFilesReadOnly`/`outputFilesExclusive` const true,
   `executableAllowlist`, `secretsInArgv:false`,
   `secretsInConsoleCapture:false`, `filesystem: sandbox-volumes-only`.
4. **parameters** : `allowedInArgv` requis ; `false` si `secret` / `secretRef`.
5. **console** : `secretMasking.failClosed: true` ;
   `exitCode.nullMeans` ; `retention.noUnlimitedRetention: true`.
6. **exitDocumentation** (URL source des codes) sur l'opération.
7. **flow** : `dataType` sur chaque edge ; `runtimeNote` const.
8. **invocation** : `warningsPreserved` si exit dans `warningValues` ;
   `console.policy` conforme v1.1.

## Exemple migré

`plugins/remux-mkv.example/operations/remux.json` → **1.1.0**
(codes mkvmerge documentés : https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.exit_codes).

## Non-objectifs

- Aucune modification silencieuse des schémas v1.
- Aucun runtime, aucun test local/NAS.
- FFmpeg/MP4 reste `examples/pending/` (pending-decision).
