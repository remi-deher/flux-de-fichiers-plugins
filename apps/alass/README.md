# alass (synchronisation de sous-titres) (`alass`)

Resynchronisation automatique d'un sous-titre texte sur la piste audio.

Compilé depuis la crate [alass-cli](https://crates.io/crates/alass-cli) 2.0.0 (aucun binaire arm64 n'est publié en amont). alass appelle `ffmpeg` pour extraire l'audio : le plugin **Sous-titres** le place dans son `PATH` (`pathTools`). Compilation vérifiée avec Rust 1.99 ; `nom` 2.1 émet un avertissement de compatibilité future.

Construction : [`build.json`](build.json), publiée par `build-tools.yml` dans la Release immuable `tools-alass-1.0.0`.
