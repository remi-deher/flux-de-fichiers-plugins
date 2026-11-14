# Contrat macro-blocs / opérations composites

Un **macro-bloc** encapsule **plusieurs opérations versionnées** en une seule
étape de flow, lisible et testable unitairement. Il ne crée pas de shell
composite ni de script.

## Schéma

| Fichier | Rôle |
|---------|------|
| `schema/macro-block.v1.schema.json` | Contrat |
| `examples/catalogue/plugins/remux-mkv.example/blocks/macro-remux-verify.example/` | Exemple pédagogique |

## Modèle

1. Sockets d'entrée/sortie typés (comme un bloc).
2. `steps[]` ordonnées (≥ 2) : chaque étape référence
   `operationId` + `operationVersion` exacts.
3. `paramBindings` : `macro_input` | `step_output` | `literal` (refs opaques).
4. `errorPolicy: stop` — pas de compensation automatique.
5. `unitTestSurface.testableAsSingleUnit: true` — le macro est l'unité de test.
6. `runtimeNote` const — pas de moteur dans ce dépôt.

## Sécurité

- Pas de shell libre, pas d'interpolation, pas d'argv libre.
- Chaque étape hérite des garanties de l'opération (command-argv, permissions).
- Chemins via paramètres fichier / fileRef opaques uniquement.

## Différence bloc vs macro-bloc

| | Bloc | Macro-bloc |
|---|------|------------|
| Contenu | 1 opération | ≥ 2 opérations |
| Test | opération | surface composite déclarée |
| Flow | nœud simple | nœud qui masque un sous-graphe linéaire |
