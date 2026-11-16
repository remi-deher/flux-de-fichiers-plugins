# Note de décision — contrats d'extensions v1 (#39)

Date : 9 novembre 2026. Statut : **proposition de contrat documentaire** pour
relecture avant implémentation. Les choix techniques permanents restent ceux
validés par l'utilisateur ; les recommandations ci-dessous ne les remplacent pas.

## Choix retenus dans ce livrable

- Fiches et index historiques conservés à l'identique ; découverte des nouveaux
  contrats dans un index complémentaire et extension de manifeste identifiée 1.1.0.
- Opération fournie par un plugin, outil installé distinct, bloc de présentation,
  flow DAG, preset typé et pack déclaratif avec cycle d'installation distinct.
- Versions de contenu exactes, références fichiers opaques, aucun shell libre,
  sortie MKV et options `mkvmerge` alignées sur le code actuel.
- Capture stdout/stderr distincte en octets, après masquage obligatoire,
  limites effectives finies, TTL, erreurs explicites et aucune reprise automatique.
- Définition des messages sans imposer d'endpoint, de bus, de crate ou de nouveau
  service. Le runtime actuel ne consomme aucun de ces contrats.

Ces règles bornent une future implémentation. Elles ne valent ni approbation de
production, ni preuve de sécurité ou de fonctionnement du runtime inexistant.

## Arbitrages à prendre avant implémentation ou activation

| Sujet | Proposition | Décision encore nécessaire / effet |
| --- | --- | --- |
| Distribution et confiance | Artefact immuable, empreinte et source approuvée, registre local de schémas | Choisir entre clone épinglé, archive signée et volume ; autorités de signature et révocation. Sans source approuvée, pas d'installation |
| Isolation des plugins exécutables | Adaptateur CLI vers les seuls outils déjà approuvés, réseau interdit dans v1 | Décider si et comment accueillir du code tiers (processus, conteneur, WASM ou RPC), sans déduire sa confiance d'une fiche |
| Chiffrement et captures | Métadonnées dans PostgreSQL ; captures masquées dans un stockage autorisé et borné | Choisir chiffrement, clés hors DB, sauvegardes et effacement ; aucune donnée sensible en clair avant cette décision |
| Quotas et rétention | L'exemple propose 1 Mio par pipe, 2 Mio retenus, 1 Gio lus par pipe, 64 Kio de mémoire, 1 000 événements, TTL 24 h | Valider des limites globales/par utilisateur/nœud et la capacité disque. Ces nombres sont illustratifs, pas des valeurs mesurées de production |
| Streaming et progression | Résultat terminal récupérable ; événements d'étapes facultatifs | Choisir transport, reprise et pagination. Un parseur `mkvmerge` devra être versionné ; aucun pourcentage métier n'est simulé comme réel |
| Arrêt et baux | Délai fini, SIGTERM puis arrêt forcé, résultat terminal atomique | Choisir supervision de groupe/conteneur, fenêtres de grâce et récupération après perte de worker ; ne pas promettre « exactement une fois » |
| Installation et dépendances | Bundle déclaratif à versions exactes, activation atomique et mise à jour manuelle | Fixer stockage de l'état, intégration Leptos, source des composants et gestion des appels en cours ; aucune installation ou migration automatique ici |
| Alternatives de formats | Conserver MKVToolNix pour MKV, FFmpeg uniquement pour les médias synthétiques de tests | MP4 et outil de production éventuel nécessitent une décision utilisateur explicite. Aucun contrat FFmpeg de production ni outil alternatif n'est publié |

## Périmètre des preuves

Livrable : schémas, définitions liées, exemples fictifs et exigences de validation
sémantique. Aucun code Rust/Leptos, changement Docker, migration SQL, appel de
processus média, build ou essai fonctionnel local. Pas de déploiement, commit,
push, release ou autre ticket créé par ce travail.

La [relecture documentaire](limites-et-revue.md) distingue les contrôles statiques
réalisés des scénarios nécessaires à la future implémentation. Les arbitrages
restent sur le ticket #39 et dans cette note ; ils n'empêchent pas la livraison
du contrat documentaire demandé.
