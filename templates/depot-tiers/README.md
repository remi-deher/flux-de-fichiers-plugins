# Dépôt de plugins tiers — Modèle autonome

Ce dossier est un dépôt modèle prêt à être copié dans votre propre dépôt Git
(GitHub, GitLab, Forgejo, Gitea ou serveur HTTPS statique).

## Mise en route rapide

1. Copiez le contenu de `templates/depot-tiers/` à la racine de votre propre dépôt.
2. Remplacez le namespace `org.exemple` par votre identifiant éditeur (ex. `com.monpseudo` ou `io.monorg`).
3. Adaptez `plugins/mon-plugin/` (ou ajoutez vos plugins/apps/flows via `scaffold.py`).
4. Régénérez `index.json` à la racine (et ses empreintes `sha256`) avec `build_index.py`.
5. Vérifiez avec `check_catalogue.py` puis publiez un tag ou une release immuable.

## URL à déclarer dans Forgearr

Dans l'interface **Plugins → Dépôts**, ajoutez l'URL complète se terminant par `/index.json` :

- Release / tag figé (recommandé en production) :
  `https://raw.githubusercontent.com/<compte>/<depot>/v1.0.0/index.json`
- Branche de développement (test uniquement) :
  `https://raw.githubusercontent.com/<compte>/<depot>/main/index.json`
