# Frontières du catalogue

| Élément | Responsabilité | Dépend de |
| --- | --- | --- |
| **application** (`app`) | Programme exécutable : MKVToolNix, FFmpeg… Distribution autonome hors image (`distribution.v1.json`) | Rien |
| **plugin** | Fournit des opérations et des blocs ; un adaptateur décrit comment utiliser une application | Applications, **proposées** (`optional`), jamais imposées : un plugin Sonarr n'en a pas |
| **bloc** | Façade low-code d'une opération. Appartient à un plugin (`owner`), jamais exposé seul | Son plugin |
| **flow** | Graphe acyclique de blocs | Plugins et/ou éléments « Autre » |
| **autre** | Préréglage, police, image, musique, couleur, langue ou modèle ; peut vivre seul, appelable par un flow | Rien |
| **pack** | Ensemble d'une ou plusieurs pièces des types précédents (hors blocs) | Applications, plugins, flows, « Autre » |
| **dépôt** | Source distante qui porte le catalogue ; n'est pas une pièce | |

Un pack est l'unité d'installation et de désinstallation. Un flow est l'unité
 de composition ; le même flow peut être référencé par plusieurs packs. Installer
un pack ne signifie ni lancer son flow, ni installer un service Docker, ni
remplacer PostgreSQL ou MKVToolNix. Le premier contrat de pack porte un paquet
**déclaratif** présenté par le frontend Leptos, sans nouveau code d'interface.

Le catalogue ne peut transformer un `resource.template` en script. Un type
inconnu, une capacité non supportée ou un contrat de version inconnue est refusé
sans exécution. L'index unique est `catalogue/index.json` ; les
exemples de contrats : [contracts.v1.json](../examples/catalogue/contracts.v1.json).

Les fichiers de ce dépôt ne constituent pas une autorisation de confiance.
L'exécution, la vérification des médias et la gestion des secrets appartiennent
au socle applicatif ; l'isolation des futurs plugins exécutables reste à arbitrer.
