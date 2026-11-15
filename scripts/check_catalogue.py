#!/usr/bin/env python3
"""Contrôle structurel et contractuel complet du catalogue (bibliothèque standard uniquement).

Vérifie :
- la validité syntaxique des schémas JSON (`schema/*.schema.json`) ;
- l'index (`catalogue/index.json`), l'unicité des identifiants et les manifestes ;
- la complétude des fichiers déclarés dans `files[]` et `pack.installation` ;
- la conformité des contrats `apps/*/distribution.v1.json` (formats, SHA-256, allowlist) ;
- la cohérence des blocs (`owner`, `operationId`, `ui.suggestedNext`) et des packs ;
- les liens relatifs dans la documentation Markdown.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []

OTHER_TYPES = {
    "preset",
    "resource.font",
    "resource.image",
    "resource.audio",
    "resource.color",
    "resource.language",
    "resource.template",
}
ALLOWED_TYPES = {"app", "plugin", "block", "flow", "pack"} | OTHER_TYPES
ALLOWED_DEPENDENCIES = {
    "plugin": {"app"},
    "flow": {"plugin"} | OTHER_TYPES,
    "pack": {"app", "plugin", "flow"} | OTHER_TYPES,
}
ID_RE = re.compile(r"^[a-z0-9]+([.-][a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
OCTAL_MODE_RE = re.compile(r"^0[0-7]{3}$")
OP_ID_RE = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
BINARY_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def fail(message: str) -> None:
    ERRORS.append(message)


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path.relative_to(ROOT)} : {error}")
        return None


def is_safe_relative(raw: object) -> bool:
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        return False
    parts = Path(raw).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def check_schemas() -> None:
    for schema in sorted((ROOT / "schema").glob("*.json")):
        load(schema)


def check_distribution(app_entry: dict, dist_path: Path) -> None:
    rel = dist_path.relative_to(ROOT).as_posix()
    dist = load(dist_path)
    if not isinstance(dist, dict):
        return
    if dist.get("schemaVersion") != "1.0.0":
        fail(f"{rel} : schemaVersion doit valoir '1.0.0'")
    if dist.get("toolId") != app_entry["id"]:
        fail(f"{rel} : toolId != {app_entry['id']}")
    if dist.get("toolVersion") != app_entry["version"]:
        fail(f"{rel} : toolVersion != {app_entry['version']}")
    if dist.get("distributionMode") != "autonomous-binary":
        fail(f"{rel} : distributionMode doit valoir 'autonomous-binary'")
    status = dist.get("releaseStatus")
    if status is not None and status not in {"contract-only", "candidate", "released"}:
        fail(f"{rel} : releaseStatus invalide ({status!r})")

    artifacts = dist.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        fail(f"{rel} : artifacts doit contenir au moins 1 entrée")
    else:
        for idx, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                fail(f"{rel} : artifact[{idx}] invalide")
                continue
            if artifact.get("arch") not in {"x86_64", "aarch64"}:
                fail(f"{rel} : artifact[{idx}].arch invalide")
            if artifact.get("os") != "linux":
                fail(f"{rel} : artifact[{idx}].os doit valoir 'linux'")
            url = artifact.get("archiveUrl", "")
            if not isinstance(url, str) or not url.startswith("https://"):
                fail(f"{rel} : artifact[{idx}].archiveUrl doit utiliser HTTPS")
            if artifact.get("archiveFormat") != "tar.gz":
                fail(f"{rel} : artifact[{idx}].archiveFormat doit valoir 'tar.gz'")
            if not SHA256_RE.match(str(artifact.get("archiveSha256", ""))):
                fail(f"{rel} : artifact[{idx}].archiveSha256 invalide")
            bin_rel = artifact.get("binaryRelativePath")
            if not is_safe_relative(bin_rel):
                fail(f"{rel} : artifact[{idx}].binaryRelativePath invalide ({bin_rel!r})")
            bin_sha = artifact.get("binarySha256")
            if bin_sha is not None and not SHA256_RE.match(str(bin_sha)):
                fail(f"{rel} : artifact[{idx}].binarySha256 invalide")
            perms = artifact.get("permissions")
            if isinstance(perms, dict):
                if not OCTAL_MODE_RE.match(str(perms.get("unixMode", ""))):
                    fail(f"{rel} : artifact[{idx}].permissions.unixMode invalide")
                if perms.get("owner") not in {"runtime-user", "root-forbidden"}:
                    fail(f"{rel} : artifact[{idx}].permissions.owner invalide")
                if perms.get("executableBit") is not True:
                    fail(f"{rel} : artifact[{idx}].permissions.executableBit doit valoir true")

    policy = dist.get("installPolicy")
    if not isinstance(policy, dict):
        fail(f"{rel} : installPolicy requis")
        return
    if policy.get("verifySha256BeforeExec") is not True:
        fail(f"{rel} : verifySha256BeforeExec doit valoir true")
    if policy.get("refuseMismatchedDigest") is not True:
        fail(f"{rel} : refuseMismatchedDigest doit valoir true")
    if policy.get("noShellUnpack") is not True:
        fail(f"{rel} : noShellUnpack doit valoir true")
    allowlist = policy.get("executableAllowlist")
    if not isinstance(allowlist, list) or not allowlist:
        fail(f"{rel} : executableAllowlist requis et non vide")
    else:
        for exe in allowlist:
            if not isinstance(exe, str) or not BINARY_NAME_RE.match(exe):
                fail(f"{rel} : nom exécutable invalide dans allowlist ({exe!r})")


def check_pack_installation(entry: dict, manifest: dict, manifest_path: Path, kinds: dict[str, str]) -> None:
    pack_meta = manifest.get("pack")
    if not isinstance(pack_meta, dict):
        fail(f"{entry['id']} : bloc 'pack' manquant dans {entry['manifestPath']}")
        return
    rel_install = pack_meta.get("installation")
    if not is_safe_relative(rel_install):
        fail(f"{entry['id']} : pack.installation invalide ({rel_install!r})")
        return
    install_path = manifest_path.parent / rel_install
    if not install_path.is_file():
        fail(f"{entry['id']} : fichier absent {install_path.relative_to(ROOT)}")
        return
    plan = load(install_path)
    if not isinstance(plan, dict):
        return
    rel = install_path.relative_to(ROOT).as_posix()
    if plan.get("schemaVersion") != "1.0.0":
        fail(f"{rel} : schemaVersion doit valoir '1.0.0'")
    if plan.get("packId") != entry["id"]:
        fail(f"{rel} : packId != {entry['id']}")
    if plan.get("packVersion") != entry["version"]:
        fail(f"{rel} : packVersion != {entry['version']}")
    if plan.get("kind") != "declarative-bundle":
        fail(f"{rel} : kind doit valoir 'declarative-bundle'")
    components = plan.get("components")
    if not isinstance(components, list) or not components:
        fail(f"{rel} : components doit être non vide")
    else:
        for idx, comp in enumerate(components):
            if not isinstance(comp, dict):
                fail(f"{rel} : component[{idx}] invalide")
                continue
            cid = comp.get("id")
            if cid not in kinds:
                fail(f"{rel} : composant inconnu dans l'index ({cid!r})")
            elif comp.get("kind") and kinds[cid] != comp.get("kind"):
                fail(f"{rel} : kind de {cid} différent de l'index ({comp.get('kind')} vs {kinds[cid]})")
            if not SEMVER_RE.match(str(comp.get("version", ""))):
                fail(f"{rel} : version semver invalide pour {cid!r}")
    entrypoint = plan.get("entrypoint")
    if not isinstance(entrypoint, dict) or not entrypoint.get("id") or not entrypoint.get("kind"):
        fail(f"{rel} : entrypoint incomplet")


def check_block(
    entry: dict,
    block_path: Path,
    kinds: dict[str, str],
    plugin_declared_files: dict[str, set[str]],
    plugin_declared_blocks: dict[str, set[str]],
) -> None:
    rel = block_path.relative_to(ROOT).as_posix()
    block = load(block_path)
    if not isinstance(block, dict):
        return
    for key in ("schemaVersion", "id", "version", "name", "description", "operationId"):
        if not block.get(key):
            fail(f"{rel} : champ requis manquant ({key})")
    if block.get("id") != entry["id"] or block.get("version") != entry["version"]:
        fail(f"{rel} : id/version incompatibles avec l'index")
    op_id = block.get("operationId")
    if op_id is not None and not (isinstance(op_id, str) and OP_ID_RE.match(op_id)):
        fail(f"{rel} : operationId invalide ({op_id!r})")
    owner = entry.get("owner")
    in_files = owner in plugin_declared_files and rel in plugin_declared_files[owner]
    in_blocks = owner in plugin_declared_blocks and entry["id"] in plugin_declared_blocks[owner]
    if owner in plugin_declared_files and not (in_files or in_blocks):
        fail(f"{rel} : bloc non déclaré dans files[] ni blocks[] du plugin propriétaire {owner}")
    ui = block.get("ui")
    if isinstance(ui, dict):
        suggested = ui.get("suggestedNext")
        if isinstance(suggested, list):
            for nxt in suggested:
                if nxt not in kinds:
                    fail(f"{rel} : suggestedNext référence un identifiant inconnu ({nxt!r})")


def check_index(index_path: Path) -> None:
    index = load(index_path)
    if not isinstance(index, dict):
        return
    if index.get("schemaVersion") != "1.0.0":
        fail("catalogue/index.json : schemaVersion doit valoir '1.0.0'")
    if not isinstance(index.get("generatedFor"), str) or not index["generatedFor"].strip():
        fail("catalogue/index.json : generatedFor manquant")

    entries = index.get("entries")
    if not isinstance(entries, list):
        fail("catalogue/index.json : entries doit être une liste")
        return

    seen_ids: set[str] = set()
    kinds: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("catalogue/index.json : entrée invalide")
            continue
        ident = entry.get("id")
        kind = entry.get("type")
        if not isinstance(ident, str) or not ID_RE.match(ident):
            fail(f"catalogue/index.json : identifiant invalide ({ident!r})")
            continue
        if ident in seen_ids:
            fail(f"catalogue/index.json : identifiant dupliqué {ident}")
        seen_ids.add(ident)
        if kind not in ALLOWED_TYPES:
            fail(f"{ident} : type inconnu {kind!r}")
        if not SEMVER_RE.match(str(entry.get("version", ""))):
            fail(f"{ident} : version semver invalide ({entry.get('version')!r})")
        kinds[ident] = kind

    plugin_declared_files: dict[str, set[str]] = {}
    plugin_declared_blocks: dict[str, set[str]] = {}
    block_entries: list[dict] = []

    for entry in entries:
        ident, kind = entry["id"], entry["type"]
        raw_manifest = entry.get("manifestPath")
        if not is_safe_relative(raw_manifest):
            fail(f"{ident} : manifestPath invalide ({raw_manifest!r})")
            continue
        manifest_path = ROOT / raw_manifest
        if not manifest_path.is_file():
            fail(f"{ident} : fichier absent {raw_manifest}")
            continue
        if kind == "block":
            owner = entry.get("owner")
            if kinds.get(owner) != "plugin":
                fail(f"{ident} : un bloc doit avoir un plugin propriétaire (owner={owner!r})")
            elif not raw_manifest.startswith(f"plugins/{owner.split('.', 1)[1]}/"):
                fail(f"{ident} : le fichier du bloc doit être rangé sous son plugin {owner}")
            block_entries.append(entry)
            continue

        manifest = load(manifest_path)
        if not isinstance(manifest, dict):
            continue
        for key in ("id", "type", "version", "name"):
            if manifest.get(key) != entry.get(key):
                fail(f"{ident} : {key} diffère entre l'index et le manifeste")
        required_meta = (
            ("description", "author", "license")
            if manifest.get("schemaVersion") == "1.1.0"
            else ("description",)
        )
        for field in required_meta:
            if not isinstance(manifest.get(field), str) or not manifest[field].strip():
                fail(f"{raw_manifest} : champ requis manquant ({field})")

        declared_paths: set[str] = set()
        for item in manifest.get("files", []):
            if not isinstance(item, dict) or not is_safe_relative(item.get("path")):
                fail(f"{raw_manifest} : entrée files[] invalide ({item!r})")
                continue
            target = (manifest_path.parent / item["path"]).resolve()
            if not target.is_file():
                fail(f"{raw_manifest} : fichier déclaré absent ({item['path']})")
            else:
                declared_paths.add(target.relative_to(ROOT).as_posix())
        if kind == "plugin":
            plugin_declared_files[ident] = declared_paths
            plugin_declared_blocks[ident] = {
                b["id"]
                for b in manifest.get("blocks", [])
                if isinstance(b, dict) and isinstance(b.get("id"), str)
            }

        for dep in manifest.get("dependencies", []):
            target = kinds.get(dep.get("id"))
            if target is None:
                fail(f"{ident} : dépendance inconnue {dep.get('id')}")
            elif target not in ALLOWED_DEPENDENCIES.get(kind, set()):
                fail(f"{ident} ({kind}) ne peut pas dépendre de {dep['id']} ({target})")

        if kind == "app":
            dist_path = manifest_path.parent / "distribution.v1.json"
            invocation = (manifest.get("tool") or {}).get("invocation")
            expects_dist = (
                entry.get("distribution") == "autonomous-binary"
                or invocation == "binary"
                or dist_path.is_file()
            )
            if expects_dist and not dist_path.is_file():
                fail(f"{ident} : distribution.v1.json absent")
            elif dist_path.is_file():
                check_distribution(entry, dist_path)
        elif kind == "pack":
            check_pack_installation(entry, manifest, manifest_path, kinds)

    for block_entry in block_entries:
        check_block(
            block_entry,
            ROOT / block_entry["manifestPath"],
            kinds,
            plugin_declared_files,
            plugin_declared_blocks,
        )

    listed = {entry.get("manifestPath") for entry in entries}
    for manifest in ROOT.glob("*/**/manifest.json"):
        relative = manifest.relative_to(ROOT).as_posix()
        if not relative.startswith(("examples/", "schema/")) and relative not in listed:
            fail(f"{relative} : manifeste absent de l'index")


def check_markdown_links() -> None:
    link = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
    for doc in ROOT.rglob("*.md"):
        if ".git" in doc.parts:
            continue
        for target in link.findall(doc.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (doc.parent / target).exists():
                fail(f"{doc.relative_to(ROOT)} : lien cassé {target}")


def main() -> int:
    check_schemas()
    check_index(ROOT / "catalogue" / "index.json")
    check_markdown_links()
    for message in ERRORS:
        print(message)
    print(f"{len(ERRORS)} problème(s)")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
