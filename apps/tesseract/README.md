# Tesseract OCR (`tesseract`)

Reconnaissance de caractères, pour convertir les sous-titres image (PGS) en texte.

Paquet Debian bookworm `tesseract-ocr` 5.3 avec les langues anglais, français, allemand, espagnol, italien, portugais et néerlandais. Les données `tessdata` sont embarquées et un lanceur pose `TESSDATA_PREFIX`. Utilisé par le plugin **Sous-titres** pour l'OCR des pistes PGS.

Construction : [`build.json`](build.json), publiée par `build-tools.yml` dans la Release immuable `tools-tesseract-1.0.0`.
