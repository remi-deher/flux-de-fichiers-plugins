# Variables exposées par les plugins

Un plugin peut **exposer** des valeurs qu'il calcule (le codec d'un fichier, sa largeur…) pour que
les scripts les utilisent dans leurs variables, avec `{{espace.nom}}`. Un script déclare les variables
qu'il **consomme** : c'est une dépendance, contrôlée comme les autres.

Ce contrat est celui de Forgearr (ADR 0025). Le central revalide ces déclarations à la
synchronisation du dépôt : il écarte, avec un avertissement, toute opération dont `exposes`,
`variables` ou `requires` sont invalides. `scripts/check_catalogue.py` applique les mêmes règles
avant publication.

## Exposer des variables (`exposes`)

`exposes` se déclare à la racine du fichier d'**opération** (`plugins/<slug>/operations/*.json`),
et non dans le manifeste : les workers ne reçoivent que les opérations.

```json
"exposes": {
  "namespace": "mediainfo",
  "contractVersion": "1.0.0",
  "variables": [
    { "name": "video.codec", "label": "Codec vidéo", "type": "text",
      "path": "mediainfo.media.track[@type=Video].Format" }
  ]
}
```

- `namespace` : propre au plugin (`[a-z][a-z0-9_]*`), jamais `nodes`. La référence complète est
  `namespace.name`, ici `{{mediainfo.video.codec}}`. Un plugin ne peut exposer que dans son espace.
- `name` : relatif à l'espace de noms, en identifiants séparés par des points. Un nom ne peut pas
  être à la fois une valeur et un groupe (`video` et `video.codec` ensemble sont refusés).
- `type` : `text` (défaut), `multiline`, `number`, `boolean` ou `choice`. Jamais `secret`.
- `path` : requête dans `mediaInfo` après l'opération du plugin. Pour une sonde qui enrichit
  (`executionMode: "probe-enrich"`), le chemin commence par sa `probeEnrichmentKey`
  (ici `mediainfo`). Une valeur absente ou nulle n'est pas disponible : la variable du script
  retombe sur sa valeur par défaut, sinon l'étape échoue en le disant.

### Syntaxe des chemins

| Forme | Sens |
|---|---|
| `a.b.c` | clés d'objets |
| `liste[0]` | élément d'un tableau par son indice |
| `liste[*]` | tous les éléments (la première valeur non nulle est retenue) |
| `liste[clé=valeur]` | éléments dont `clé` vaut `valeur` (casse ignorée), par exemple `track[@type=Video]` |

Préférez `[clé=valeur]` aux indices : l'ordre des pistes d'un fichier varie.

### Fixture obligatoire

Chaque opération qui expose des variables est accompagnée d'une **fixture** :
`plugins/<slug>/fixtures/<nom-de-l-opération>.json`, un exemple réaliste de `mediaInfo` après
l'opération. `check_catalogue.py` exige que chaque `path` s'y résolve. Les fixtures ne sont pas
publiées (aucun manifeste ne les référence).

### Versionner le contrat

`contractVersion` suit `MAJEUR.MINEUR.CORRECTIF`. Retirer, renommer ou changer le type d'une variable,
ou changer l'espace de noms, **impose une montée du majeur** : sans elle, la CI échoue. Ajouter une
variable ou modifier un chemin ne le demande pas. La CI compare le contrat à celui de la branche de
base (`CATALOGUE_BASE_REF`, renseignée par le workflow `check-catalogue`).

## Consommer des variables (`requires`)

Un script déclare, dans `runtime.requires` de son opération, les variables exposées qu'il utilise :

```json
"requires": [
  { "variable": "mediainfo.video.codec", "provider": "mediainfo", "contractMajor": 1 }
]
```

- `provider` : identifiant du plugin fournisseur dans le catalogue.
- `contractMajor` : version majeure du contrat visée (1 par défaut).
- `repository` (facultatif) : `{ "id": "…", "indexUrl": "https://…/index.json" }` si le fournisseur
  est publié dans un autre dépôt. Forgearr le signale sans jamais l'ajouter tout seul.
- `dependenciesUnverified: true` intègre le script sans ses dépendances : elles ne sont ni contrôlées
  ni installées et les valeurs se saisissent à la main.

Les variables saisissables d'un script se déclarent dans `runtime.variables` (types `text`,
`multiline`, `number`, `boolean`, `choice`, `secret`) ; le script les lit dans `config` sur `stdin`.

## Compatibilité

Forgearr 0.70.0 lit `exposes`, `requires` et `variables`, mais n'accepte que des chemins sans sélecteur
(`a.b`, `a.0.b`). Les chemins avec `[clé=valeur]` demandent la version suivante : **ne publiez pas une
opération qui les utilise avant que les installations ne soient à jour**, car une opération dont
`exposes` est refusé est écartée entièrement à la synchronisation.
