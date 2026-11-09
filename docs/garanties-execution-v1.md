# Garanties d'exécution des extensions v1

Contrat déclaratif proposé pour le ticket #39, daté du 9 novembre 2026.
Ce texte décrit les obligations du **futur** runtime Rust/Axum/Tokio ; il ne
prouve pas leur implémentation dans l'application actuelle. Les documents JSON
sont des définitions et des échanges fictifs, jamais des traces de production.

Les garanties P0/P1 de ce texte sont portées de façon normative par les schémas
`schema/*.v1.1.schema.json` (migration : `docs/migration-schemas-v1.1.md`,
diff : `docs/diff-revue-securite-40.md`). Les schémas `*.v1.schema.json` ne
sont pas modifiés silencieusement.

## Autorité et capacités

Une capacité fonctionnelle (`remux`, par exemple) décrit ce qu'une opération
fait. Une permission décrit ce qu'elle peut toucher : fichiers d'entrée en
lecture seule, fichiers de sortie réservés, binaire autorisé, réseau éventuel.
Une déclaration du catalogue ne donne aucun droit. L'autorité effective est
l'intersection des besoins déclarés, des droits de l'appelant et de la politique
locale du nœud d'exécution. Toute permission inconnue ou refusée bloque l'appel
avant création d'un processus ; aucune élévation implicite n'est permise.

Le coordinateur authentifie et autorise l'appel. Un worker distant reçoit les
données autorisées par HTTPS ; il n'accède pas directement à PostgreSQL.
Le contrat s'applique aussi à l'exécuteur intégré au coordinateur. Il n'impose
ni HA, ni nouveau service, ni langage de plugin. Un futur plugin natif, WASM ou
RPC nécessitera son propre adaptateur explicitement accepté.

## Fichiers et commandes

Un fichier échangé est une **référence typée opaque**, jamais un chemin hôte,
une URL à télécharger librement ou une chaîne substituée par le client.
Le runtime vérifie son propriétaire, son autorisation, son empreinte si fournie,
son type réel et sa disponibilité avant exécution. L'indication de type média
du catalogue ne suffit pas à rendre un fichier fiable.

Une sortie est réservée dans un espace propre à la tentative ; elle ne peut
écraser ni la source ni un résultat publié. Les chemins absolus locaux sont
résolus par le runtime sous ses volumes autorisés. Traversées `..`, liens
symboliques sortants, chemins réseau et changements de fichier entre contrôle
et ouverture sont refusés. Le contrat ne donne aucun accès arbitraire au disque.

L'exécutable est choisi dans les binaires autorisés de l'outil installé,
indépendamment des paramètres. Chaque référence de paramètre produit un argument
atomique. Pas de découpage sur les espaces, concaténation de commande, expansion
de variable, glob, substitution, shell ou interpréteur à code libre. Les tableaux
sont développés élément par élément, jamais joints puis analysés à nouveau.
Les nombres utilisent une représentation décimale indépendante de la locale.

L'absence de shell n'empêche pas l'injection d'options propres au programme.
Les valeurs d'options libres sont donc interdites : un choix vient d'une liste
fermée déclarée. Les chemins générés par le runtime ne commencent pas par `-`
ou `@`. Pour `mkvmerge`, ne pas ajouter `--` : il serait lu comme un fichier.
Les mécanismes de fichiers de réponse, scripts, plugins chargés par l'outil et
téléchargements doivent aussi être exclus de l'adaptateur initial.

L'environnement est explicitement construit ; aucun héritage global des secrets
ou des variables modifiant le chargement de code (`LD_PRELOAD`, etc.). Un secret
est une référence au coffre ou à un fichier monté en lecture seule par
l'orchestrateur. Sa valeur ne figure ni dans les paramètres littéraux, ni dans
argv, ni dans les manifests, exemples, erreurs ou métadonnées.

## Console brute, masquage et affichage

« Brut » signifie stdout et stderr distincts, avec leurs octets et leur ordre
respectif, **après masquage obligatoire et dans les limites annoncées**. Aucun
ordre total entre les deux pipes n'est garanti. On ne reconstruit pas une console
à partir des seuls messages de progression, ni à partir d'une sortie reformatée.
L'encodage de transport peut être base64 pour préserver les octets non UTF-8.
Les retours chariot, lignes vides et séquences non textuelles ne sont pas perdus.

Le masquage précède toute persistance, fichier temporaire, événement, transmission,
analyse de progression et affichage. Il couvre les secrets connus de l'appel,
leurs variantes explicitement prévues par la politique et les valeurs déclarées
sensibles. Le filtre conserve en mémoire une frontière suffisante entre lectures
pour masquer un secret coupé entre deux chunks ou deux écritures du processus.
Cette mémoire est bornée et n'est jamais sérialisée. En cas de filtre indisponible,
de secret impossible à traiter ou d'échec de capture : arrêt et `capture_failed`,
sans repli vers un journal non masqué.

Le remplacement par `***` modifie les octets : une capture masquée n'est pas
présentée comme une preuve binaire exacte de la sortie originale. Aucune copie
non masquée n'est gardée « pour diagnostic ». Le masquage ne peut reconnaître
toute transformation arbitraire d'un secret par un outil : seuls les outils de
confiance approuvés peuvent recevoir un secret ; un plugin non fiable ne reçoit
aucun secret dans le périmètre initial.

