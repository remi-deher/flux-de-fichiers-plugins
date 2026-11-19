# HDR et Dolby Vision (`hdr`)

Conserve et rend lisibles les métadonnées dynamiques des fichiers Matroska HEVC.

| Bloc | Rôle |
| --- | --- |
| `hdr.dv-profile-8` | Convertit un Dolby Vision **profil 7** (double couche, disques UHD) en **profil 8.1**, lu par Plex, Jellyfin, Shield, téléviseurs. Sans objet pour les autres profils. |
| `hdr.dv-reinject` | Après un réencodage HEVC, réinjecte le RPU Dolby Vision de l'original (converti en 8.1). Le nombre d'images doit être identique. |
| `hdr.hdr10plus-reinject` | Après un réencodage HEVC, réinjecte les métadonnées HDR10+ de l'original. |

Les deux blocs de réinjection lisent l'**original de la tâche** (`sourceFile`) : placez-les après le bloc d'encodage. Ils passent leur tour si l'original n'a pas ces métadonnées ou si la vidéo encodée n'est pas en HEVC.

Outils : `mkvtoolnix`, `dovi-tool`, `hdr10plus-tool`, exécutés par le script [`scripts/hdr.py`](scripts/hdr.py) (Python des `interpreteurs`).
