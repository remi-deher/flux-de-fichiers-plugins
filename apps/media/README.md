# Application Studio Multimédia (`app.media`)

Application fédératrice de traitement multimédia pour Flux de Fichiers, inspirée de l'architecture par nœuds de flux (FileFlows).

## Plugins intégrés

- **`plugin.video`** : Traitement d'image, encodage accéléré par matériel (Intel QSV, NVENC, VAAPI, CPU) et remuxage Matroska sans perte.
- **`plugin.audio`** : Traitement et extraction de pistes sonores, conversion vers AAC / AC3 / E-AC3 / FLAC / MP3 et normalisation audio.

## Outils système distribués (Option B)

- **`tool.mkvtoolnix`** (`mkvmerge`) : Opérations de remuxage strict sans réencodage.
- **`tool.ffmpeg`** (`ffmpeg`, `ffprobe`) : Moteur de transcodage et filtres vidéo/audio.
