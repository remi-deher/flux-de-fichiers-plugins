# ab-av1 (`ab-av1`)

Encodage à qualité cible : cherche le CRF qui atteint un score VMAF minimal, puis encode.

Compilé depuis la crate [ab-av1](https://crates.io/crates/ab-av1) 0.11.7 (aucun binaire arm64 n'est publié en amont). ab-av1 appelle `ffmpeg` et `ffprobe` : le plugin **Qualité VMAF** place `ffmpeg-vmaf` dans son `PATH`.

Construction : [`build.json`](build.json), publiée par `build-tools.yml` dans la Release immuable `tools-ab-av1-1.0.0`.
