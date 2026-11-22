# Routage : codec vidéo (`route-by-video-codec`)

Script d'exemple officiel des **variables de script** et des **variables exposées par un plugin** (ADR 0025).
Il oriente le flux selon le codec vidéo du fichier, sans réimplémenter la lecture des métadonnées :

- `codec` vaut par défaut `{$mediainfo.video.codec}`, une variable **exposée par MediaInfo** (plugin `video`).
  La valeur est résolue par Forgearr avant le script, qui la reçoit dans `config.codec`.
- `expected` est un choix (HEVC, AVC, AV1, VP9) saisi dans le formulaire du nœud.
- Sorties : **`true`** « Codec attendu » et **`false`** « Autre codec ». Les noms courants (H.265, H.264)
  sont ramenés à ceux de MediaInfo.

## Dépendance

`runtime.requires` déclare `mediainfo.video.codec` (fournisseur `video`, contrat 1). Sans le plugin
MediaInfo en amont dans le flux, l'étape échoue avant l'exécution en nommant la variable manquante ; la
dépendance est installée avec le script. Pour utiliser ce script sans MediaInfo, saisissez `codec` à la
main dans un script local déclaré avec `dependenciesUnverified`.

## Utilisation

Placez la sonde MediaInfo avant ce bloc, puis choisissez le codec attendu. L'aperçu du nœud montre la
`config` résolue avec les métadonnées d'exemple du simulateur (bouton « Dernier job réel »).
