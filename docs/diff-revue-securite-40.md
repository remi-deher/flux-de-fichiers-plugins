# Diff lisible — revue sécurité #40 → schémas v1.1

Référence : `docs/garanties-execution-v1.md`.
Stratégie : **v1.1 additive** sur le modèle Backend v1 (pas de rupture silencieuse).

## P0 — maintenant normatifs dans `*.v1.1.schema.json`

| Écart | v1 (Backend) | v1.1 |
|-------|--------------|------|
| `forbidden` | `shell:false` seul | `forbidden` requis : shell/interpolation/eval/responseFiles = `const true` |
| executable / argv[0] | `executable` + argv sans dup | + `permissions.executableAllowlist` obligatoire |
| Injection d'options | Flags libres possibles | `optionPolicy.mode: closed-list` + `allowedFlags` |
| Paths / symlinks / sandbox | Prose / runtime | `pathPolicy` const (opaque, deny `..`/symlinks, sandbox) |
| Permissions | `readInputs`/`writeOutputs` booléens libres | const true + secrets exclus + filesystem sandbox |
| `secret` → argv | Convention | `allowedInArgv: false` forcé si secret/secretRef |
| stdout/stderr | déjà `capture: true` | conservé + `failClosed` masquage |

## P1

| Écart | v1.1 |
|-------|------|
| Codes d'échec | déjà dans `error.code` v1 (`spawn_failed`, `capture_failed`, `output_invalid`, …) + `capture_expired` |
| `exitCode: null` | `nullMeans` explicite |
| mkvmerge code 1 | `warningValues: [1]` + `exitDocumentation` URL officielle + `warningsPreserved` |
| Edges typées | `dataType` requis sur chaque edge |
| runtimeNote | `const` obligatoire sur flow v1.1 |

## Fichiers

**Schémas nouveaux / réécrits (additifs)**

- `schema/command-argv.v1.1.schema.json`
- `schema/operation.v1.1.schema.json`
- `schema/console-capture.v1.1.schema.json`
- `schema/invocation.v1.1.schema.json`
- `schema/block.v1.1.schema.json`
- `schema/flow.v1.1.schema.json`

**Exemples alignés 1.1.0**

- `examples/catalogue/plugins/remux-mkv.example/operations/remux.json`
- `examples/catalogue/plugins/remux-mkv.example/blocks/remux-mkv.example/block.json`
- `examples/catalogue/flows/remux-rapide.example/flow.v1.json`
- `examples/invocation/remux-mkv.*.json`

**Docs**

- `docs/migration-schemas-v1.1.md`, ce fichier, contrats, questions ouvertes

**Inchangé volontairement**

- Tous les `*.v1.schema.json`
- `examples/pending/ffmpeg-mp4.pending/` (pending)
- Aucun runtime / test local / NAS
