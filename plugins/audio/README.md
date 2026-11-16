# Plugin Audio (`plugin.audio`)

Plugin dédié à la manipulation, à l'encodage et à la normalisation de pistes sonores au sein de l'application `pack.media`.

## Blocs fournis

- **`block.audio.encode`** : Encodage et rééchantillonnage de flux audio (AAC, E-AC3, AC3, FLAC, MP3, Opus), débit sélectionnable (128 à 640 kbps) et normalisation intelligente EBU R128 (`loudnorm`).

## Dépendances

- `app.ffmpeg` (`>= 1.0.0`)
