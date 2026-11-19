#!/usr/bin/env python3
"""Tests unitaires et d'intégration des outils du catalogue (bibliothèque standard)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_index  # noqa: E402
import check_catalogue  # noqa: E402
import scaffold  # noqa: E402


class CatalogueToolsTests(unittest.TestCase):
    def test_official_repo_and_template_pass_validation(self) -> None:
        self.assertEqual(build_index.main(["--root", str(REPO_ROOT), "--check"]), 0)
        self.assertEqual(check_catalogue.main(["--root", str(REPO_ROOT)]), 0)

    def test_third_party_repo_scaffold_and_external_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            third_party = Path(tmp) / "alice-plugins"
            rc = scaffold.main(
                [
                    "--root",
                    str(third_party),
                    "--namespace",
                    "com.alice",
                    "--author",
                    "alice",
                    "--license",
                    "MIT",
                    "init-repo",
                    "--name",
                    "Alice Plugins",
                    "--with-example",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "plugin",
                        "transcode-lite",
                        "--name",
                        "Transcode Lite",
                        "--kind",
                        "binary",
                        "--tool-id",
                        "ffmpeg",
                        "--executable",
                        "ffmpeg",
                    ]
                ),
                0,
            )
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "app",
                        "handbrake",
                        "--name",
                        "HandBrakeCLI",
                        "--executable",
                        "HandBrakeCLI",
                        "--capability",
                        "transcode",
                    ]
                ),
                0,
            )
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "flow",
                        "encode-hevc",
                        "--name",
                        "Encode HEVC",
                        "--plugin-id",
                        "com.alice.transcode-lite",
                    ]
                ),
                0,
            )
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "pack",
                        "suite-alice",
                        "--name",
                        "Suite Alice",
                        "--plugin-id",
                        "com.alice.transcode-lite",
                    ]
                ),
                0,
            )
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "resource",
                        "lut-rec709",
                        "--name",
                        "LUT Rec709",
                        "--type",
                        "resource.color",
                    ]
                ),
                0,
            )
            self.assertEqual(
                scaffold.main(
                    [
                        "--root",
                        str(third_party),
                        "--namespace",
                        "com.alice",
                        "script",
                        "tag-mkv",
                        "--name",
                        "Tag MKV",
                        "--interpreter",
                        "python3",
                    ]
                ),
                0,
            )
            idx_after = json.loads((third_party / "index.json").read_text(encoding="utf-8"))
            self.assertIn("scripts/tag-mkv/run.py", idx_after["filesSha256"])

            self.assertEqual(build_index.main(["--root", str(third_party), "--check"]), 0)
            self.assertEqual(
                check_catalogue.main(
                    [
                        "--root",
                        str(third_party),
                        "--schema-dir",
                        str(REPO_ROOT / "schema"),
                        "--external-index",
                        str(REPO_ROOT / "index.json"),
                    ]
                ),
                0,
            )
            self.assertEqual(
                check_catalogue.main(
                    [
                        "--root",
                        str(third_party),
                        "--schema-dir",
                        str(REPO_ROOT / "schema"),
                        "--allow-external-refs",
                    ]
                ),
                0,
            )

    def test_detects_tampered_sha256_unknown_property_and_default_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "bad-repo"
            scaffold.main(
                [
                    "--root",
                    str(repo),
                    "--namespace",
                    "com.bob",
                    "init-repo",
                    "--name",
                    "Bob",
                    "--with-example",
                ]
            )
            scaffold.main(
                [
                    "--root",
                    str(repo),
                    "--namespace",
                    "com.bob",
                    "plugin",
                    "demo",
                    "--name",
                    "Demo",
                    "--kind",
                    "binary",
                    "--tool-id",
                    "ffmpeg",
                    "--executable",
                    "ffmpeg",
                ]
            )

            # 1. Empreinte SHA-256 falsifiée dans index.json
            idx_path = repo / "index.json"
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
            idx["entries"][0]["sha256"] = "0" * 64
            idx_path.write_text(json.dumps(idx), encoding="utf-8")
            checker = check_catalogue.CatalogueChecker(
                repo, REPO_ROOT / "schema", [REPO_ROOT / "index.json"], False, False
            )
            errs = checker.run()
            self.assertTrue(any("sha256 périmé" in e for e in errs), errs)

            # 2. Propriété inconnue rejetée par le schéma + défaut divergent bloc/opération
            build_index.main(["--root", str(repo)])
            block_path = repo / "plugins" / "demo" / "blocks" / "demo.json"
            block = json.loads(block_path.read_text(encoding="utf-8"))
            block["unexpectedKey"] = True
            block["ui"]["fields"][0]["default"] = "autre"
            block_path.write_text(json.dumps(block), encoding="utf-8")
            build_index.main(["--root", str(repo)])

            checker2 = check_catalogue.CatalogueChecker(
                repo, REPO_ROOT / "schema", [REPO_ROOT / "index.json"], False, False
            )
            errs2 = checker2.run()
            self.assertTrue(any("unexpectedKey" in e for e in errs2), errs2)
            self.assertTrue(any("défaut divergent" in e for e in errs2), errs2)


            # 3. filesSha256 falsifié sur fichier secondaire + contrôle strict-immutable
            del block["unexpectedKey"]
            block["ui"]["fields"][0]["default"] = ""
            block_path.write_text(json.dumps(block), encoding="utf-8")
            build_index.main(["--root", str(repo)])

            op_path = repo / "plugins" / "demo" / "operations" / "demo.json"
            op = json.loads(op_path.read_text(encoding="utf-8"))
            op["name"] = "Modifié sans recalcul"
            op_path.write_text(json.dumps(op), encoding="utf-8")
            checker3 = check_catalogue.CatalogueChecker(
                repo, REPO_ROOT / "schema", [REPO_ROOT / "index.json"], False, False
            )
            errs3 = checker3.run()
            self.assertTrue(any("filesSha256" in e for e in errs3), errs3)

            build_index.main(["--root", str(repo), "--release-version", "1.0.0"])
            checker_strict = check_catalogue.CatalogueChecker(
                repo,
                REPO_ROOT / "schema",
                [REPO_ROOT / "index.json"],
                False,
                False,
                strict_immutable=True,
            )
            self.assertEqual(checker_strict.run(), [])

            # Vérifie que --strict-immutable refuse une archiveUrl sur branche mouvante
            scaffold.main(
                [
                    "--root",
                    str(repo),
                    "--namespace",
                    "com.bob",
                    "app",
                    "tool",
                    "--name",
                    "Tool",
                    "--executable",
                    "tool",
                ]
            )
            dist_path = repo / "apps" / "tool" / "distribution.v1.json"
            dist = json.loads(dist_path.read_text(encoding="utf-8"))
            dist["releaseStatus"] = "released"
            dist["artifacts"][0]["archiveUrl"] = "https://github.com/bob/repo/raw/dev/tool.tar.gz"
            dist_path.write_text(json.dumps(dist), encoding="utf-8")
            build_index.main(["--root", str(repo), "--release-version", "1.0.1"])
            checker_mutable = check_catalogue.CatalogueChecker(
                repo,
                REPO_ROOT / "schema",
                [REPO_ROOT / "index.json"],
                False,
                False,
                strict_immutable=True,
            )
            errs_mutable = checker_mutable.run()
            self.assertTrue(any("archiveUrl non immuable" in e for e in errs_mutable), errs_mutable)

    def test_updated_at_follows_content_changes_only(self) -> None:
        day_one, day_two = "1767225600", "1767312000"  # 2026-01-01 et 2026-01-02 (UTC)
        previous = os.environ.get("SOURCE_DATE_EPOCH")
        self.addCleanup(
            lambda: os.environ.pop("SOURCE_DATE_EPOCH", None)
            if previous is None
            else os.environ.__setitem__("SOURCE_DATE_EPOCH", previous)
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "depot"

            def regenerate(epoch: str) -> dict:
                os.environ["SOURCE_DATE_EPOCH"] = epoch
                self.assertEqual(build_index.main(["--root", str(repo)]), 0)
                entries = json.loads((repo / "index.json").read_text(encoding="utf-8"))["entries"]
                return {entry["id"]: entry for entry in entries}

            os.environ["SOURCE_DATE_EPOCH"] = day_one
            scaffold.main(["--root", str(repo), "--namespace", "org.test", "init-repo"])
            scaffold.main(["--root", str(repo), "--namespace", "org.test", "plugin", "demo", "--name", "Démo"])
            first = regenerate(day_one)
            self.assertEqual(first["org.test.demo"]["updatedAt"], "2026-01-01")
            self.assertEqual(build_index.main(["--root", str(repo), "--check"]), 0)

            unchanged = regenerate(day_two)
            self.assertEqual(unchanged["org.test.demo"]["updatedAt"], "2026-01-01")

            readme = repo / "plugins" / "demo" / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nNote.\n", encoding="utf-8")
            changed = regenerate(day_two)
            self.assertEqual(changed["org.test.demo"]["updatedAt"], "2026-01-02")
            self.assertEqual(changed["org.test.demo.demo"]["updatedAt"], "2026-01-01")
            self.assertNotEqual(changed["org.test.demo"]["contentSha256"], first["org.test.demo"]["contentSha256"])

if __name__ == "__main__":
    unittest.main()
