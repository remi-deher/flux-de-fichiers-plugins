# tool.ffmpeg

Fiche de **distribution** Option B pour FFmpeg (hors conteneur applicatif).

## Rôle actuel

- Médias synthétiques de tests / analyse (`ffprobe` / `ffmpeg` allowlist).
- **Pas** le remuxer production (MKVToolNix reste le choix remux).
- Conteneur MP4 production : toujours `examples/pending/ffmpeg-mp4.pending/`.

## Distribution

[`distribution.v1.json`](distribution.v1.json) — `x86_64` et `aarch64`,
SHA-256 obligatoires, `releaseStatus: contract-only`.
