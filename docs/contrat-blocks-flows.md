# Contrats blocs low-code et flows (v1 / v1.1)

## Schémas

| Fichier | Rôle |
|---------|------|
| `schema/block.v1.schema.json` | v1 conservé (sockets déjà typés) |
| `schema/flow.v1.schema.json` | v1 conservé (DAG, stop on error) |
| `schema/block.v1.1.schema.json` | mediaType requis si file |
| `schema/flow.v1.1.schema.json` | `dataType` sur edges + `runtimeNote` |
| `examples/catalogue/plugins/remux-mkv.example/blocks/remux-mkv.example/` | Exemple **1.1.0** |
| `examples/catalogue/flows/remux-rapide.example/flow.v1.json` | Exemple **1.1.0** |

## Modèle v1.1

1. Block → opération avec `operationVersion` exacte ; sockets `dataType` (+ `mediaType` si file).
2. Flow DAG ; chaque nœud épingle `blockVersion`.
3. Chaque edge porte `dataType` aligné sur les ports.
4. `errorPolicy: stop` ; `runtimeNote` const (catalogue ≠ moteur).

`flows/.../flow.json` historique conservé si présent.
