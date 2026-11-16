#!/usr/bin/env python3
"""Générateur CLI pour initialiser un dépôt tiers ou ajouter des pièces au catalogue."""
import argparse
import re
import sys
from pathlib import Path
from typing import Any

from build_index import build_index_document
from catalogue_lib import write_json

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _slug_to_id(namespace: str | None, kind_prefix: str, slug: str) -> str:
    if namespace:
        return f"{namespace}.{kind_prefix}.{slug}"
    return f"{kind_prefix}.{slug}"


def _validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise SystemExit(f"Slug invalide {slug!r} : minuscules, chiffres et tirets uniquement.")
    return slug


def _validate_ns(ns: str | None) -> str | None:
    if not ns:
        return None
    if not re.match(r"^[a-z0-9]+(\.[a-z0-9]+)*$", ns):
        raise SystemExit(f"Namespace invalide {ns!r} : format attendu ex. com.auteur")
    return ns


def _update_index(root: Path, generated_for: str | None = None) -> None:
    index_doc = build_index_document(root, generated_for=generated_for)
    write_json(root / "index.json", index_doc)


def cmd_init_repo(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    ns = _validate_ns(args.namespace) or "org.exemple"
    write_json(
        root / "index.json",
        {"schemaVersion": "1.0.0", "generatedFor": args.name, "entries": []},
    )
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {args.name}\n\n"
            "Dépôt de plugins pour Flux de Fichiers.\n\n"
            "URL d'index à ajouter dans Flux de Fichiers :\n"
            "`https://<hote>/<depot>/main/index.json` (ou un tag/release immuable).\n",
            encoding="utf-8",
        )
    if args.with_example:
        example_args = argparse.Namespace(
            root=root,
            slug="exemple",
            namespace=ns,
            name="Plugin Exemple",
            author=args.author,
            license=args.license,
            kind="http",
            tool_id="app.ffmpeg",
            executable="ffmpeg",
        )
        cmd_plugin(example_args)
    else:
        _update_index(root, generated_for=args.name)
    print(f"Dépôt initialisé dans {root}")


