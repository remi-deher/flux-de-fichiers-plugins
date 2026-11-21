# Créer et publier un dépôt de plugins tiers

Toute personne peut héberger son propre dépôt de plugins, d'applications, de flows,
de packs ou de ressources « Autre » pour **Forgearr**, sans avoir à soumettre
ses fichiers dans le dépôt officiel.

## 1. Prérequis imposés par le moteur

Lors de la synchronisation (`src/plugins/sync.rs` dans `flux-de-fichiers`), le serveur impose :

- **URL d'index** : doit être accessible en HTTPS public (ou HTTP privé en labo avec
  `PLUGIN_ALLOW_PRIVATE_HOSTS=1`) et **se terminer exactement par `/index.json`**.
- **Quotas** : au maximum **500 fichiers** et **1 Mio par fichier JSON** (les archives
  d'applications Option B sont téléchargées séparément jusqu'à 256 Mio via `distribution.v1.json`).
- **Propriété des blocs** : un bloc (`type: "block"`) doit avoir `owner` pointant vers
  un `plugin` déclaré dans **le même `index.json`** et être rangé sous `<dossier-du-plugin>/blocks/`.
- **Empreintes SHA-256** : lorsque `sha256` est présent sur une entrée de `index.json`,
  Forgearr refuse tout manifeste dont l'empreinte ne correspond pas.

## 2. Démarrer depuis le modèle ou le CLI

### Option A — Copier le modèle `templates/depot-tiers/`

Copiez le contenu de [templates/depot-tiers/](../templates/depot-tiers/README.md) à la racine de
votre propre dépôt GitHub / GitLab / Forgejo, puis remplacez `org.exemple` par votre espace de noms.

### Option B — Initialiser via `scaffold.py`

Depuis un clone local de `flux-de-fichiers-plugins` :

```bash
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo init-repo --with-example
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo plugin mon-outil --kind http --name "Mon Outil"
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo app mon-binaire --name "Mon Binaire" --executable mon-bin
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo flow mon-flow --name "Mon Flow" --plugin-id com.monpseudo.plugin.mon-outil
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo pack mon-pack --name "Mon Pack" --plugin-id com.monpseudo.plugin.mon-outil
python3 scripts/scaffold.py --root ../mon-depot-plugins --namespace com.monpseudo resource ma-lut --name "Ma LUT" --type resource.color
```

## 3. Règle d'or anti-collision : utiliser un namespace

Quand plusieurs dépôts sont synchronisés sur une même instance Forgearr, **le premier
dépôt qui déclare un `id` l'emporte**. Pour ne jamais masquer une pièce officielle ni entrer en
conflit avec un autre auteur :

- Les identifiants courts (`ffmpeg`, `essentiel`, `video`, `audio`, `sonarr`, `media`…) sont
  réservés au catalogue officiel : le type est porté par le champ `type`, jamais par l'identifiant.
- Préfixez tous vos identifiants avec un espace de noms inversé :
  - `<namespace>.<nom>` pour un plugin, une application ou un pack (ex. `com.alice.sous-titres`)
  - `<namespace>.<plugin>.<action>` pour un bloc (ex. `com.alice.sous-titres.extract-srt`)
  - `<namespace>.operation.<nom>` pour une opération (ex. `com.alice.operation.extract-srt`)

## 4. Dépendre d'une application ou d'un bloc officiel

Vous n'avez **pas** besoin de recopier `ffmpeg`, `mkvtoolnix` ou `essentiel` dans
votre dépôt :

- Dans `manifest.json` → `dependencies` : référencez `ffmpeg` avec `"optional": true`.
- Dans `operations/*.json` → `runtime.tool.id` : référencez `"ffmpeg"`.
- Dans `blocks/*.json` → `ui.suggestedNext` : référencez `"essentiel.file-output"`.

### Classer son plugin : `category` et `subcategory`

Le catalogue de Forgearr regroupe les plugins par **sous-catégorie**. Ce vocabulaire appartient à
Forgearr (registre officiel versionné, [ADR 0023](https://github.com/remi-deher/flux-de-fichiers/blob/dev/docs/adr/0023-taxonomie-officielle-des-sous-categories-de-plugins.md)) :
un dépôt **référence** un identifiant, il ne peut ni en créer ni fournir de libellé.

```json
{ "category": "media", "subcategory": "media-servers" }
```

- `subcategory` exige `category` et doit être rattachée à cette catégorie dans le registre.
- Identifiants actuels : `media-servers`, `media-managers`, `media-encoding` et `media-subtitles` (catégorie `media`), `notifications` (catégorie `io`).
- Une valeur inconnue, mal formée ou rattachée à une autre catégorie **n'invalide pas le plugin** : il reste
  simplement sous sa catégorie, et l'écran du dépôt dans Forgearr signale l'avertissement.
- Il manque une famille ? Proposez-la par une PR sur le registre `subcategories.v1.json` du dépôt Forgearr.
- Le hors-registre (mots libres) va dans `tags`, pas dans `subcategory`.

## 5. Valider son dépôt en local et en CI

Générez ou vérifiez votre index et ses empreintes SHA-256 :

```bash
python3 scripts/build_index.py --root ../mon-depot-plugins
python3 scripts/check_catalogue.py \
  --root ../mon-depot-plugins \
  --schema-dir schema \
  --external-index index.json
```

Le workflow prêt à l'emploi [templates/depot-tiers/.github/workflows/check-catalogue.yml](../templates/depot-tiers/.github/workflows/check-catalogue.yml)
automatise cette validation sur chaque PR dans votre propre dépôt.

## 6. Tester en local avec Forgearr

1. Démarrez Forgearr avec `PLUGINS_DIR=/chemin/vers/mon-depot-plugins` (prioritaire sur les dépôts distants), **ou**
2. Servez votre dépôt en HTTP local, activez `PLUGIN_ALLOW_PRIVATE_HOSTS=1` sur le central,
   et ajoutez `http://127.0.0.1:<port>/index.json` dans **Plugins → Dépôts**.

## 7. Publier proprement (tags figés et releases immuables)

- Évitez de faire pointer vos utilisateurs en production sur une branche mouvante (`dev` / `main`) :
  publiez un tag SemVer (`v1.0.0`) avec le workflow
  [release-catalogue.yml](../templates/depot-tiers/.github/workflows/release-catalogue.yml) et activez les
  **Immutable Releases** sur GitHub (*Settings → General → Releases → Enable immutable releases*) afin
  qu'aucune archive ni manifeste d'une version publiée ne puisse être écrasé silencieusement.
  Détails complets : [releases-immuables.md](releases-immuables.md).
- Fournissez l'URL figée du tag à vos utilisateurs :
  `https://raw.githubusercontent.com/<compte>/<depot>/v1.0.0/index.json`.
