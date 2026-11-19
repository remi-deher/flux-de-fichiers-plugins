# Routage : format HDR / Dolby Vision (`route-by-hdr-format`)

Analyse les métadonnées vidéo de `mediaInfo` (ou lance `mediainfo --Output=JSON` en repli si les informations HDR ne sont pas encore dans le contexte) pour aiguiller un flow selon le format HDR détecté :

- `any-dynamic` (défaut) : Dolby Vision ou HDR10+ ;
- `dolby-vision` : toute piste Dolby Vision ;
- `dv-profile-7` : Dolby Vision profil 7 (double couche UHD Blu-ray) ;
- `hdr10plus` : HDR10+ (SMPTE ST 2094 App 4) ;
- `any-hdr` : tout HDR (Dolby Vision, HDR10+, HDR10, HLG, PQ).

Route sur `true` (« Correspond ») ou `false` (« Autre »).
