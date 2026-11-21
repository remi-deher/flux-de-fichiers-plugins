# Plugin Scripts (`scripts`)

Fournit le bloc unique `scripts.run` (« Script ») dans la palette de l'éditeur de flux :
- sélection d'un script enregistré dans `Librairies → Scripts` ;
- création rapide d'un nouveau script réutilisable ;
- exécution d'un code collé directement dans le bloc ;
- choix entre une sortie simple ou un routage conditionnel (`true` / `false`) piloté par `nextPort`.

## Protocole d'échange (schéma `1.1`)

Le script lit un objet JSON sur `stdin` et peut écrire un objet JSON sur `stdout`.

Entrée : `schemaVersion`, `flowId`, `nodeId`, `operationId`, `workingFile`, `sourceFile`, `workDir`, `mediaInfo`, `config` (réglages du bloc, modèles `{$…}` déjà rendus) et, depuis `1.1`, `variables` :

```json
{
  "file": { "name": "Film.mkv", "stem": "Film", "ext": "mkv", "dir": "/work", "size": 1234 },
  "source": { "name": "Films/Film.mkv" },
  "library": { "id": "…", "name": "Films" },
  "worker": { "name": "worker-1" },
  "job": { "id": "…" },
  "flow": { "id": "…" },
  "vars": { "codec": "hevc" }
}
```

Sortie (tous les champs sont facultatifs) : `status` (`ok`, `skip`, `error`), `message`, `nextPort`, `workingFile` (dans `workDir`), `mediaInfo` (fusionné dans la sonde), `stopPipeline` et, depuis `1.1`, `variables`.

`variables` en sortie est un objet plat nom → texte, nombre ou booléen, fusionné dans `vars.*` : noms en `[A-Za-z0-9_-]` (64 caractères au plus), 64 variables et 4 Kio par valeur au plus. Les variables intrinsèques (`file.*`, `job.*`…) ne peuvent pas être écrasées ; une entrée invalide fait échouer l'étape. Un script `1.0` ignore le champ `variables` d'entrée et reste compatible.

Les réglages texte des blocs acceptent les modèles `{$file.stem}`, `{$vars.codec|défaut}` (valeur par défaut après `|`) ; `{{$` produit le littéral `{$`. Le code d'un script inline n'est jamais réécrit.

## Routage

Le mode de sortie se règle dans l'inspecteur du bloc (`config.routing`) :

- **Simple** (`"single"`, valeur par défaut) : le bloc suit son unique liaison (sortie `destination`). Un `nextPort` libre reste accepté et suit la liaison de ce nom si elle existe.
- **Conditionnel** (`"conditional"`) : le bloc expose les sorties `true` (✓ Vrai) et `false` (✗ Faux), comme le bloc Condition. `nextPort` n'accepte que `"true"` ou `"false"` ; toute autre valeur fait échouer l'étape. Sans `nextPort`, `status: "ok"` (ou aucune réponse JSON) suit Vrai et `status: "skip"` suit Faux ; `status: "error"` fait échouer le flux.

Les sorties `true` / `false` sont déclarées dans `sockets.outputs` mais pas dans `ui.ports` : l'éditeur les affiche seulement en mode conditionnel, pour ne pas casser les liaisons simples existantes.

```json
{ "status": "ok", "nextPort": "false", "message": "codec déjà conforme" }
```
