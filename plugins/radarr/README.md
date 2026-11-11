# Plugin Radarr pour Flux de Fichiers

Ce plugin permet à Flux de Fichiers d'interagir directement avec une instance [Radarr](https://radarr.video/) via son API REST v3.

## Fonctionnalités
- **Valeurs par défaut configurables** : L'URL du serveur et la clé d'API sont saisies une seule fois dans le panneau *Plugins & Outils* et héritées automatiquement par tous les flux de films.
- **Rescan de film** : Déclenche la commande `RescanMovie` pour que Radarr analyse et prenne en compte les nouveaux formats de flux (ex: bascule de H.264 vers HEVC).
- **Renommage automatique** : Déclenche la commande `RenameFiles` pour renommer le média final selon la convention configurée dans Radarr.
- **Mappage de chemins** : Traduction automatique entre les points de montage locaux et ceux du conteneur Radarr.
