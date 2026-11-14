# Intégration future au socle

Le dépôt applicatif conserve le binaire Rust unique (coordinateur Axum/Tokio,
worker distant ou exécuteur intégré), SQLx/PostgreSQL, Docker, TLS, API autorisée
et frontend Leptos. Aucun fichier applicatif n'est modifié par ces contrats.
Le coordinateur reste seul à accéder à PostgreSQL ; les workers passent par HTTPS.
Aucun changement de HA ou de stratégie de bascule n'est impliqué.

Le futur lecteur charge [l'index historique](../catalogue/index.json), puis
[l'index complémentaire](../examples/catalogue/contracts.v1.json). Il sélectionne le bon
schéma par famille et `schemaVersion`, avec registre local de `$ref`, puis valide
les références et règles sémantiques. Le choix de distribution et de confiance
est [ouvert](questions-ouvertes.md). Aucun `FLUX_PLUGINS_ROOT` opérationnel n'est
ajouté au code actuel.

| Zone du socle | Obligation future |
| --- | --- |
| Catalogue | Vérifier schémas, versions, dépendances, chemins et confiance |
| Autorisation | Intersection des droits de l'appelant et du nœud ; aucune permission autoaccordée |
| Stockage | Résoudre les fileRef, réserver les sorties, vérifier avant publication |
| Worker/local | Adaptateur argv fixe, captures concurrentes bornées, masquage et arrêt supervisé |
| Coordinateur | Corrélation, états/baux, résultat durable et idempotence du transport |
| Frontend Leptos | Fiches, blocs et app déclarative ; console affichée comme texte non fiable |

La commande du [plugin MKV](../examples/catalogue/plugins/remux-mkv.example/operations/remux.json)
reprend les options de `src/media.rs`. Ce module ignore encore la console de
remux ; les nouveaux contrats ne sont donc pas un adaptateur déjà implémenté.
La vérification actuelle des médias reste la référence de publication.

Les fichiers Compose, images, migrations et déploiements du dépôt applicatif
restent la source de vérité. Les modèles sous `apps/postgresql/deploy/` ne
remplacent aucune configuration. Installation, exécution générique et scénarios
de validation du futur runtime restent à réaliser après les arbitrages.
