# Plugin Sous-titres

Blocs dédiés à la gestion propre des pistes de sous-titres Matroska :
- `block.subtitles.clean` : filtre les pistes audio et sous-titres par langues (`fre,eng`, `none`, `all`) via `mkvmerge`.
- `block.subtitles.flags` : marque les drapeaux `default` / `forced` sur la piste de sous-titres principale via `mkvpropedit`.
