# Variables exposées par les plugins

Un plugin peut **exposer** des valeurs qu'il calcule (le codec d'un fichier, sa largeur…) pour que
les scripts les utilisent dans leurs variables, avec `{$espace.nom}` (modèle unique, ADR 0026). Un script déclare les variables
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

- `namespace` : propre au plugin (`[a-z][a-z0-9_]*`), jamais un espace réservé du moteur (`nodes`,
  `media`, `vars`, `file`, `source`, `work`, `library`, `worker`, `job`, `flow`, `error`, `context`,
  `var`, `setting`, `config`). La référence complète est `namespace.name`, ici
  `{$mediainfo.video.codec}`. Un plugin ne peut exposer que dans son espace.
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

### Déprécier une variable

Pour renommer ou retirer une variable sans casser les scripts, **dépréciez-la d'abord** dans une version
mineure du contrat :

```json
{ "name": "video.codec", "path": "mediainfo.media.track[@type=Video].Format",
  "deprecated": "Renommée en video.codec_name.", "replacedBy": "video.codec_name" }
```

- `deprecated` : message non vide (300 caractères au plus). La variable reste lue ; Forgearr avertit,
  sans bloquer, dans la fiche du plugin, le sélecteur de références, l'aperçu du nœud et la validation du flux.
- `replacedBy` (facultatif) : nom relatif d'une autre variable du même contrat ; exige `deprecated`.
- Retrait : autorisé à la version suivante si la variable était **déjà dépréciée** dans celle de la base ;
  sinon il compte comme changement cassant et impose une montée de version majeure.

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
- Un espace de noms ne se lie qu'à **un** fournisseur et à **une** version majeure par script : c'est la
  dépendance qui décide quelle exposition le script lit quand plusieurs plugins déclarent le même espace
  de noms (sans dépendance, la première par identifiant d'opération l'emporte).
- `dependenciesUnverified: true` intègre le script sans ses dépendances : elles ne sont ni contrôlées
  ni installées et les valeurs se saisissent à la main.

Exemple officiel complet : [`scripts/route-by-video-codec`](../scripts/route-by-video-codec/README.md)
(variable `codec` par défaut `{$mediainfo.video.codec}`, choix du codec attendu, dépendance sur le plugin `video`).

Les variables saisissables d'un script se déclarent dans `runtime.variables` (types `text`,
`multiline`, `number`, `boolean`, `choice`, `secret`) ; le script les lit dans `config` sur `stdin`.

## Compatibilité

### Syntaxe des modèles

Forgearr n'a plus qu'une syntaxe de modèle : `{$expr|défaut}` (ADR 0026). L'ancienne syntaxe
`{{…}}` de l'ADR 0025 est convertie à la lecture et à l'exécution, puis réécrite à l'enregistrement :

| Ancienne | Nouvelle |
| --- | --- |
| `{{workingFile}}` | `{$file.path}` |
| `{{sourceFile}}` | `{$source.path}` |
| `{{workDir}}` | `{$work.dir}` |
| `{{mediaInfo.<chemin>}}` | `{$media.<chemin>}` |
| `{{nodes.<id>.workingFile}}` | `{$nodes.<id>.file}` |
| `{{espace.nom}}` (plugin) | `{$espace.nom}` |

Écrivez `{$…}` dans tout nouveau contenu du catalogue. Un serveur antérieur à l'ADR 0026 ne résout
pas `{$espace.nom}` dans le défaut d'une variable de script : il le transmet tel quel au script.
Aucun champ de manifeste ne fixe de version minimale du serveur ; ne publiez un tel défaut qu'une
fois les installations à jour.

### Chemins à sélecteur

Forgearr 0.70.0 lit `exposes`, `requires` et `variables`, mais n'accepte que des chemins sans sélecteur
(`a.b`, `a.0.b`). Les chemins avec `[clé=valeur]` demandent la version suivante : **ne publiez pas une
opération qui les utilise avant que les installations ne soient à jour**, car une opération dont
`exposes` est refusé est écartée entièrement à la synchronisation.
