# Contribuer à `flux-de-fichiers-plugins`

Ce dépôt porte le **catalogue officiel** de Forgearr et sert de référence
technique pour la communauté.

> Vous souhaitez publier vos propres plugins dans **votre propre dépôt** ?
> Consultez directement le guide dédié : [docs/creer-un-depot-tiers.md](docs/creer-un-depot-tiers.md)
> ainsi que le modèle prêt à copier [templates/depot-tiers/](templates/depot-tiers/README.md).

## Ajouter ou modifier un élément dans ce dépôt

1. Créez la pièce avec l'assistant (ou manuellement en respectant les schémas sous `schema/`) :
   ```bash
   python3 scripts/scaffold.py plugin mon-plugin --name "Mon Plugin" --kind http
   ```
2. Mettez à jour `index.json` et ses empreintes SHA-256 :
   ```bash
   python3 scripts/build_index.py
   ```
3. Validez les schémas, dépendances, empreintes et liens Markdown :
   ```bash
   python3 scripts/check_catalogue.py
   python3 scripts/build_index.py --check
   ```
4. Ouvrez une Pull Request vers `dev` (ne modifiez jamais `index.json` à la main sans
   relancer `build_index.py`).
5. Après la fusion de `dev` dans `main`, la **Release du catalogue se publie automatiquement**
   quand le catalogue a changé (`auto-release.yml`) : la version suit vos commits conventionnels
   (`feat:` mineure, `fix:` correctif, `feat!:` majeure). Voir
   [docs/releases-immuables.md](docs/releases-immuables.md).

## Conventions de structure

- **Applications (`apps/<slug>/`)** : `manifest.json` + `distribution.v1.json` (Option B) + `README.md`.
- **Plugins (`plugins/<slug>/`)** : `manifest.json` (déclare les blocs avec `role: "block"` et les opérations avec `role: "operation"`), `blocks/*.json`, `operations/*.json`, `README.md`.
- **Variables exposées** : une opération peut déclarer `exposes` (avec une fixture
  `plugins/<slug>/fixtures/<opération>.json`) ; un script, `requires`. Voir
  [docs/variables-exposees.md](docs/variables-exposees.md).
- **Flows (`flows/<slug>/`)** : `manifest.json` (`schemaVersion: "1.1.0"`) + `README.md` éventuel.
- **Packs (`packs/<slug>/`)** : `manifest.json` + `installation.json` + `README.md`.
