# Serveurs de langage (`langages`)

Application qui fournit à l'éditeur de script de Forgearr ses suggestions et ses diagnostics (ADR 0032 de
l'application). Elle est **autonome** : elle ne dépend pas de `interpreteurs` et n'est jamais embarquée dans l'image
Docker principale. Le cœur lance ces outils sous confinement (ADR 0034), uniquement à l'ouverture d'un éditeur.

| Binaire | Rôle | Provenance | Version | Licence |
| --- | --- | --- | --- | --- |
| `ty` | Python : complétion, infobulle, diagnostics (`ty server`) | [astral-sh/ty](https://github.com/astral-sh/ty) | 0.0.111 | MIT |
| `shellcheck` | bash et sh : diagnostics (`--shell=sh` pour sh) | [koalaman/shellcheck](https://github.com/koalaman/shellcheck) | 0.11.0 | GPL-3.0 |
| `bash-language-server` | bash : complétion et infobulle (`start`) | [npm](https://www.npmjs.com/package/bash-language-server) | 5.8.1 | MIT |
| `node` | Exécute `bash-language-server` (non partagé avec `interpreteurs`) | [nodejs.org](https://nodejs.org/dist/) | 26.13.1 LTS | MIT |

Les sources de ShellCheck (GPL-3.0) sont publiées sur son dépôt, à la version indiquée ci-dessus.

## Construction

La recette [`build.json`](build.json) (source `upstream-archives`) épingle `ty`, `shellcheck` et Node.js par URL et
SHA-256. Le bloc `npmPackages` installe `bash-language-server` avec le Node.js embarqué par `npm ci`, à partir du
verrou figé [`npm/package-lock.json`](npm/package-lock.json) : empreintes d'intégrité vérifiées, aucun script
d'installation, aucune dépendance de développement, toutes les sources viennent du registre npm. Chaque binaire est
exposé par un lanceur `sh` à la racine de l'archive.

Pour monter de version : mettre à jour la recette (URL, SHA-256, `upstreamVersion`) ou le verrou
(`npm install --package-lock-only --ignore-scripts` dans `npm/`), incrémenter `toolVersion` (Release immuable), puis
lancer `build-tools` avec `tool=langages`. `ty` est jeune : une version plus récente peut changer le format de ses
réponses, la mise à jour passe par l'essai de l'ADR 0034.