def cmd_plugin(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    slug = _validate_slug(args.slug)
    ns = _validate_ns(args.namespace)
    plugin_id = _slug_to_id(ns, "plugin", slug)
    block_id = _slug_to_id(ns, "block", slug)
    op_id = _slug_to_id(ns, "operation", slug)
    pdir = root / "plugins" / slug
    if pdir.exists():
        raise SystemExit(f"Le dossier existe déjà : {pdir}")

    op_runtime: dict[str, Any]
    deps: list[dict[str, Any]] = []
    if args.kind == "binary":
        op_runtime = {
            "kind": "binary",
            "tool": {"id": args.tool_id, "version": "1.0.0"},
            "executable": args.executable,
            "executionMode": "staged-output",
            "outputExtension": "mkv",
            "outputContentType": "video/x-matroska",
            "outputFilename": "output.mkv",
            "postValidate": "non-empty",
            "errorCode": "operation_failed",
            "successMessage": f"{args.name} terminé",
            "defaults": {"note": ""},
            "argv": [
                "-i",
                {"param": "source", "as": "filePath"},
                {"param": "destination", "as": "filePath"},
            ],
            "console": {
                "progressFormat": "none",
                "progressStream": "stderr",
                "successExitCodes": [0],
                "warningExitCodes": [],
                "timeoutSeconds": 600,
            },
        }
        deps.append({"id": args.tool_id, "versionRange": "^1.0.0", "kind": "app", "optional": True})
    else:
        op_runtime = {
            "kind": "http",
            "settingsPluginId": plugin_id,
            "requiredSettings": ["url"],
            "errorCode": "integration_failed",
            "failOnErrorParam": "fail_on_error",
            "timeoutSeconds": 15,
            "defaults": {},
            "steps": [
                {
                    "url": "{$setting.url}",
                    "method": "POST",
                    "body": {"job_id": "{$context.jobId}", "source": "{$context.sourceName}"},
                    "successMessage": f"{args.name} transmis",
                }
            ],
        }

    manifest: dict[str, Any] = {
        "schemaVersion": "1.1.0",
        "id": plugin_id,
        "type": "plugin",
        "version": "1.0.0",
        "name": args.name,
        "description": f"Plugin {args.name}.",
        "author": args.author,
        "license": args.license,
        "capability": "other" if args.kind == "binary" else "integration",
        "files": [
            {"path": "README.md", "role": "docs", "mediaType": "text/markdown"},
            {"path": f"blocks/{slug}.json", "role": "block", "mediaType": "application/json"},
            {"path": f"operations/{slug}.json", "role": "operation", "mediaType": "application/json"},
        ],
        "compatibility": {"appMin": "1.0.0", "platforms": ["linux/amd64", "linux/arm64"]},
    }
    if deps:
        manifest["dependencies"] = deps
    if args.kind == "http":
        manifest["settingsSchema"] = {
            "fields": [
                {
                    "name": "url",
                    "label": "URL du service",
                    "type": "url",
                    "default": "https://example.invalid/hook",
                    "required": True,
                }
            ]
        }

    block = {
        "schemaVersion": "1.1.0",
        "id": block_id,
        "version": "1.0.0",
        "name": args.name,
        "description": f"Bloc fourni par {plugin_id}.",
        "category": "io" if args.kind == "http" else "media",
        "operationId": op_id,
        "operationVersion": "1.0.0",
        "sockets": {
            "inputs": [{"id": "source", "label": "Fichier source", "dataType": "file", "mediaType": "*/*"}],
            "outputs": [{"id": "destination", "label": "Fichier de sortie", "dataType": "file", "mediaType": "*/*"}],
        },
        "ui": {
            "category": "Plugins tiers",
            "domain": "integration" if args.kind == "http" else "media",
            "icon": "fas fa-puzzle-piece",
            "color": "#38BDF8",
            "suggestedNext": ["block.core.file-output"],
            "fields": (
                [{"name": "fail_on_error", "label": "Échec bloquant", "type": "boolean", "default": False}]
                if args.kind == "http"
                else [{"name": "note", "label": "Note", "type": "string", "default": ""}]
            ),
        },
    }

    operation = {
        "schemaVersion": "1.1.0",
        "id": op_id,
        "version": "1.0.0",
        "name": args.name,
        "providerId": plugin_id,
        "providerKind": "plugin",
        "capability": "integration" if args.kind == "http" else "other",
        "status": "validated",
        "runtime": op_runtime,
    }

    write_json(pdir / "manifest.json", manifest)
    write_json(pdir / "blocks" / f"{slug}.json", block)
    write_json(pdir / "operations" / f"{slug}.json", operation)
    (pdir / "README.md").write_text(f"# {args.name}\n\nIdentifiant : `{plugin_id}`.\n", encoding="utf-8")
    _update_index(root)
    print(f"Plugin créé : {pdir.relative_to(root)} ({plugin_id})")


def cmd_app(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    slug = _validate_slug(args.slug)
    ns = _validate_ns(args.namespace)
    app_id = _slug_to_id(ns, "app", slug)
    adir = root / "apps" / slug
    if adir.exists():
        raise SystemExit(f"Le dossier existe déjà : {adir}")

    manifest = {
        "schemaVersion": "1.1.0",
        "id": app_id,
        "type": "app",
        "version": "1.0.0",
        "name": args.name,
        "description": f"Application autonome {args.name}.",
        "author": args.author,
        "license": args.license,
        "files": [
            {"path": "README.md", "role": "docs", "mediaType": "text/markdown"},
            {"path": "distribution.v1.json", "role": "config", "mediaType": "application/json"},
        ],
        "compatibility": {"platforms": ["linux/amd64", "linux/arm64"]},
        "dependencies": [],
        "tool": {
            "capability": args.capability,
            "interface": args.interface,
            "invocation": "host-binary",
            "currentChoice": False,
        },
    }
    placeholder_sha = "0" * 64
    dist = {
        "schemaVersion": "1.0.0",
        "toolId": app_id,
        "toolVersion": "1.0.0",
        "distributionMode": "autonomous-binary",
        "releaseStatus": "contract-only",
        "artifacts": [
            {
                "arch": "x86_64",
                "os": "linux",
                "archiveUrl": f"https://artifacts.example.invalid/apps/{slug}/1.0.0/{slug}-linux-x86_64.tar.gz",
                "archiveFormat": "tar.gz",
                "archiveSha256": placeholder_sha,
                "binaryRelativePath": args.executable,
                "binarySha256": placeholder_sha,
                "permissions": {"unixMode": "0755", "owner": "runtime-user", "executableBit": True},
            }
        ],
        "installPolicy": {
            "verifySha256BeforeExec": True,
            "refuseMismatchedDigest": True,
            "cacheRootRelative": f"tools-cache/{slug}/1.0.0",
            "noShellUnpack": True,
            "executableAllowlist": [args.executable],
            "networkAtInstall": "explicit-allowlist",
        },
    }
    write_json(adir / "manifest.json", manifest)
    write_json(adir / "distribution.v1.json", dist)
    (adir / "README.md").write_text(f"# {args.name}\n\nContrat Option B pour `{app_id}`.\n", encoding="utf-8")
    _update_index(root)
    print(f"Application créée : {adir.relative_to(root)} ({app_id})")


def cmd_flow(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    slug = _validate_slug(args.slug)
    ns = _validate_ns(args.namespace)
    flow_id = _slug_to_id(ns, "flow", slug)
    fdir = root / "flows" / slug
    if fdir.exists():
        raise SystemExit(f"Le dossier existe déjà : {fdir}")

    manifest: dict[str, Any] = {
        "schemaVersion": "1.1.0",
        "id": flow_id,
        "type": "flow",
        "version": "1.0.0",
        "name": args.name,
        "description": f"Flow déclaratif {args.name}.",
        "author": args.author,
        "license": args.license,
        "capability": args.capability,
        "fileMask": args.file_mask,
        "isDefault": False,
        "definition": {
            "nodes": [
                {"id": "node-1", "type": "file-input", "name": "Fichier source"},
                {"id": "node-2", "type": "file-output", "name": "Fin du flux"},
            ],
            "connections": [{"from": "node-1", "to": "node-2"}],
        },
        "dependencies": [{"id": args.plugin_id, "versionRange": "^1.0.0", "kind": "plugin"}],
    }
    write_json(fdir / "manifest.json", manifest)
    (fdir / "README.md").write_text(f"# {args.name}\n\nFlow `{flow_id}`.\n", encoding="utf-8")
    _update_index(root)
    print(f"Flow créé : {fdir.relative_to(root)} ({flow_id})")


def cmd_pack(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    slug = _validate_slug(args.slug)
    ns = _validate_ns(args.namespace)
    pack_id = _slug_to_id(ns, "pack", slug)
    pdir = root / "packs" / slug
    if pdir.exists():
        raise SystemExit(f"Le dossier existe déjà : {pdir}")

    manifest = {
        "schemaVersion": "1.1.0",
        "id": pack_id,
        "type": "pack",
        "version": "1.0.0",
        "name": args.name,
        "description": f"Pack déclaratif {args.name}.",
        "author": args.author,
        "license": args.license,
        "files": [
            {"path": "README.md", "role": "docs", "mediaType": "text/markdown"},
            {"path": "installation.json", "role": "config", "mediaType": "application/json"},
        ],
        "pack": {
            "kind": "declarative-bundle",
            "installation": "installation.json",
            "runtimeImplemented": True,
        },
    }
    installation = {
        "schemaVersion": "1.0.0",
        "packId": pack_id,
        "packVersion": "1.0.0",
        "kind": "declarative-bundle",
        "components": [{"id": args.plugin_id, "version": "1.0.0", "kind": "plugin"}],
        "entrypoint": {"kind": "plugin", "id": args.plugin_id, "version": "1.0.0"},
        "permissions": {"readInputs": True, "writeOutputs": True, "network": "none"},
        "updates": "manual",
        "uninstallData": "preserve",
        "runtimeImplemented": True,
    }
    write_json(pdir / "manifest.json", manifest)
    write_json(pdir / "installation.json", installation)
    (pdir / "README.md").write_text(f"# {args.name}\n\nPack `{pack_id}`.\n", encoding="utf-8")
    _update_index(root)
    print(f"Pack créé : {pdir.relative_to(root)} ({pack_id})")


def cmd_resource(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    slug = _validate_slug(args.slug)
    ns = _validate_ns(args.namespace)
    res_type = args.resource_type
    if res_type == "preset":
        rdir = root / "presets" / slug
        prefix = "preset"
    else:
        sub = res_type.split(".", 1)[1]
        rdir = root / "resources" / sub / slug
        prefix = res_type
    res_id = _slug_to_id(ns, prefix, slug)
    if rdir.exists():
        raise SystemExit(f"Le dossier existe déjà : {rdir}")

    manifest = {
        "schemaVersion": "1.1.0",
        "id": res_id,
        "type": res_type,
        "version": "1.0.0",
        "name": args.name,
        "description": f"Ressource {res_type} : {args.name}.",
        "author": args.author,
        "license": args.license,
        "files": [{"path": "README.md", "role": "docs", "mediaType": "text/markdown"}],
    }
    write_json(rdir / "manifest.json", manifest)
    (rdir / "README.md").write_text(f"# {args.name}\n\nRessource `{res_id}` (`{res_type}`).\n", encoding="utf-8")
    _update_index(root)
    print(f"Ressource créée : {rdir.relative_to(root)} ({res_id})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assistant de création de pièces ou de dépôt Flux de Fichiers.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Racine du dépôt cible.")
    parser.add_argument("--namespace", type=str, default=None, help="Préfixe éditeur (recommandé pour tiers, ex. com.auteur).")
    parser.add_argument("--author", type=str, default="third-party", help="Auteur dans les manifestes.")
    parser.add_argument("--license", type=str, default="MIT", help="Licence SPDX.")

    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-repo", help="Initialise un dépôt tiers autonome.")
    p_init.add_argument("--name", default="mon-depot-plugins", help="Nom logique du dépôt (generatedFor).")
    p_init.add_argument("--with-example", action="store_true", help="Ajoute un plugin exemple complet.")
    p_init.set_defaults(func=cmd_init_repo)

    p_plugin = sub.add_parser("plugin", help="Crée un plugin avec un bloc et une opération.")
    p_plugin.add_argument("slug", help="Nom court du dossier (ex. mon-plugin).")
    p_plugin.add_argument("--name", required=True, help="Titre lisible.")
    p_plugin.add_argument("--kind", choices=["binary", "http"], default="http")
    p_plugin.add_argument("--tool-id", default="app.ffmpeg", help="ID de l'app requise si kind=binary.")
    p_plugin.add_argument("--executable", default="ffmpeg", help="Binaire exécuté si kind=binary.")
    p_plugin.set_defaults(func=cmd_plugin)

    p_app = sub.add_parser("app", help="Crée une application binaire Option B.")
    p_app.add_argument("slug", help="Nom court du dossier (ex. handbrake).")
    p_app.add_argument("--name", required=True, help="Titre lisible.")
    p_app.add_argument("--executable", required=True, help="Nom du binaire principal.")
    p_app.add_argument("--capability", default="other", help="Capacité déclarée (remux, probe, transcode…).")
    p_app.add_argument("--interface", default="CustomTool", help="Nom d'interface logique.")
    p_app.set_defaults(func=cmd_app)

    p_flow = sub.add_parser("flow", help="Crée un flow déclaratif.")
    p_flow.add_argument("slug", help="Nom court du dossier (ex. mon-flow).")
    p_flow.add_argument("--name", required=True, help="Titre lisible.")
    p_flow.add_argument("--plugin-id", default="plugin.core", help="Plugin requis par ce flow.")
    p_flow.add_argument("--capability", default="other", help="Capacité associée.")
    p_flow.add_argument("--file-mask", default="*.mkv, *.mp4", help="Masque de fichiers.")
    p_flow.set_defaults(func=cmd_flow)

    p_pack = sub.add_parser("pack", help="Crée un pack déclaratif.")
    p_pack.add_argument("slug", help="Nom court du dossier (ex. mon-pack).")
    p_pack.add_argument("--name", required=True, help="Titre lisible.")
    p_pack.add_argument("--plugin-id", default="plugin.core", help="Plugin principal du pack.")
    p_pack.set_defaults(func=cmd_pack)

    p_res = sub.add_parser("resource", help="Crée un élément « Autre » (preset ou resource.*).")
    p_res.add_argument("slug", help="Nom court du dossier.")
    p_res.add_argument("--name", required=True, help="Titre lisible.")
    p_res.add_argument(
        "--type",
        dest="resource_type",
        required=True,
        choices=[
            "preset",
            "resource.font",
            "resource.image",
            "resource.audio",
            "resource.subtitle",
            "resource.color",
            "resource.language",
            "resource.template",
        ],
    )
    p_res.set_defaults(func=cmd_resource)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
