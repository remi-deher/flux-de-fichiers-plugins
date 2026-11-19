# Contrôle d'intégrité média (`integrity-check-media`)

Vérifie rapidement un fichier vidéo avant son remplacement ou sa publication :
1. existence et taille strictement positive ;
2. lecture du conteneur via `ffprobe` (ou `mkvmerge -J` en repli) ;
3. durée strictement positive ;
4. présence des pistes exigées (`require_video`, `require_audio`).

Route vers `true` (« Valide ») ou `false` (« Corrompu »).
