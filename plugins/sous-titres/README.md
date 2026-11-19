# Plugin Sous-titres

Blocs dédiés à la gestion propre des pistes de sous-titres Matroska :
- `sous-titres.clean` : filtre les pistes audio et sous-titres par langues (`fre,eng`, `none`, `all`) via `mkvmerge`.
- `sous-titres.flags` : marque les drapeaux `default` / `forced` sur la piste de sous-titres principale via `mkvpropedit`.
- `sous-titres.sync` : recale les pistes texte (SRT, ASS, SSA) sur l'audio avec alass (`ffmpeg` extrait l'audio). Les pistes resynchronisées remplacent les originales, en fin de liste.
- `sous-titres.ocr` : convertit les pistes image PGS en SRT avec Tesseract (anglais, français, allemand, espagnol, italien, portugais, néerlandais) ; les PGS sont conservées sauf option contraire. Le décodage PGS est fait en Python, sans dépendance.

Ces deux blocs passent par le script [`scripts/sous_titres.py`](scripts/sous_titres.py) (Python des `interpreteurs`).