La console et les messages d'erreur sont des données non fiables. Le frontend
Leptos les affiche comme texte, échappe HTML et neutralise les commandes de
terminal, liens actifs automatiques et séquences ANSI/OSC dangereuses. Les
messages publics restent génériques ; le diagnostic autorisé est lié à un
identifiant de corrélation, sans exposer chemin interne ou secret.

## Limites et rétention

Chaque appel possède une politique **effective et finie** avant démarrage :
durée maximale, délai de grâce d'arrêt, octets retenus par pipe, quota total de
capture, taille d'événement, nombre d'événements et durée de rétention. Les valeurs
d'exemple sont illustratives et ne valent pas politique de production.
Un appel peut demander moins, jamais dépasser la politique locale ou retirer
le masquage. Aucun défaut JSON Schema n'est considéré comme déjà appliqué.

Atteindre la limite d'octets retenus conserve un préfixe masqué et marque le pipe
comme tronqué. Le runtime continue de drainer **les deux** pipes sans accumulation
non bornée afin d'éviter un blocage du processus. Il compte les octets observés
et retenus séparément. Les fichiers de débordement ne contournent pas les quotas.
Un défaut d'écriture de capture produit `capture_failed`, pas une réussite muette.
Une progression optionnelle peut être coalescée lorsqu'un quota est atteint ;
le résultat terminal et l'indication de perte d'événements restent récupérables.

Les captures, leurs copies et leurs index suivent la même expiration, y compris
après annulation, échec ou redémarrage. Aucun mode de conservation illimitée
n'est implicite. Une référence expirée retourne `capture_expired`, distinct d'un
pipe vide. La purge des captures ne supprime jamais les médias source ou publiés.
La politique des sauvegardes et le chiffrement des données sensibles restent
à décider avant tout stockage de captures de production.

## États, erreurs et publication

Un appel porte un identifiant de corrélation, une version exacte d'opération et
un identifiant de tentative. Ses états non terminaux sont `queued`, `running`
et `cancelling`. Le coordinateur enregistre un seul résultat terminal faisant
autorité ; les événements tardifs d'un ancien bail ne le remplacent pas.

| Situation | Résultat attendu | Code du processus |
| --- | --- | --- |
| Entrée invalide, permission refusée, version/capacité indisponible | `rejected`, avant lancement | `null` |
| Binaire absent ou échec de création du processus | `failed`, `spawn_failed` | `null` |
| Code admis et sorties vérifiées | `succeeded` | Code réellement observé |
| Code non admis | `failed`, `tool_failed` | Code réellement observé |
| Sortie absente, invalide ou empreinte incorrecte | `failed`, `output_invalid` | Code observé, même égal à zéro |
| Délai dépassé | `timed_out` | Code observé ou `null` |
| Annulation acceptée | `cancelled` | Code observé ou `null` |
| Signal sans code normal | `failed`, `process_signalled` | `null`, signal séparé |
| Capture impossible ou filtre de secrets défaillant | `failed`, `capture_failed` | Code observé ou `null` |
| Worker perdu, état du processus indéterminé | `failed`, `worker_lost` | `null` si inconnu |

`exitCode: null` ne signifie donc pas seulement « jamais démarré ». Un code 0 ne
suffit pas à publier un résultat. Pour MKVToolNix, 0 est un succès, 1 un succès
avec avertissements conservés, 2 une erreur. L'exemple n'autorise ni transcodage
ni MP4. Le remux doit être revalidé avant publication comme dans la chaîne actuelle.

L'arrêt demande d'abord une annulation coopérative, puis termine le groupe de
processus après le délai de grâce. Le runtime draine les pipes, attend la fin
et ferme les ressources. Annulation, expiration et publication concurrentes
sont arbitrées par la transition terminale atomique ; aucune réussite n'est
annoncée sur une sortie encore partielle.

Pas de reprise automatique d'une opération générique après perte de worker :
son effet peut avoir eu lieu. Les tentatives distinctes, la déduplication des
requêtes et l'idempotence métier ne sont pas équivalentes. La politique de
reprise doit être déclarée et autorisée ; aucune garantie « exactement une fois »
n'est fournie. Les sorties partielles restent non publiées ; leur nettoyage
relève d'une politique explicite distincte de la rétention console.

## Validation sémantique en complément des schémas

JSON Schema vérifie la forme d'un document, pas l'existence des dépendances,
les droits ni la correction d'un graphe. Avant toute exécution, le futur runtime
doit aussi vérifier :

- unicité des identifiants et résolution de chaque version exacte ;
- correspondance fournisseur, manifeste, opération et bloc ;
- paramètres requis, types, bornes et absence de paramètres inconnus ;
- liaisons des sockets vers les entrées/sorties déclarées ;
- compatibilité de type et de média de chaque connexion, sans conversion cachée ;
- une seule origine par entrée, absence de cycle et présence de toutes les entrées ;
- droits sur les références fichiers et politique effective de capture/arrêt ;
- résultat vérifié avant exposition au bloc suivant ou publication finale.

Un preset fournit des valeurs par défaut typées ; il n'accorde aucune permission
et n'ajoute jamais des options de commande libres. Le flow initial s'arrête sur
l'échec d'un bloc et ne démarre aucun bloc dépendant. Boucles, expressions libres,
branches conditionnelles et compensation distribuée restent hors du contrat
initial tant qu'une sémantique distincte n'est pas définie.
