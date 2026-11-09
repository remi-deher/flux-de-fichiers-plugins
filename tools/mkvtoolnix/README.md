# tool.mkvtoolnix

Remuxage Matroska via `mkvmerge` — choix applicatif actuel.

## Distribution (Option B)

Voir [`distribution.v1.json`](distribution.v1.json) : archives `x86_64` /
`aarch64`, chemin relatif `bin/mkvmerge`, SHA-256 obligatoire, permissions
`0755` sous `runtime-user`.

`releaseStatus: contract-only` — URL et empreintes illustratives, non
installables en production tant qu'une release ne les remplace pas.

## Sécurité

- Pas de shell ; argv paramétré (voir opérations du plugin remux).
- Allowlist exécutable : `mkvmerge` uniquement.
- Chemins opaques résolus par le runtime futur.

## Hors périmètre

Aucun binaire versionné dans ce dépôt. Pas de MP4.
