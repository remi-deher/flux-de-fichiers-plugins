# Interpréteurs de scripts (`interpreteurs`)

Application fournissant les interpréteurs des scripts `stdin`/`stdout` JSON de Forgearr
(bloc `scripts.run` du plugin `scripts`), sans embarquer de runtimes dans l'image Docker principale.

| Interpréteur | Provenance | Version |
| --- | --- | --- |
| `sh`, `bash` | Image de base (Debian bookworm-slim) | système |
| `python3` | [python-build-standalone](https://github.com/astral-sh/python-build-standalone) (relocalisable) | CPython 3.14.10 |
| `node` | [nodejs.org](https://nodejs.org/dist/) (binaire officiel) | 26.13.1 LTS |
| `jq` | [jqlang/jq](https://github.com/jqlang/jq) (binaire officiel) | 1.8.2 |

`deno`, `bun` et `pwsh` restent sélectionnables dans l'éditeur, mais ne sont utilisables que si l'hôte les fournit dans son `PATH`.

## Construction

La recette [`build.json`](build.json) (source `upstream-archives`) épingle chaque archive amont par URL et SHA-256.
`build-tools.yml` télécharge et vérifie chaque archive, l'extrait dans `<extractTo>/`, retire les fichiers inutiles
(`prune`, en-têtes, npm, tkinter…) et les symboles de débogage (`strip`), remplace les liens symboliques par des
copies (le cache du cœur les refuse), puis expose chaque binaire par un lanceur `sh` à la racine de l'archive.
Pour monter de version : mettre à jour URL, SHA-256 et `upstreamVersion`, incrémenter `toolVersion`
(Release immuable), puis lancer `build-tools` avec `tool=script-runners`.
