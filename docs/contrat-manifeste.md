# Contrat manifeste v1

## Fichiers

| Fichier | Rôle |
|---------|------|
| `schema/manifest.v1.schema.json` | Schéma d’une fiche individuelle |
| `schema/catalogue-index.v1.schema.json` | Schéma de l’index |
| `catalogue/index.json` | Index réel (références uniquement) |

## Règles

1. Chaque élément exposé au catalogue possède un `manifest.json` à sa racine.
2. `id` est stable ; un renommage de dossier ne change pas l’`id`.
3. L’index référence `manifestPath` + métadonnées courtes (`name`, `type`, `version`) ; la description longue reste dans la fiche.
4. `license: UNLICENSED` marque un exemple local sans licence tierce inventée.
5. Aucun actif binaire tiers n’est embarqué dans ce squelette.
6. `schemaVersion: "1.0.0"` est figé pour v1 ; une rupture de contrat imposera `manifest.v2`.

## Champs obligatoires

`schemaVersion`, `id`, `type`, `version`, `name`, `description`, `author`, `license`.

## Champs optionnels utiles

`icon`, `previews`, `files`, `compatibility`, `dependencies`, `integrity`, `tool` (outils).
