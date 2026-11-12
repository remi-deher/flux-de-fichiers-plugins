# Limites et preuves pour revue indépendante

## Chemins produits (dépôt `/home/remi/GitHub/flux-de-fichiers-plugins`)

- `README.md`, `.gitignore`
- `schema/manifest.v1.schema.json`, `schema/catalogue-index.v1.schema.json`
- `catalogue/index.json`
- `apps/mkvtoolnix/`, `apps/postgresql/` (+ `deploy/*.example`)
- `plugins/remux-mkv.example/`, `flows/remux-rapide.example/`, `presets/remux-defaut.example/`
- `resources/{fonts,images,audio,color,languages,templates}/…`
- `docs/*.md`, `deploy/README.md`

## Non fait (volontaire)

- Commit / push / remote GitHub → #12
- Modification de `flux-de-fichiers` (src, migrations, Compose) → éviter conflit #10
- Chargeur de plugins / exécution de flux
- Tests
- Alternatives DB ou remux

## Décisions à arbitrer (hors exécution #11)

1. Stratégie de distribution du catalogue (sous-module git, release d’artefact, volume).
2. Moment de bascule des fichiers `deploy/` applicatifs vers ce dépôt.
3. Forme Rust exacte du trait `Remuxer` / injection dans le worker (#10 ou ticket suivi).
4. Contenu réel des premières ressources (licences, icônes) au-delà des placeholders.
