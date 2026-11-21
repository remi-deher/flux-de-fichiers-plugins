# Plugin Noyau & Contrôle de Flux

Ce plugin fournit les blocs structurels et réseau de base du catalogue :

- `essentiel.file-input` : point d'entrée d'un flux (`file-input`).
- `essentiel.condition` : aiguillage conditionnel vers les sorties `true` et `false` (`condition`).
- `essentiel.webhook` : notification HTTP avec en-têtes chiffrés (`webhook`).
- `essentiel.file-output` : bloc terminal marquant le fichier résultat (`file-output`).
- `essentiel.worker-capability` : aiguillage `capable` / `incapable` selon les encodeurs matériels du worker qui exécute (`worker-capability`).
- `essentiel.relay` : confie la tâche à la file d'un autre worker, capable ou précis, avant tout traitement ; la sortie « Reprise » continue sur le worker cible (`relay`).
