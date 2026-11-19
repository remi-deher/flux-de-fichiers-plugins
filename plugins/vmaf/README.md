# Qualité VMAF (`vmaf`)

| Bloc | Rôle |
| --- | --- |
| `vmaf.measure` | Compare le fichier courant à l'**original de la tâche** avec libvmaf (modèle 1080p, ou 4K au-delà de 1440 lignes ; mise à l'échelle automatique) et oriente vers **Conforme** ou **Insuffisant** selon le seuil. Le score est ajouté aux métadonnées (`vmaf.mean`, `vmaf.min`, `vmaf.harmonicMean`). |
| `vmaf.target-encode` | Encode avec [ab-av1](https://github.com/alexheretic/ab-av1) : recherche par échantillons du CRF le plus économe qui atteint le score VMAF demandé, puis encodage complet vérifié (`--verify`). Audio et sous-titres copiés. AV1 (SVT-AV1), HEVC (x265) ou H.264 (x264). |

Outils : `ffmpeg-vmaf` (FFmpeg statique avec libvmaf et SVT-AV1) et `ab-av1`. La mesure passe par le script [`scripts/vmaf.py`](scripts/vmaf.py).
