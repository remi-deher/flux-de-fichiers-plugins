# FFmpeg (VMAF) (`ffmpeg-vmaf`)

FFmpeg statique avec libvmaf et SVT-AV1, pour mesurer la qualité perçue et encoder à qualité cible.

Build statique GPL de [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) (FFmpeg 8.1.3), compilé avec libvmaf et SVT-AV1, absents du FFmpeg de Debian. Distinct de l'application `ffmpeg` : il ne sert qu'au plugin **Qualité VMAF**. Les autobuilds BtbN sont purgés après quelques semaines ; une nouvelle version demande de mettre à jour URL et SHA-256.

Construction : [`build.json`](build.json), publiée par `build-tools.yml` dans la Release immuable `tools-ffmpeg-vmaf-1.0.0`.
