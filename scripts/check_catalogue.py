#!/usr/bin/env python3
"""Contrôle structurel du catalogue (bibliothèque standard uniquement).

Vérifie l'index, les fichiers pointés, les propriétaires de blocs, les règles de
dépendance et les liens relatifs des documents. Ne remplace pas la validation par
JSON Schema, qui reste à brancher en CI.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []

# Types autorisés comme dépendance, par type de pièce (voir docs/distinctions-catalogue.md).
OTHER_TYPES = {"preset", "resource.font", "resource.image", "resource.audio",
               "resource.color", "resource.language", "resource.template"}
ALLOWED_DEPENDENCIES = {
    "plugin": {"app"},
    "flow": {"plugin"} | OTHER_TYPES,
    "pack": {"app", "plugin", "flow"} | OTHER_TYPES,
}


def fail(message: str) -> None:
    ERRORS.append(message)


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path.relative_to(ROOT)} : {error}")
        return None


def check_index(index_path: Path) -> None:
    index = load(index_path)
    if index is None:
        return
    entries = index["entries"]
    kinds = {entry["id"]: entry["type"] for entry in entries}
    for entry in entries:
        ident, kind = entry["id"], entry["type"]
        manifest_path = ROOT / entry["manifestPath"]
        if not manifest_path.is_file():
            fail(f"{ident} : fichier absent {entry['manifestPath']}")
            continue
        if kind == "block":
            owner = entry.get("owner")
            if kinds.get(owner) != "plugin":
                fail(f"{ident} : un bloc doit avoir un plugin propriétaire (owner={owner!r})")
            elif not entry["manifestPath"].startswith(f"plugins/{owner.split('.', 1)[1]}/"):
                fail(f"{ident} : le fichier du bloc doit être rangé sous son plugin {owner}")
            continue
        manifest = load(manifest_path)
        if manifest is None:
            continue
        for key in ("id", "type", "version", "name"):
            if manifest.get(key) != entry.get(key):
                fail(f"{ident} : {key} diffère entre l'index et le manifeste")
        for dep in manifest.get("dependencies", []):
            target = kinds.get(dep["id"])
            if target is None:
                fail(f"{ident} : dépendance inconnue {dep['id']}")
            elif target not in ALLOWED_DEPENDENCIES.get(kind, set()):
                fail(f"{ident} ({kind}) ne peut pas dépendre de {dep['id']} ({target})")
    listed = {entry["manifestPath"] for entry in entries}
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
    check_index(ROOT / "catalogue" / "index.json")
    check_markdown_links()
    for message in ERRORS:
        print(message)
    print(f"{len(ERRORS)} problème(s)")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
