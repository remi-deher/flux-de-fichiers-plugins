# Exemple de plugin MKV

La [fiche historique](manifest.json) reste au format 1.0.0 sans modification.
L'[index complémentaire](../../contracts.v1.json) lui associe
[une opération versionnée](operations/remux.json), puis
[un bloc](blocks/remux-mkv.example/block.json),
[un preset](../../presets/remux-defaut.example/preset.v1.json),
[un flow composé](../../flows/remux-rapide.example/flow.v1.json) et
[une app déclarative](../../packs/pilotage.example/installation.json).

Le plugin expose l'opération ; MKVToolNix fournit le binaire. L'argv reprend la
chaîne Rust actuelle : UTF-8, désactivation des tags statistiques, sortie réservée
puis source. Codes 0/1/2 distingués, sortie MKV, jamais MP4. L'entrée et la sortie
sont des références fichiers autorisées, sans chemin hôte échangé.

[Les messages d'invocation](../../../invocation/) sont inventés. Le futur
chargeur/runtime devra satisfaire les
[garanties d'exécution](../../../../docs/garanties-execution-v1.md), notamment capture,
masquage, bornes, vérification et arrêt. La CLI est compatible avec l'outil choisi ;
aucune exécution de ces définitions ni validation fonctionnelle n'est revendiquée.
