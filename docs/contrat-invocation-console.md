# Contrat invocation et capture console (v1 / v1.1)

## Schémas

| Fichier | Rôle |
|---------|------|
| `schema/invocation.v1.schema.json` | v1 conservé |
| `schema/console-capture.v1.schema.json` | v1 conservé |
| `schema/invocation.v1.1.schema.json` | warningsPreserved, capture_expired, policy v1.1 |
| `schema/console-capture.v1.1.schema.json` | failClosed, nullMeans, noUnlimitedRetention |
| `examples/invocation/remux-mkv.*.json` | Exemples **1.1.0** |

## Capture obligatoire

- stdout/stderr : `capture: true` (non désactivable).
- Masquage : `enabled`/`failClosed` const true → sinon `capture_failed`.
- `exitCode: null` = not_started / signalled / unknown_after_worker_loss.
- Un code 0 ne suffit pas à publier (`output_invalid` possible).
- Codes d'erreur : `spawn_failed`, `tool_failed`, `output_invalid`,
  `capture_failed`, `capture_expired`, `process_signalled`, `worker_lost`, …

## Limites

Politique finie avant démarrage (octets, timeout, grâce, TTL).
Aucune rétention illimitée (`noUnlimitedRetention`).
