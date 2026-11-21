#!/usr/bin/env python3
"""Calcule la prochaine version du catalogue officiel pour la release automatique.

Après chaque fusion dans `main`, `auto-release.yml` appelle ce script. Il lit les tags
`catalogue-vX.Y.Z` et les commits depuis le dernier, puis imprime la version à publier, ou rien
si aucune release n'est utile :

- le catalogue (`plugins/`, `apps/`, `flows/`, `packs/`, `schema/`, `index.json`) n'a pas changé
  depuis la dernière release : une release est immuable, on n'en crée pas pour de la documentation ;
- le commit courant porte déjà un tag de release.

Version (commits conventionnels qui modifient le catalogue, hors commits de fusion) : `feat` = mineure, `fix` et le reste =
correctif, `!` après le type ou `BREAKING CHANGE` dans le corps = majeure ; la plus haute gagne.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from enum import IntEnum
from pathlib import Path

TAG_PREFIX = "catalogue-v"
TAG_RE = re.compile(r"^catalogue-v(\d+)\.(\d+)\.(\d+)$")
CATALOGUE_PATHS = ("plugins/", "apps/", "flows/", "packs/", "schema/", "index.json")
SUBJECT_RE = re.compile(r"^(?P<type>[A-Za-z]+)(?:\([^)]*\))?(?P<breaking>!)?:")
BREAKING_MARKER = "BREAKING CHANGE"
FIRST_VERSION = "1.0.0"
FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"

Version = tuple[int, int, int]


class Bump(IntEnum):
    PATCH = 1
    MINOR = 2
    MAJOR = 3


def latest_version(tags: list[str]) -> Version | None:
    """Plus haute version SemVer parmi les tags `catalogue-vX.Y.Z` (les autres tags sont ignorés)."""
    versions = [tuple(int(part) for part in match.groups()) for tag in tags if (match := TAG_RE.match(tag))]
    return max(versions) if versions else None


def classify(subject: str, body: str) -> Bump:
    """Niveau de version d'un commit conventionnel."""
    match = SUBJECT_RE.match(subject)
    if BREAKING_MARKER in body or (match and match.group("breaking")):
        return Bump.MAJOR
    if match and match.group("type").lower() == "feat":
        return Bump.MINOR
    return Bump.PATCH


def bump_for(commits: list[tuple[str, str]]) -> Bump:
    """Niveau le plus haut parmi des commits `(sujet, corps)` ; un correctif si la liste est vide."""
    return max((classify(subject, body) for subject, body in commits), default=Bump.PATCH)


def next_version(last: Version, bump: Bump) -> str:
    major, minor, patch = last
    if bump is Bump.MAJOR:
        return f"{major + 1}.0.0"
    if bump is Bump.MINOR:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def touches_catalogue(paths: list[str]) -> bool:
    return any(path == "index.json" or path.startswith(CATALOGUE_PATHS[:-1]) for path in paths)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout


def plan(root: Path) -> tuple[str | None, str]:
    """`(version, explication)` ; la version est `None` quand aucune release n'est utile."""
    tags = git(root, "tag", "--list", f"{TAG_PREFIX}*").split()
    if any(tag in tags for tag in git(root, "tag", "--points-at", "HEAD").split()):
        return None, "ce commit porte déjà un tag de release"
    last = latest_version(tags)
    if last is None:
        return FIRST_VERSION, "aucune release précédente"
    last_tag = f"{TAG_PREFIX}{last[0]}.{last[1]}.{last[2]}"
    changed = git(root, "diff", "--name-only", last_tag, "HEAD").split("\n")
    if not touches_catalogue([path for path in changed if path]):
        return None, f"le catalogue n'a pas changé depuis {last_tag}"
    log = git(
        root,
        "log",
        f"{last_tag}..HEAD",
        "--no-merges",
        f"--format=%s{FIELD_SEPARATOR}%b{RECORD_SEPARATOR}",
        "--",
        *CATALOGUE_PATHS,
    )
    commits = [
        tuple(record.strip("\n").split(FIELD_SEPARATOR, 1))
        for record in log.split(RECORD_SEPARATOR)
        if record.strip()
    ]
    bump = bump_for([(subject, body) for subject, body in commits])
    return next_version(last, bump), f"{len(commits)} commit(s) depuis {last_tag} : niveau {bump.name.lower()}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--github-output", type=Path, help="Fichier GITHUB_OUTPUT où écrire `version=…`.")
    args = parser.parse_args(argv)
    version, reason = plan(args.root)
    print(f"{'Release ' + version if version else 'Aucune release'} : {reason}", file=sys.stderr)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"version={version or ''}\n")
    elif version:
        print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
