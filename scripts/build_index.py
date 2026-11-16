#!/usr/bin/env python3
"""Génère ou contrôle `index.json` à la racine depuis les manifestes du dépôt.

Utilisable sur le dépôt officiel comme sur tout dépôt tiers autonome :
- découvre automatiquement `apps/`, `plugins/` (+ `blocks/`), `flows/`, `packs/`,
  `presets/` et `resources/` ;
- calcule le `sha256` de chaque manifeste/bloc ainsi que `filesSha256` pour tous
  les fichiers JSON annexes (`distribution.v1.json`, `operations/*.json`,
  `installation.json`, etc.) ;
- préserve l'ordre existant des entrées et ajoute les nouvelles de façon déterministe.
"""
import argparse
import sys
from pathlib import Path
from typing import Any

from catalogue_lib import SECTION_ORDER, is_safe_relative, load_json, sha256_file, write_json

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def _discover_manifests(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for folder in ("apps", "plugins", "flows", "presets", "packs"):
        base = root / folder
        if base.is_dir():
            candidates.extend(sorted(base.glob("*/manifest.json")))
    res_base = root / "resources"
    if res_base.is_dir():
        candidates.extend(sorted(res_base.glob("*/*/manifest.json")))
    return candidates


def _collect_secondary_json(root: Path, manifest_path: Path, manifest: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    kind = manifest.get("type")

    def add_file(target: Path) -> None:
        if target.is_file():
            rel = target.relative_to(root).as_posix()
            hashes[rel] = sha256_file(target)

    if kind == "app":
        add_file(manifest_path.parent / "distribution.v1.json")
    if kind == "pack":
        inst = (manifest.get("pack") or {}).get("installation")
        if is_safe_relative(inst):
            add_file(manifest_path.parent / inst)

    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            continue
        rel_item = item.get("path")
        if not is_safe_relative(rel_item):
            continue
        is_json = rel_item.endswith(".json") or item.get("mediaType") == "application/json"
        if is_json and item.get("role") != "block":
            add_file(manifest_path.parent / rel_item)
    return hashes


def _build_manifest_entry(
    root: Path, manifest_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    manifest = load_json(manifest_path)
    rel = manifest_path.relative_to(root).as_posix()
    kind = manifest["type"]
    entry: dict[str, Any] = {
        "id": manifest["id"],
        "type": kind,
        "version": manifest["version"],
        "name": manifest["name"],
        "manifestPath": rel,
    }
    if kind == "app" and isinstance(manifest.get("tool"), dict):
        tool = manifest["tool"]
        if tool.get("capability"):
            entry["capability"] = tool["capability"]
        if "currentChoice" in tool:
            entry["currentChoice"] = bool(tool["currentChoice"])
        dist_path = manifest_path.parent / "distribution.v1.json"
        if dist_path.is_file():
            dist = load_json(dist_path)
            if isinstance(dist, dict) and dist.get("distributionMode"):
                entry["distribution"] = dist["distributionMode"]
    elif manifest.get("capability"):
        entry["capability"] = manifest["capability"]

    if manifest.get("category") and kind != "block":
        entry["category"] = manifest["category"]
    if manifest.get("tags"):
        entry["tags"] = manifest["tags"]
    entry["sha256"] = sha256_file(manifest_path)

    secondary_hashes = _collect_secondary_json(root, manifest_path, manifest)

    block_entries: list[dict[str, Any]] = []
    if kind == "plugin":
        blocks_dir = manifest_path.parent / "blocks"
        if blocks_dir.is_dir():
            for block_path in sorted(blocks_dir.glob("*.json")):
                block = load_json(block_path)
                block_entries.append(
                    {
                        "id": block["id"],
                        "type": "block",
                        "owner": manifest["id"],
                        "version": block["version"],
                        "name": block["name"],
                        "manifestPath": block_path.relative_to(root).as_posix(),
                        "sha256": sha256_file(block_path),
                    }
                )
    return entry, block_entries, secondary_hashes


def build_index_document(
    root: Path,
    generated_for: str | None = None,
    release_version: str | None = None,
    clear_release_version: bool = False,
) -> dict[str, Any]:
    index_path = root / "index.json"
    existing_order: dict[str, int] = {}
    existing_generated_for = None
    existing_release_version = None
    if index_path.is_file():
        existing = load_json(index_path)
        existing_generated_for = existing.get("generatedFor")
        existing_release_version = existing.get("releaseVersion")
        for idx, item in enumerate(existing.get("entries", [])):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                existing_order[item["id"]] = idx

    collected: list[dict[str, Any]] = []
    files_sha256: dict[str, str] = {}
    for manifest_path in _discover_manifests(root):
        entry, blocks, secondary = _build_manifest_entry(root, manifest_path)
        collected.append(entry)
        collected.extend(blocks)
        files_sha256.update(secondary)

    collected.sort(
        key=lambda e: (
            SECTION_ORDER.get(e["type"], 99),
            existing_order.get(e["id"], 10_000_000),
            e["manifestPath"],
        )
    )
    doc: dict[str, Any] = {
        "schemaVersion": "1.0.0",
        "generatedFor": generated_for or existing_generated_for or root.name,
    }
    effective_release = None if clear_release_version else (release_version or existing_release_version)
    if effective_release:
        doc["releaseVersion"] = effective_release
    if files_sha256:
        doc["filesSha256"] = dict(sorted(files_sha256.items()))
    doc["entries"] = collected
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Génère index.json à la racine depuis les manifestes.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Racine du dépôt.")
    parser.add_argument("--generated-for", type=str, default=None, help="Valeur de generatedFor.")
    parser.add_argument("--release-version", type=str, default=None, help="Version SemVer de release figée.")
    parser.add_argument(
        "--clear-release-version",
        action="store_true",
        help="Retire releaseVersion (utile sur branche de travail mutable).",
    )
    parser.add_argument("--check", action="store_true", help="Échoue si index.json n'est pas à jour.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    index_path = root / "index.json"
    generated = build_index_document(
        root,
        generated_for=args.generated_for,
        release_version=args.release_version,
        clear_release_version=args.clear_release_version,
    )

    if args.check:
        if not index_path.is_file():
            print("index.json absent", file=sys.stderr)
            return 1
        current = load_json(index_path)
        if current != generated:
            print(
                "index.json n'est pas synchronisé avec les manifestes "
                "(lancez python3 scripts/build_index.py).",
                file=sys.stderr,
            )
            return 1
        print("index.json est à jour.")
        return 0

    write_json(index_path, generated)
    print(f"Index généré ({len(generated['entries'])} entrées) : {index_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
