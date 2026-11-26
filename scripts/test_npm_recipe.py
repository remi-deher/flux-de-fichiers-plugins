#!/usr/bin/env python3
"""Tests du verrou npm et de la recette `npmPackages` de l'application `langages` (bibliothèque standard)."""
import copy
import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import catalogue_lib  # noqa: E402
import check_catalogue  # noqa: E402

VALID_INTEGRITY = "sha512-" + "A" * 86 + "=="
REGISTRY_URL = "https://registry.npmjs.org/paquet/-/paquet-1.0.0.tgz"


def lockfile(**entry: object) -> dict:
    package = {"version": "1.0.0", "resolved": REGISTRY_URL, "integrity": VALID_INTEGRITY}
    package.update(entry)
    return {"lockfileVersion": 3, "packages": {"": {"name": "racine"}, "node_modules/paquet": package}}


class NpmLockfileTests(unittest.TestCase):
    def test_a_complete_lockfile_has_no_problem(self) -> None:
        self.assertEqual(catalogue_lib.npm_lockfile_problems(lockfile()), [])

    def test_the_committed_lockfile_is_valid(self) -> None:
        lock = catalogue_lib.load_json(REPO_ROOT / "apps/langages/npm/package-lock.json")
        self.assertEqual(catalogue_lib.npm_lockfile_problems(lock), [])

    def test_a_package_without_integrity_is_refused(self) -> None:
        problems = catalogue_lib.npm_lockfile_problems(lockfile(integrity="sha1-abc"))
        self.assertTrue(any("empreinte sha512" in problem for problem in problems))

    def test_a_package_outside_the_npm_registry_is_refused(self) -> None:
        problems = catalogue_lib.npm_lockfile_problems(lockfile(resolved="https://example.test/paquet.tgz"))
        self.assertTrue(any("registre npm" in problem for problem in problems))

    def test_a_local_link_is_refused(self) -> None:
        problems = catalogue_lib.npm_lockfile_problems(lockfile(link=True))
        self.assertTrue(any("registre npm" in problem for problem in problems))

    def test_an_old_format_or_an_empty_lockfile_is_refused(self) -> None:
        self.assertTrue(catalogue_lib.npm_lockfile_problems({"lockfileVersion": 2, "packages": {"": {}}}))
        self.assertTrue(catalogue_lib.npm_lockfile_problems([]))


class NpmRecipeTests(unittest.TestCase):
    def failures(self, recipe: dict) -> list[str]:
        checker = check_catalogue.CatalogueChecker(
            REPO_ROOT, REPO_ROOT / "schema", [], allow_external_refs=False, require_jsonschema=False
        )
        checker._check_npm_packages("apps/langages/build.json", recipe)
        return checker.errors

    def recipe(self) -> dict:
        return copy.deepcopy(json.loads((REPO_ROOT / "apps/langages/build.json").read_text(encoding="utf-8")))

    def test_the_langages_recipe_is_consistent(self) -> None:
        self.assertEqual(self.failures(self.recipe()), [])

    def test_the_runtime_must_provide_node(self) -> None:
        recipe = self.recipe()
        recipe["source"]["npmPackages"]["runtime"] = "ty-runtime"
        self.assertTrue(any("npmPackages.runtime" in error for error in self.failures(recipe)))

    def test_every_entrypoint_must_be_declared_as_a_binary(self) -> None:
        recipe = self.recipe()
        recipe["binaries"].remove("bash-language-server")
        self.assertTrue(any("binaires exposés" in error for error in self.failures(recipe)))

    def test_a_missing_lockfile_is_reported(self) -> None:
        recipe = self.recipe()
        recipe["source"]["npmPackages"]["projectDir"] = "apps/langages/absent"
        self.assertTrue(any("package-lock.json attendus" in error for error in self.failures(recipe)))


if __name__ == "__main__":
    unittest.main()
