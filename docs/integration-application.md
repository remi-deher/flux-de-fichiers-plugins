# Intégration à l’application

## Principes

1. Le dépôt applicatif reste le runtime (Rust, Docker, Compose, migrations).
2. Ce dépôt fournit le **catalogue** et les **contrats** ; le chargeur reste à concevoir plus tard.
3. #10 (socle / frontend différé) ne doit pas être bloqué : aucune modification des
   fichiers applicatifs n’a été faite depuis #11.
4. Secrets : toujours par fichiers / orchestrateur ; jamais dans ce dépôt.

## Changements applicatifs futurs (à planifier, non faits ici)

| Zone | Adaptation |
|------|------------|
| Worker remux | Extraire un trait / module `Remuxer` autour de l’appel `mkvmerge` |
| Config | Référence optionnelle vers un `toolId` catalogue (défaut `tool.mkvtoolnix`) |
| Compose / image | Continuer d’embarquer MKVToolNix dans l’image runtime tant qu’il est le choix actuel |
| SQLx / DB | Inchangé ; PostgreSQL reste requis |
| Frontend Leptos (futur) | Lire `catalogue/index.json` + fiches pour présentation (icône, licence, description) |

## Chemin de lecture envisagé

```text
FLUX_PLUGINS_ROOT/
  catalogue/index.json
  tools|plugins|flows|…/<id>/manifest.json
```

`FLUX_PLUGINS_ROOT` pourra être un clone, un volume monté ou un artefact publié
(#12). Format exact de distribution : décision ouverte.

## Non-régression

- `compose.yaml` et `deploy/` du dépôt applicatif restent la vérité runtime.
- Les exemples sous `tools/postgresql/deploy/*.example` ne remplacent rien tant
  qu’une bascule n’est pas explicitement demandée.
