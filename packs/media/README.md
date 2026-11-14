# Pack Studio Multimédia (`pack.media`)

Pack fédérateur de traitement multimédia pour Flux de Fichiers, inspirée de l'architecture par nœuds de flux (FileFlows).

## Plugins intégrés

- **`plugin.video`** : Traitement d'image, encodage accéléré par matériel (Intel QSV, NVENC, VAAPI, CPU) et remuxage Matroska sans perte.
- **`plugin.audio`** : Traitement et extraction de pistes sonores, conversion vers AAC / AC3 / E-AC3 / FLAC / MP3 et normalisation audio.

## Applications distribuées (Option B)

- **`app.mkvtoolnix`** (`mkvmerge`) : Opérations de remuxage strict sans réencodage.
- **`app.ffmpeg`** (`ffmpeg`, `ffprobe`) : Moteur de transcodage et filtres vidéo/audio.

Les blocs (par exemple `block.video.remux-mkv`) appartiennent à leurs plugins et ne sont pas listés dans le pack.
