# Plugin Vidéo (`plugin.video`)

Plugin dédié à la manipulation, à l'encodage et au remuxage de flux vidéo au sein de l'application `app.media`.

## Blocs fournis

- **`block.video.encode`** : Encodage vidéo avec sélecteur de codec (H.264, HEVC, AV1), encodeur matériel (Intel QSV, NVIDIA, VAAPI, CPU), curseurs de Qualité (1-9) et Vitesse (1-5).
- **`block.video.remux-mkv`** : Remuxage sans perte vers le format Matroska (`.mkv`) à l'aide de MKVToolNix.

## Dépendances

- `tool.ffmpeg` (`>= 1.0.0`)
- `tool.mkvtoolnix` (`>= 1.0.0`)
