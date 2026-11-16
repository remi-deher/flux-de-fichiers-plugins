# Packs installables v1

Un pack est un ensemble de pièces du catalogue (applications, plugins, flows, éléments « Autre »),
sans bloc : un bloc appartient à son plugin. C'est un paquet avec un cycle d'installation, distinct de ses flows et
plugins. Le contrat initial décrit un **bundle déclaratif** présenté et lancé
par le futur frontend Leptos ; aucun nouvel exécutable ni service n'est embarqué.

[Le manifeste](../examples/catalogue/packs/pilotage.example/manifest.json) utilise la version 1.1.0.
Son champ `pack.installation` référence
[installation.json](../examples/catalogue/packs/pilotage.example/installation.json), validé par
[pack-installation.v1](../schema/pack-installation.v1.schema.json).
Il déclare l'identité/version du pack (`packId`, `packVersion`), les versions exactes de ses composants,
son flow de démarrage et les permissions nécessaires. Le point d'entrée doit
être l'un des composants, avec une version identique. Le résolveur vérifie la
fermeture des dépendances, l'absence de conflit et la compatibilité de tous les
contrats avant activation. Le pack ne devient pas un fournisseur de commandes.

## Cycle exigé du futur installeur

1. **Découverte** : lire les fiches et contrats sans déclencher d'action.
2. **Résolution** : épingler les composants et vérifier type/version/intégrité
   depuis une source approuvée. La distribution et sa signature restent à décider.
3. **Autorisation** : présenter les droits et dépendances à l'administrateur ;
   refuser ce qui dépasse sa politique. Le manifeste ne s'autorise pas lui-même.
4. **Préparation** : réserver un espace et un identifiant d'installation,
   sans modifier un pack actif ni exécuter son flow.
5. **Activation** : enregistrer atomiquement l'ensemble résolu ; état `installed`
   puis `enabled` après vérification du point d'entrée. Une erreur laisse
   `failed` et conserve l'installation active précédente, sans activation partielle.
6. **Mise à jour manuelle** : nouvelle résolution et nouvelle autorisation si
   les droits changent ; retour à la version active précédente si activation
   impossible. Pas de scripts de migration implicites.
7. **Désinstallation** : désactiver, gérer explicitement les appels en cours,
   supprimer l'enregistrement et les fichiers privés du paquet. Conserver
   sources, résultats, secrets externes et composants partagés. Les captures
   suivent leur TTL, pas une suppression de médias.

Les états d'installation `discovered`, `prepared`, `installed`, `enabled`,
`disabled`, `failed`, `removed` sont distincts des états d'invocation d'un flow.
Un redémarrage ne doit ni activer une préparation incomplète ni relancer un
traitement. Un pack désactivé refuse de nouveaux appels. Les quotas et droits
restent contrôlés à chaque invocation, même après installation.

`updates: manual`, `uninstallData: preserve` et `runtimeImplemented: false`
explicitent le périmètre. L'exemple référence le plugin MKV, son flow et l'application
MKVToolNix ; ses blocs voyagent avec le plugin. Il ne représente ni un paquet publié,
ni un écran livré, ni un remplacement de l'application existante. La recette est
complète comme contrat ; aucun installeur n'est fourni et aucune installation
n'a été effectuée. Les artefacts Leptos/WASM et plugins exécutables futurs auront
besoin d'un contrat de distribution et d'isolation supplémentaire.
