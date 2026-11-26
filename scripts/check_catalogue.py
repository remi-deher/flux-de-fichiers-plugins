#!/usr/bin/env python3
"""Contrôle complet (schémas JSON, cohérence, empreintes, immuabilité et liens) d'un catalogue.

Conçu pour fonctionner aussi bien sur le dépôt officiel que sur un dépôt tiers autonome :
- validation JSON Schema Draft 2020-12 (`jsonschema` si présent, sinon validateur stdlib intégré) ;
- support de dépôts tiers via `--root`, `--schema-dir`, `--external-index` et `--allow-external-refs` ;
- vérification SHA-256 des manifestes ET de `filesSha256` ;
- mode `--strict-immutable` pour les builds de release (releaseVersion, empreintes complètes, URLs figées).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from catalogue_lib import (
    ALLOWED_DEPENDENCIES,
    ALLOWED_TYPES,
    BINARY_NAME_RE,
    ID_RE,
    OP_ID_RE,
    SHA256_RE,
    LocalSchemaValidator,
    MAX_ICON_BYTES,
    contract_major,
    exposes_breaking_changes,
    exposes_problems,
    first_value,
    is_icon_path,
    is_safe_relative,
    load_json,
    npm_lockfile_problems,
    requirements_problems,
    sha256_file,
    svg_icon_problems,
)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
# Révision git (SHA ou référence) de la base de la PR : les contrats `exposes` de l'opération sont
# comparés à cette version pour exiger une montée de version majeure sur changement cassant.
BASE_REF_ENV = "CATALOGUE_BASE_REF"
FIXTURES_DIR = "fixtures"
GIT_TIMEOUT_SECONDS = 30
MUTABLE_URL_RE = re.compile(r"/(?:refs/heads/|main/|dev/|master/)")


class CatalogueChecker:
    def __init__(
        self,
        root: Path,
        schema_dir: Path,
        external_indexes: list[Path],
        allow_external_refs: bool,
        require_jsonschema: bool,
        strict_immutable: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.schema_dir = schema_dir.resolve()
        self.allow_external_refs = allow_external_refs
        self.strict_immutable = strict_immutable
        self.errors: list[str] = []
        self.validator = LocalSchemaValidator(self.schema_dir)
        if require_jsonschema and not self.validator.has_jsonschema():
            self.fail("paquet Python 'jsonschema' requis (--require-jsonschema)")
        self.external_kinds: dict[str, str] = {}
        for ext_path in external_indexes:
            self._load_external_index(ext_path.resolve())

    def fail(self, message: str) -> None:
        self.errors.append(message)

    def load(self, path: Path) -> Any:
        try:
            return load_json(path)
        except (OSError, ValueError) as error:
            rel = path.relative_to(self.root).as_posix() if path.is_relative_to(self.root) else str(path)
            self.fail(f"{rel} : {error}")
            return None

    def validate_schema(self, schema_name: str, data: Any, rel: str) -> None:
        for err in self.validator.validate(schema_name, data):
            self.fail(f"{rel} (schéma {schema_name}) : {err}")

    def _load_external_index(self, index_path: Path) -> None:
        if not index_path.is_file():
            self.fail(f"index externe introuvable : {index_path}")
            return
        data = self.load(index_path)
        if not isinstance(data, dict):
            return
        for entry in data.get("entries", []):
            if isinstance(entry, dict) and isinstance(entry.get("id"), str) and isinstance(entry.get("type"), str):
                self.external_kinds[entry["id"]] = entry["type"]

    def _resolve_kind(self, ident: str, local_kinds: dict[str, str]) -> str | None:
        return local_kinds.get(ident) or self.external_kinds.get(ident)

    def _check_schemas(self) -> None:
        if not self.schema_dir.is_dir():
            self.fail(f"dossier schema absent : {self.schema_dir}")
            return
        for err in self.validator.check_schemas_compile():
            self.fail(err)

    def _check_build_recipes(self) -> None:
        apps_dir = self.root / "apps"
        if not apps_dir.is_dir():
            return
        for recipe_path in sorted(apps_dir.glob("*/build.json")):
            rel = recipe_path.relative_to(self.root).as_posix()
            recipe = self.load(recipe_path)
            if not isinstance(recipe, dict):
                continue
            self.validate_schema("tool-build.v1.schema.json", recipe, rel)
            if recipe.get("slug") != recipe_path.parent.name:
                self.fail(f"{rel} : slug ({recipe.get('slug')!r}) != dossier ({recipe_path.parent.name!r})")
            self._check_npm_packages(rel, recipe)

    def _check_npm_packages(self, rel: str, recipe: dict[str, Any]) -> None:
        source = recipe.get("source")
        npm = source.get("npmPackages") if isinstance(source, dict) else None
        if not isinstance(npm, dict):
            return
        archives = source.get("archives") or []
        runtime = next((a for a in archives if isinstance(a, dict) and a.get("extractTo") == npm.get("runtime")), None)
        if runtime is None or "node" not in (runtime.get("entrypoints") or {}):
            self.fail(f"{rel} : npmPackages.runtime doit désigner une archive dont le point d'entrée « node » existe")
        extract_dirs = {a.get("extractTo") for a in archives if isinstance(a, dict)}
        archive_binaries = {name for a in archives if isinstance(a, dict) for name in (a.get("entrypoints") or {})}
        npm_binaries = set(npm.get("entrypoints") or {})
        if npm.get("extractTo") in extract_dirs:
            self.fail(f"{rel} : npmPackages.extractTo en collision avec une archive")
        for name in sorted(npm_binaries & archive_binaries):
            self.fail(f"{rel} : point d'entrée npm {name!r} déjà exposé par une archive")
        declared = set(recipe.get("binaries") or [])
        if declared != archive_binaries | npm_binaries:
            self.fail(f"{rel} : binaries {sorted(declared)} != binaires exposés {sorted(archive_binaries | npm_binaries)}")
        project = self.root / str(npm.get("projectDir", ""))
        lock = project / "package-lock.json"
        if not (project / "package.json").is_file() or not lock.is_file():
            self.fail(f"{rel} : package.json et package-lock.json attendus dans {npm.get('projectDir')}")
            return
        for problem in npm_lockfile_problems(self.load(lock)):
            self.fail(f"{lock.relative_to(self.root).as_posix()} : {problem}")

    def _check_distribution(self, app_entry: dict[str, Any], dist_path: Path) -> list[str]:
        rel = dist_path.relative_to(self.root).as_posix()
        dist = self.load(dist_path)
        if not isinstance(dist, dict):
            return []
        self.validate_schema("tool-distribution.v1.schema.json", dist, rel)
        if dist.get("toolId") != app_entry["id"]:
            self.fail(f"{rel} : toolId != {app_entry['id']}")
        if dist.get("toolVersion") != app_entry["version"]:
            self.fail(f"{rel} : toolVersion != {app_entry['version']}")

        allowlist = (dist.get("installPolicy") or {}).get("executableAllowlist", [])
        release_status = dist.get("releaseStatus")
        for idx, artifact in enumerate(dist.get("artifacts", [])):
            if not isinstance(artifact, dict):
                continue
            url = artifact.get("archiveUrl", "")
            if self.strict_immutable and release_status == "released":
                if "artifacts.example.invalid" in url or MUTABLE_URL_RE.search(url):
                    self.fail(f"{rel} : artifact[{idx}].archiveUrl non immuable ({url})")
            bin_rel = artifact.get("binaryRelativePath", "")
            if is_safe_relative(bin_rel) and Path(bin_rel).name not in allowlist:
                self.fail(f"{rel} : artifact[{idx}].binaryRelativePath ({bin_rel}) absent d'executableAllowlist")
            binaries = artifact.get("binaries")
            if isinstance(binaries, dict):
                for exe_name, meta in binaries.items():
                    if exe_name not in allowlist:
                        self.fail(f"{rel} : artifact[{idx}].binaries[{exe_name!r}] absent d'executableAllowlist")
                    if isinstance(meta, dict) and not is_safe_relative(meta.get("relativePath")):
                        self.fail(f"{rel} : artifact[{idx}].binaries[{exe_name!r}].relativePath invalide")
        return list(allowlist) if isinstance(allowlist, list) else []

    def _check_pack_installation(
        self, entry: dict[str, Any], manifest: dict[str, Any], manifest_path: Path, local_kinds: dict[str, str]
    ) -> list[str]:
        checked_paths: list[str] = []
        pack_meta = manifest.get("pack")
        if not isinstance(pack_meta, dict):
            self.fail(f"{entry['id']} : bloc 'pack' manquant dans {entry['manifestPath']}")
            return checked_paths
        rel_install = pack_meta.get("installation")
        if not is_safe_relative(rel_install):
            self.fail(f"{entry['id']} : pack.installation invalide ({rel_install!r})")
            return checked_paths
        install_path = manifest_path.parent / rel_install
        if not install_path.is_file():
            self.fail(f"{entry['id']} : fichier absent {install_path.relative_to(self.root)}")
            return checked_paths
        plan = self.load(install_path)
        if not isinstance(plan, dict):
            return checked_paths
        rel = install_path.relative_to(self.root).as_posix()
        checked_paths.append(rel)
        self.validate_schema("pack-installation.v1.schema.json", plan, rel)
        if plan.get("packId") != entry["id"]:
            self.fail(f"{rel} : packId != {entry['id']}")
        if plan.get("packVersion") != entry["version"]:
            self.fail(f"{rel} : packVersion != {entry['version']}")

        for comp in plan.get("components", []):
            if not isinstance(comp, dict):
                continue
            cid = comp.get("id")
            if not isinstance(cid, str):
                continue
            target_kind = self._resolve_kind(cid, local_kinds)
            if target_kind is None:
                if not self.allow_external_refs:
                    self.fail(f"{rel} : composant inconnu dans l'index ({cid!r})")
            elif comp.get("kind") and target_kind != comp.get("kind"):
                self.fail(f"{rel} : kind de {cid} différent de l'index ({comp.get('kind')} vs {target_kind})")

        entrypoint = plan.get("entrypoint")
        if isinstance(entrypoint, dict) and isinstance(entrypoint.get("id"), str):
            ep_kind = self._resolve_kind(entrypoint["id"], local_kinds)
            if ep_kind is None and not self.allow_external_refs:
                self.fail(f"{rel} : entrypoint inconnu ({entrypoint['id']!r})")
            elif ep_kind is not None and entrypoint.get("kind") and ep_kind != entrypoint["kind"]:
                self.fail(f"{rel} : entrypoint.kind ({entrypoint['kind']}) != {ep_kind}")
        return checked_paths

    def _check_operation(
        self,
        op_path: Path,
        owner_plugin: str,
        local_kinds: dict[str, str],
        app_allowlists: dict[str, list[str]],
        operations: dict[str, dict[str, Any]],
    ) -> None:
        rel = op_path.relative_to(self.root).as_posix()
        op = self.load(op_path)
        if not isinstance(op, dict):
            return
        self.validate_schema("operation-runtime.v1.schema.json", op, rel)

        op_id = op.get("id")
        if not isinstance(op_id, str) or not OP_ID_RE.match(op_id):
            return
        if op_id in operations:
            self.fail(f"{rel} : operationId dupliqué {op_id}")
        if op.get("providerId") != owner_plugin:
            self.fail(f"{rel} : providerId ({op.get('providerId')!r}) != plugin propriétaire ({owner_plugin!r})")

        runtime = op.get("runtime")
        if not isinstance(runtime, dict):
            return
        rkind = runtime.get("kind")
        if rkind == "binary":
            tool = runtime.get("tool")
            exe = runtime.get("executable")
            if isinstance(tool, dict) and isinstance(tool.get("id"), str):
                tid = tool["id"]
                tkind = self._resolve_kind(tid, local_kinds)
                if tkind is None:
                    if not self.allow_external_refs:
                        self.fail(f"{rel} : runtime.tool.id inconnu ({tid!r})")
                elif tkind != "app":
                    self.fail(f"{rel} : runtime.tool.id doit référencer une 'app' ({tid!r} est {tkind!r})")
                elif tid in app_allowlists and isinstance(exe, str) and exe not in app_allowlists[tid]:
                    self.fail(f"{rel} : executable {exe!r} absent de executableAllowlist de {tid}")
            if not isinstance(exe, str) or not BINARY_NAME_RE.match(exe):
                self.fail(f"{rel} : runtime.executable invalide ({exe!r})")
        elif rkind == "http":
            settings_plugin = runtime.get("settingsPluginId")
            if settings_plugin is not None:
                skind = self._resolve_kind(settings_plugin, local_kinds)
                if skind is None:
                    if not self.allow_external_refs:
                        self.fail(f"{rel} : settingsPluginId inconnu ({settings_plugin!r})")
                elif skind != "plugin":
                    self.fail(f"{rel} : settingsPluginId doit être un 'plugin' ({settings_plugin!r})")

        if "exposes" in op:
            self._check_exposes(op_path, rel, op)
        if rkind == "script" and "requires" in runtime:
            for problem in requirements_problems(runtime["requires"]):
                self.fail(f"{rel} : runtime.requires : {problem}")

        operations[op_id] = op

    def _check_exposes(self, op_path: Path, rel: str, op: dict[str, Any]) -> None:
        """Variables exposées : règles du central, chemins résolus sur la fixture, version de contrat."""
        exposes = op["exposes"]
        problems = exposes_problems(exposes)
        for problem in problems:
            self.fail(f"{rel} : exposes : {problem}")
        if problems:
            return
        runtime = op.get("runtime") if isinstance(op.get("runtime"), dict) else {}
        enrichment_key = runtime.get("probeEnrichmentKey")
        for variable in exposes.get("variables", []):
            root_key = re.split(r"[.\[]", variable["path"], maxsplit=1)[0]
            if isinstance(enrichment_key, str) and root_key != enrichment_key:
                self.fail(
                    f"{rel} : exposes : le chemin de {variable['name']!r} doit commencer par la clé "
                    f"d'enrichissement de la sonde ({enrichment_key!r}), pas {root_key!r}"
                )
        self._check_exposes_fixture(op_path, rel, exposes)
        self._check_exposes_compat(rel, exposes)

    def _check_exposes_fixture(self, op_path: Path, rel: str, exposes: dict[str, Any]) -> None:
        """La fixture `<plugin>/fixtures/<opération>.json` est un `mediaInfo` d'exemple : chaque chemin doit s'y résoudre."""
        fixture_path = op_path.parent.parent / FIXTURES_DIR / op_path.name
        fixture_rel = fixture_path.relative_to(self.root).as_posix()
        if not fixture_path.is_file():
            self.fail(f"{rel} : exposes : fixture manquante ({fixture_rel})")
            return
        fixture = self.load(fixture_path)
        for variable in exposes.get("variables", []):
            if first_value(fixture, variable["path"]) is None:
                self.fail(f"{rel} : exposes : {variable['name']!r} ne se résout pas sur {fixture_rel} ({variable['path']})")

    def _git_show_json(self, ref: str, rel: str) -> Any:
        """Contenu JSON de `rel` à la révision `ref`, ou None si git, la révision ou le fichier manque."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{ref}:./{rel}"],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def _check_exposes_compat(self, rel: str, exposes: dict[str, Any]) -> None:
        """Un changement cassant du contrat exposé impose une montée de version majeure (ADR 0025)."""
        base_ref = os.environ.get(BASE_REF_ENV, "").strip()
        if not base_ref:
            return
        previous = self._git_show_json(base_ref, rel)
        old = previous.get("exposes") if isinstance(previous, dict) else None
        if not isinstance(old, dict):
            return
        old_major, new_major = contract_major(old.get("contractVersion")), contract_major(exposes.get("contractVersion"))
        if old_major is not None and new_major is not None and new_major < old_major:
            self.fail(f"{rel} : exposes : contractVersion diminue ({old.get('contractVersion')} → {exposes.get('contractVersion')})")
        changes = exposes_breaking_changes(old, exposes)
        if changes and (old_major is None or new_major is None or new_major <= old_major):
            self.fail(
                f"{rel} : exposes : changement cassant sans montée de version majeure du contrat "
                f"({old.get('contractVersion')} → {exposes.get('contractVersion')}) : " + " ; ".join(changes)
            )

    def _check_block(
        self,
        entry: dict[str, Any],
        block_path: Path,
        local_kinds: dict[str, str],
        plugin_declared_files: dict[str, set[str]],
        plugin_declared_blocks: dict[str, set[str]],
        operations: dict[str, dict[str, Any]],
    ) -> None:
        rel = block_path.relative_to(self.root).as_posix()
        block = self.load(block_path)
        if not isinstance(block, dict):
            return
        self.validate_schema("block-runtime.v1.schema.json", block, rel)

        if block.get("id") != entry["id"] or block.get("version") != entry["version"]:
            self.fail(f"{rel} : id/version incompatibles avec l'index")

        op_id = block.get("operationId")
        if isinstance(op_id, str):
            if op_id not in operations:
                self.fail(f"{rel} : operationId introuvable dans les opérations du dépôt ({op_id!r})")
            else:
                op_defaults = (operations[op_id].get("runtime") or {}).get("defaults", {})
                if isinstance(op_defaults, dict):
                    for field in (block.get("ui") or {}).get("fields", []):
                        fname = field.get("name")
                        if "default" in field and fname in op_defaults and field["default"] != op_defaults[fname]:
                            self.fail(
                                f"{rel} : défaut divergent pour {fname!r} "
                                f"(bloc={field['default']!r} vs opération={op_defaults[fname]!r})"
                            )

        owner = entry.get("owner")
        in_files = owner in plugin_declared_files and rel in plugin_declared_files[owner]
        in_blocks = owner in plugin_declared_blocks and entry["id"] in plugin_declared_blocks[owner]
        if owner in plugin_declared_files and not (in_files or in_blocks):
            self.fail(f"{rel} : bloc non déclaré dans files[] du plugin propriétaire {owner}")

        ui = block.get("ui")
        if isinstance(ui, dict):
            for nxt in ui.get("suggestedNext", []):
                if self._resolve_kind(nxt, local_kinds) is None and not self.allow_external_refs:
                    self.fail(f"{rel} : suggestedNext référence un identifiant inconnu ({nxt!r})")

    def _check_icon(
        self, raw_manifest: str, manifest_path: Path, icon: object, required_secondary: set[str]
    ) -> None:
        """L'icône déclarée existe, reste dans le dépôt et respecte la liste blanche SVG."""
        if not is_icon_path(icon):
            self.fail(f"{raw_manifest} : icon doit être un chemin relatif sûr terminé par .svg ({icon!r})")
            return
        target = (manifest_path.parent / str(icon)).resolve()
        if not target.is_relative_to(self.root) or not target.is_file():
            self.fail(f"{raw_manifest} : icône absente ou hors du dépôt ({icon})")
            return
        data = target.read_bytes()
        if len(data) > MAX_ICON_BYTES:
            self.fail(f"{raw_manifest} : icône {icon} trop lourde (plus de {MAX_ICON_BYTES} octets)")
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            self.fail(f"{raw_manifest} : icône {icon} n'est pas en UTF-8")
            return
        for problem in svg_icon_problems(text):
            self.fail(f"{raw_manifest} : icône {icon} refusée ({problem})")
        required_secondary.add(target.relative_to(self.root).as_posix())

    def _check_files_sha256(self, index: dict[str, Any], required_secondary: set[str]) -> None:
        files_sha = index.get("filesSha256")
        if files_sha is None:
            if self.strict_immutable and required_secondary:
                self.fail("index.json : filesSha256 requis en mode --strict-immutable")
            return
        if not isinstance(files_sha, dict):
            return
        for rel, expected in files_sha.items():
            if not is_safe_relative(rel):
                self.fail(f"index.json : chemin filesSha256 invalide ({rel!r})")
                continue
            target = self.root / rel
            if not target.is_file():
                self.fail(f"index.json : fichier absent pour filesSha256 ({rel})")
                continue
            actual = sha256_file(target)
            if actual != expected:
                self.fail(f"index.json : filesSha256[{rel!r}] périmé ({expected[:12]} != {actual[:12]})")
        if self.strict_immutable:
            for rel in sorted(required_secondary):
                if rel not in files_sha:
                    self.fail(f"index.json : filesSha256 manquant pour {rel}")

    def _check_index(self) -> None:
        index_path = self.root / "index.json"
        index = self.load(index_path)
        if not isinstance(index, dict):
            return
        self.validate_schema("catalogue-index.v1.schema.json", index, "index.json")

        if self.strict_immutable and not isinstance(index.get("releaseVersion"), str):
            self.fail("index.json : releaseVersion requis en mode --strict-immutable")

        entries = index.get("entries")
        if not isinstance(entries, list):
            return

        seen_ids: set[str] = set()
        kinds: dict[str, str] = {}
        manifest_dirs: dict[str, Path] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ident = entry.get("id")
            kind = entry.get("type")
            raw_manifest = entry.get("manifestPath")
            if not isinstance(ident, str) or not ID_RE.match(ident):
                continue
            if ident in seen_ids:
                self.fail(f"index.json : identifiant dupliqué {ident}")
            seen_ids.add(ident)
            if kind in ALLOWED_TYPES:
                kinds[ident] = kind
            if isinstance(raw_manifest, str) and is_safe_relative(raw_manifest):
                manifest_dirs[ident] = (self.root / raw_manifest).parent

        plugin_declared_files: dict[str, set[str]] = {}
        plugin_declared_blocks: dict[str, set[str]] = {}
        app_allowlists: dict[str, list[str]] = {}
        operations: dict[str, dict[str, Any]] = {}
        block_entries: list[dict[str, Any]] = []
        non_block_entries: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
        required_secondary: set[str] = set()

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ident, kind = entry.get("id"), entry.get("type")
            raw_manifest = entry.get("manifestPath")
            if entry.get("subcategory") and not entry.get("category"):
                self.fail(f"{ident} : subcategory exige une category dans le manifeste")
            if not is_safe_relative(raw_manifest):
                self.fail(f"{ident} : manifestPath invalide ({raw_manifest!r})")
                continue
            manifest_path = self.root / raw_manifest
            if not manifest_path.is_file():
                self.fail(f"{ident} : fichier absent {raw_manifest}")
                continue
            expected_sha = entry.get("sha256")
            if expected_sha is None and self.strict_immutable:
                self.fail(f"{ident} : sha256 requis en mode --strict-immutable")
            elif isinstance(expected_sha, str):
                if not SHA256_RE.match(expected_sha):
                    self.fail(f"{ident} : sha256 invalide dans index.json")
                else:
                    actual_sha = sha256_file(manifest_path)
                    if actual_sha != expected_sha:
                        self.fail(f"{ident} : sha256 périmé dans index.json ({expected_sha[:12]} != {actual_sha[:12]})")

            if kind == "block":
                owner = entry.get("owner")
                if kinds.get(owner) not in {"plugin", "script"}:
                    self.fail(
                        f"{ident} : un bloc doit avoir un plugin ou script propriétaire dans le même dépôt (owner={owner!r})"
                    )
                elif owner in manifest_dirs:
                    expected_blocks_dir = (manifest_dirs[owner] / "blocks").resolve()
                    if not manifest_path.resolve().is_relative_to(expected_blocks_dir):
                        self.fail(f"{ident} : le bloc doit être rangé sous {expected_blocks_dir.relative_to(self.root)}")
                block_entries.append(entry)
                continue

            manifest = self.load(manifest_path)
            if not isinstance(manifest, dict):
                continue
            self.validate_schema("manifest.v1.1.schema.json", manifest, raw_manifest)
            for key in ("id", "type", "version", "name"):
                if manifest.get(key) != entry.get(key):
                    self.fail(f"{ident} : {key} diffère entre l'index et le manifeste")
            if kind == "app":
                dist_path = manifest_path.parent / "distribution.v1.json"
                invocation = (manifest.get("tool") or {}).get("invocation")
                expects_dist = (
                    entry.get("distribution") == "autonomous-binary"
                    or invocation in {"host-binary", "binary"}
                    or dist_path.is_file()
                )
                if expects_dist and not dist_path.is_file():
                    self.fail(f"{ident} : distribution.v1.json absent")
                elif dist_path.is_file():
                    required_secondary.add(dist_path.relative_to(self.root).as_posix())
                    app_allowlists[ident] = self._check_distribution(entry, dist_path)
            non_block_entries.append((entry, manifest_path, manifest))

        for entry, manifest_path, manifest in non_block_entries:
            ident, kind = entry["id"], entry["type"]
            raw_manifest = entry["manifestPath"]
            declared_paths: set[str] = set()
            for item in manifest.get("files", []):
                if not isinstance(item, dict) or not is_safe_relative(item.get("path")):
                    continue
                target = (manifest_path.parent / item["path"]).resolve()
                if not target.is_file():
                    self.fail(f"{raw_manifest} : fichier déclaré absent ({item['path']})")
                else:
                    rel_target = target.relative_to(self.root).as_posix()
                    declared_paths.add(rel_target)
                    is_json = item["path"].endswith(".json") or item.get("mediaType") == "application/json"
                    if (is_json or item.get("role") == "script") and item.get("role") != "block":
                        required_secondary.add(rel_target)
                    if kind in {"plugin", "script"} and item.get("role") == "operation":
                        self._check_operation(target, ident, kinds, app_allowlists, operations)
            if manifest.get("icon") is not None:
                self._check_icon(raw_manifest, manifest_path, manifest["icon"], required_secondary)
            if kind in {"plugin", "script"}:
                plugin_declared_files[ident] = declared_paths
                plugin_declared_blocks[ident] = {
                    b["id"]
                    for b in manifest.get("blocks", [])
                    if isinstance(b, dict) and isinstance(b.get("id"), str)
                }

            for dep in manifest.get("dependencies", []):
                if not isinstance(dep, dict) or not isinstance(dep.get("id"), str):
                    continue
                target_kind = self._resolve_kind(dep["id"], kinds)
                if target_kind is None:
                    if not self.allow_external_refs:
                        self.fail(f"{ident} : dépendance inconnue {dep['id']}")
                elif target_kind not in ALLOWED_DEPENDENCIES.get(kind, set()):
                    self.fail(f"{ident} ({kind}) ne peut pas dépendre de {dep['id']} ({target_kind})")

            if kind == "pack":
                required_secondary.update(self._check_pack_installation(entry, manifest, manifest_path, kinds))

        for block_entry in block_entries:
            self._check_block(
                block_entry,
                self.root / block_entry["manifestPath"],
                kinds,
                plugin_declared_files,
                plugin_declared_blocks,
                operations,
            )

        self._check_files_sha256(index, required_secondary)

        listed = {entry.get("manifestPath") for entry in entries if isinstance(entry, dict)}
        for manifest in self.root.glob("*/**/manifest.json"):
            relative = manifest.relative_to(self.root).as_posix()
            if not relative.startswith(("examples/", "schema/", "templates/", ".git/")) and relative not in listed:
                self.fail(f"{relative} : manifeste absent de l'index")

    def _check_markdown_links(self) -> None:
        link = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
        for doc in self.root.rglob("*.md"):
            if ".git" in doc.parts:
                continue
            for target in link.findall(doc.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("mailto:"):
                    continue
                if not (doc.parent / target).exists():
                    self.fail(f"{doc.relative_to(self.root)} : lien cassé {target}")

    def run(self) -> list[str]:
        self._check_schemas()
        self._check_build_recipes()
        self._check_index()
        self._check_markdown_links()
        return self.errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valide un catalogue Forgearr (officiel ou tiers).")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Racine du dépôt à valider.")
    parser.add_argument("--schema-dir", type=Path, default=None, help="Dossier contenant les schémas JSON.")
    parser.add_argument(
        "--external-index",
        type=Path,
        action="append",
        default=[],
        help="Index externe (ex. catalogue officiel) pour résoudre les dépendances cross-dépôt.",
    )
    parser.add_argument(
        "--allow-external-refs",
        action="store_true",
        help="Autorise les références vers des IDs externes (apps/blocs/plugins d'un autre dépôt).",
    )
    parser.add_argument(
        "--require-jsonschema",
        action="store_true",
        help="Échoue si le paquet Python `jsonschema` n'est pas installé.",
    )
    parser.add_argument(
        "--strict-immutable",
        action="store_true",
        help="Exige releaseVersion, sha256/filesSha256 complets et URLs de release figées.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    schema_dir = args.schema_dir or (root / "schema" if (root / "schema").is_dir() else DEFAULT_ROOT / "schema")

    checker = CatalogueChecker(
        root=root,
        schema_dir=schema_dir,
        external_indexes=args.external_index,
        allow_external_refs=args.allow_external_refs,
        require_jsonschema=args.require_jsonschema,
        strict_immutable=args.strict_immutable,
    )
    errors = checker.run()

    template_root = root / "templates" / "depot-tiers"
    if args.root.resolve() == DEFAULT_ROOT and template_root.is_dir():
        tpl_checker = CatalogueChecker(
            root=template_root,
            schema_dir=schema_dir,
            external_indexes=[root / "index.json"],
            allow_external_refs=False,
            require_jsonschema=args.require_jsonschema,
            strict_immutable=False,
        )
        for err in tpl_checker.run():
            errors.append(f"[templates/depot-tiers] {err}")

    for message in errors:
        print(message)
    print(f"{len(errors)} problème(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
