# tool.internal.telemetry

Sonde système interne (CPU, RAM, GPU, stockage).

## Distribution Option B

[`distribution.v1.json`](distribution.v1.json) — binaire `flux-telemetry`,
architectures `x86_64` / `aarch64`, SHA-256 obligatoires,
`networkAtInstall: offline-preseeded` (artefact préchargé préféré).

## Capacités

[`capabilities.v1.json`](capabilities.v1.json) — métriques et contraintes
(pas de shell, pas de réseau runtime, chemins opaques).

## Lien

ADR / conception cache : ticket backlog #42.
