#!/usr/bin/env python3
"""Tests du calcul de version de la release automatique (bibliothèque standard)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import plan_release  # noqa: E402
from plan_release import Bump  # noqa: E402


class FakeRepo:
    """Dépôt Git temporaire pour exercer `plan` de bout en bout."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        identity = ["-c", "user.name=Test", "-c", "user.email=test@example.test", "-c", "commit.gpgsign=false"]
        result = subprocess.run(["git", *identity, *args], cwd=self.root, check=True, capture_output=True, text=True)
        return result.stdout

    def commit(self, path: str, message: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(target.read_text() + "x\n" if target.exists() else "x\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def tag(self, name: str) -> None:
        self.git("tag", name)


class PlanReleaseTests(unittest.TestCase):
    def test_latest_version_compares_numbers_and_ignores_other_tags(self) -> None:
        tags = ["catalogue-v3.1.0", "catalogue-v3.10.0", "catalogue-v3.9.9", "tools-ffmpeg-7.1.0", "v9.9.9"]
        self.assertEqual(plan_release.latest_version(tags), (3, 10, 0))
        self.assertIsNone(plan_release.latest_version(["tools-ffmpeg-7.1.0"]))
        self.assertIsNone(plan_release.latest_version([]))

    def test_conventional_commits_map_to_bump_levels(self) -> None:
        classify = plan_release.classify
        self.assertEqual(classify("feat(catalogue): icônes", ""), Bump.MINOR)
        self.assertEqual(classify("feat: ajouter", ""), Bump.MINOR)
        self.assertEqual(classify("fix(schema): corriger", ""), Bump.PATCH)
        self.assertEqual(classify("chore: dev → main", ""), Bump.PATCH)
        self.assertEqual(classify("sans type conventionnel", ""), Bump.PATCH)
        self.assertEqual(classify("feat!: renommer les ids", ""), Bump.MAJOR)
        self.assertEqual(classify("refactor(api)!: retirer", ""), Bump.MAJOR)
        self.assertEqual(classify("fix: x", "BREAKING CHANGE: ids renommés"), Bump.MAJOR)

    def test_highest_bump_wins_and_an_empty_list_is_a_patch(self) -> None:
        commits = [("fix: a", ""), ("feat: b", ""), ("chore: c", "")]
        self.assertEqual(plan_release.bump_for(commits), Bump.MINOR)
        self.assertEqual(plan_release.bump_for(commits + [("feat!: d", "")]), Bump.MAJOR)
        self.assertEqual(plan_release.bump_for([]), Bump.PATCH)

    def test_next_version_resets_lower_numbers(self) -> None:
        self.assertEqual(plan_release.next_version((3, 4, 7), Bump.PATCH), "3.4.8")
        self.assertEqual(plan_release.next_version((3, 4, 7), Bump.MINOR), "3.5.0")
        self.assertEqual(plan_release.next_version((3, 4, 7), Bump.MAJOR), "4.0.0")

    def test_only_catalogue_paths_justify_a_release(self) -> None:
        for path in ("plugins/plex/manifest.json", "apps/ffmpeg/distribution.v1.json", "flows/a/manifest.json",
                     "packs/p/installation.json", "schema/common.v1.schema.json", "index.json"):
            self.assertTrue(plan_release.touches_catalogue([path]), path)
        for path in ("docs/a.md", "scripts/build_index.py", "README.md", ".github/workflows/x.yml",
                     "templates/depot-tiers/a.json", "pluginsx/a.json"):
            self.assertFalse(plan_release.touches_catalogue([path]), path)

    def test_plan_follows_commits_since_the_last_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(Path(tmp))
            repo.commit("plugins/a/manifest.json", "feat: premier plugin")
            self.assertEqual(plan_release.plan(repo.root)[0], plan_release.FIRST_VERSION)
            repo.tag("catalogue-v3.4.0")

            self.assertEqual(plan_release.plan(repo.root)[0], None)  # le tag est sur HEAD

            repo.commit("docs/guide.md", "feat: documenter")
            version, reason = plan_release.plan(repo.root)
            self.assertIsNone(version, reason)  # rien du catalogue n'a changé

            repo.commit("plugins/a/manifest.json", "fix: corriger un champ")
            self.assertEqual(plan_release.plan(repo.root)[0], "3.4.1")

            repo.commit("plugins/b/manifest.json", "feat(catalogue): nouveau plugin")
            self.assertEqual(plan_release.plan(repo.root)[0], "3.5.0")

            repo.commit("schema/common.v1.schema.json", "feat!: schéma incompatible")
            self.assertEqual(plan_release.plan(repo.root)[0], "4.0.0")

    def test_merge_commits_are_ignored_and_branch_commits_are_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(Path(tmp))
            repo.commit("plugins/a/manifest.json", "feat: base")
            repo.tag("catalogue-v1.0.0")
            repo.git("checkout", "-q", "-b", "travail")
            repo.commit("plugins/a/manifest.json", "feat(catalogue): icônes")
            repo.git("checkout", "-q", "main")
            repo.git("merge", "--no-ff", "-q", "-m", "chore: dev → main", "travail")
            version, reason = plan_release.plan(repo.root)
            self.assertEqual(version, "1.1.0", reason)

    def test_main_writes_the_github_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(Path(tmp))
            repo.commit("plugins/a/manifest.json", "feat: base")
            repo.tag("catalogue-v2.0.0")
            output = Path(tmp) / "github_output"
            self.assertEqual(plan_release.main(["--root", str(repo.root), "--github-output", str(output)]), 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "version=\n")
            repo.commit("plugins/a/manifest.json", "fix: corriger")
            plan_release.main(["--root", str(repo.root), "--github-output", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "version=\nversion=2.0.1\n")


if __name__ == "__main__":
    unittest.main()
