# Manifestes, découverte et versions

## Lecture ascendante explicite

[schema/manifest.v1.schema.json](../schema/manifest.v1.schema.json) et
[schema/catalogue-index.v1.schema.json](../schema/catalogue-index.v1.schema.json)
restent inchangés. Tous les anciens manifestes, y compris les ressources,
[le catalogue](../catalogue/index.json), le flow à étapes `flow.json`
et le preset historique `preset.json` sont conservés à l'identique.

Les nouveaux contrats sont référencés par
[examples/catalogue/contracts.v1.json](../examples/catalogue/contracts.v1.json), validé avec
[contracts-index.v1](../schema/contracts-index.v1.schema.json). Ses chemins sont
**relatifs à la racine du dépôt**, y compris `legacyIndex` ; ceux d'un manifeste
(`files`, `operations`, `blocks`, `pack.installation`) sont relatifs au paquet.
Les chemins absolus, traversées et liens sortants sont interdits.

L'index du catalogue est unique ; `contracts.v1.json` ne décrit que des exemples. Un lecteur de contrats charge l'index. Pour chaque
entrée, il vérifie que `id`, `type` et `version` correspondent au manifeste,
résout ses contrats et refuse les identifiants dupliqués ou divergents. Il ne
fusionne jamais deux définitions concurrentes selon leur ordre de lecture.

[manifest.v1.1](../schema/manifest.v1.1.schema.json) accepte soit **exactement**
l'ancien manifeste 1.0.0, soit un manifeste `schemaVersion: "1.1.0"` permettant
les types `app` (application) et `pack`, `block`, `operations`, `blocks` et les
métadonnées de pack. Les champs nouveaux ne deviennent pas autorisés dans un
document étiqueté 1.0.0.

## Types, propriété et dépendances

L'index porte les types `app`, `plugin`, `block`, `flow`, `pack` et les éléments « Autre »
(`preset`, `resource.*`). Un bloc porte `owner` (id du plugin) et son fichier est rangé
sous `plugins/<nom>/blocks/`. Une dépendance de plugin vers une application porte
`optional: true` : elle est proposée, jamais imposée. Règles par type :
[distinctions-catalogue.md](distinctions-catalogue.md) ; contrôle :
`python3 scripts/check_catalogue.py`.

| Consommateur | Fiche 1.0.0 | Fiche 1.1.0 |
| --- | --- | --- |
| Ancien lecteur v1 | Comportement existant | Refus explicite ; pas de repli vers une exécution |
| Lecteur v1.1 | Branche du schéma v1 inchangée | Branche étendue du schéma v1.1 |

Compatibilité ascendante signifie donc qu'un nouveau lecteur lit l'ancien
catalogue. Elle ne signifie pas qu'un ancien lecteur connaît les packs ou blocs. Le type
historique `tool` est devenu `app` (ids `tool.*` → `app.*`, ancien `app.media` → `pack.media`).
Aucune migration des ressources ni nouvelle API applicative n'est livrée ici.

## Trois versions différentes

- `schemaVersion` choisit la forme du document. Les nouveaux contrats d'opération,
  bloc, flow, preset, installation et invocation utilisent **1.0.0**.
- `version` versionne le contenu d'un élément ; l'exemple vaut **0.0.0**, jamais
  une preuve de validation fonctionnelle. Une version publiée est immuable.
- La version réelle du binaire apparaît dans `metadata.toolVersion`, indépendamment
  de la version de fiche catalogue `app.mkvtoolnix@1.0.0`.

Le graphe, ses blocs, opérations et dépendances installées utilisent des versions
**exactes** ; les plages des anciennes fiches restent des indications historiques.
Le résolveur doit vérifier la cohérence globale avant activation. Un changement
de nom/type d'entrée, de sortie, d'effet ou de permission exige une nouvelle
version de contenu et un refus de substitution automatique. Une rupture du
format de contrat exige un nouveau schéma majeur ; un ajout de champ exige un
schéma identifié, car les objets sont fermés (`additionalProperties: false`).

Les `$id` sous `https://flux-de-fichiers.local/schema/` sont des identifiants,
**pas des services réseau**. Le consommateur construit un registre local depuis
`schema/` et résout les `$ref` relatifs sans téléchargement. Les schémas ne
valident ni les droits, ni les cycles, ni les sommes de quotas : voir les
[contrôles sémantiques](garanties-execution-v1.md#validation-sémantique-en-complément-des-schémas).
