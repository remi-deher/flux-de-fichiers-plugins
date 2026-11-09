# Frontières du catalogue

| Élément | Responsabilité | Ce qu'il référence |
| --- | --- | --- |
| **tool** (outil) | Binaire ou service ; Option B = distribution autonome hors image app (`distribution.v1.json`) | `tool.mkvtoolnix`, `tool.ffmpeg`, `tool.internal.telemetry`, `tool.postgresql` |
| **plugin** | Fournisseur d'opérations versionnées ; un adaptateur décrit comment utiliser un outil | Fiche existante et définitions d'opérations |
| **operation** | Action atomique avec paramètres, entrées/sorties, permissions demandées, argv et politique console | Une version de plugin et un outil installé |
| **block** (bloc) | Façade low-code de type Scratch ; nom, sockets et liaisons d'une opération | Une version exacte d'opération |
| **macro-block** | Encapsulation de ≥ 2 opérations en une étape de flow testable unitairement | Opérations versionnées + bindings |
| **flow** | Graphe acyclique de blocs connectés ; pas une installation | Blocs et presets épinglés |
| **preset** | Valeurs par défaut typées ; aucun programme, script ou droit supplémentaire | Une version exacte d'opération |
| **app** | Paquet installable et activable, avec dépendances, lanceur de flow, permissions et cycle de vie | Un ensemble cohérent de composants exacts |
| **resource** | Contenu passif : police, image, son, couleur, langue ou modèle, avec fiche/licence | Actifs et métadonnées ; aucune exécution implicite |

Une app est l'unité d'installation et de désinstallation. Un flow est l'unité
 de composition ; le même flow peut être référencé par plusieurs apps. Installer
une app ne signifie ni lancer son flow, ni installer un service Docker, ni
remplacer PostgreSQL ou MKVToolNix. Le premier contrat d'app porte un paquet
**déclaratif** présenté par le frontend Leptos, sans nouveau code d'interface.

Le catalogue ne peut transformer un `resource.template` en script. Un type
inconnu, une capacité non supportée ou un contrat de version inconnue est refusé
sans exécution. Les anciens lecteurs restent sur leur index historique ; les
nouveaux consommateurs utilisent aussi [contracts.v1.json](../catalogue/contracts.v1.json).

Les fichiers de ce dépôt ne constituent pas une autorisation de confiance.
L'exécution, la vérification des médias et la gestion des secrets appartiennent
au socle applicatif ; l'isolation des futurs plugins exécutables reste à arbitrer.
