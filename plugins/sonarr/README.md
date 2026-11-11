# Plugin Sonarr pour Flux de Fichiers

Ce plugin permet à Flux de Fichiers d'interagir directement avec une instance [Sonarr](https://sonarr.tv/) via son API REST v3.

## Fonctionnalités
- **Valeurs par défaut configurables** : L'URL du serveur et la clé d'API sont saisies une seule fois dans le panneau *Plugins & Outils* et héritées automatiquement par tous les flux.
- **Rescan de série** : Déclenche la commande `RescanSeries` pour que Sonarr détecte immédiatement le nouveau fichier transcodé ou remuxé.
- **Renommage automatique** : Déclenche la commande `RenameFiles` pour renommer le média final selon les conventions configurées dans Sonarr.
- **Mappage de chemins** : Traduction automatique entre les points de montage locaux et ceux du conteneur Sonarr.
