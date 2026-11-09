# Outil : MKVToolNix

Choix **actuel** de remuxage pour flux-de-fichiers (`mkvmerge`).

## Rôle

- Implémente l’interface applicative `Remuxer` (voir `docs/interfaces-outils.md`).
- Exécution prévue via l’image applicative Docker (binaire présent dans l’image
  runtime), pas via un paquet stocké dans ce dépôt.

## Hors périmètre de cette fiche

- Aucune installation locale du binaire ici.
- Aucune alternative (FFmpeg remux, autre conteneur) n’est validée : FFmpeg reste
  réservé aux médias synthétiques de test dans le dépôt applicatif.
