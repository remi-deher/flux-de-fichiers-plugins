# Garde-fou : gain de taille minimal (`guard-min-size-saving`)

Script catalogue réutilisable (protocole `stdin`/`stdout` JSON) qui compare la taille du fichier courant (`workingFile`) à celle du fichier d'origine (`sourceFile`).

- **`true` (« Gain suffisant »)** : la réduction atteint au moins `min_saving_percent` %.
- **`false` (« Gain insuffisant »)** : le fichier encodé n'économise pas assez d'espace (ou est plus lourd que la source). Si `restore_source_on_reject` est activé, le script remet `workingFile` sur `sourceFile` pour éviter d'écraser l'original avec un résultat moins bon.
