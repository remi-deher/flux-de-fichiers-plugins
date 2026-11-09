# Interfaces d’outils (contrat applicatif)

Objectif : permettre plus tard de **choisir** un outil de traitement ou de stockage
sans coupler le cœur applicatif à une CLI précise. Les choix **actuels** restent
PostgreSQL et MKVToolNix.

Ces interfaces sont décrites pour l’intégration future dans le dépôt applicatif.
Elles ne sont **pas** implémentées ici.

## `Remuxer`

Responsabilité : remuxage sans réencodage d’un conteneur média.

| Élément | Valeur actuelle |
|---------|-----------------|
| Implémentation | MKVToolNix (`mkvmerge`) |
| Invocation | binaire dans l’image Docker applicative |
| Fiche catalogue | `tool.mkvtoolnix` |

Opérations minimales à prévoir côté application :

1. `probe_or_prepare(input_path) -> RemuxPlan` (optionnel selon l’outil).
2. `remux(plan, output_path) -> RemuxResult` (chemins, code retour, journal).
3. `supports(capability)` pour refuser tôt un format non géré.

Adaptation actuelle : le module applicatif qui invoque `mkvmerge` devient
l’unique adaptateur `Remuxer` ; le reste du worker dépend de l’interface, pas de
la CLI. Aucune autre implémentation n’est validée.

## `MetadataStore`

Responsabilité : persistance des métadonnées (jobs, baux, état).

| Élément | Valeur actuelle |
|---------|-----------------|
| Implémentation | PostgreSQL via SQLx |
| Invocation | service Compose `db` |
| Fiche catalogue | `tool.postgresql` |

Frontière stricte :

- **Migrations applicatives** (`flux-de-fichiers/migrations/`) : schéma métier.
- **Déploiement instance** (image Postgres, `pg_hba`, TLS, secrets fichiers) :
  modèles documentés sous `tools/postgresql/deploy/`.

## Capacités futures (non validées)

Le schéma réserve `capability: transcode | analyze | other` pour d’autres outils.
Aucune fiche « alternative » n’est créée volontairement, afin d’éviter un choix
implicite.
