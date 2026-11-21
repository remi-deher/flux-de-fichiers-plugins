#!/usr/bin/env python3
"""Variables exposées par les plugins : requêtes de chemin, règles du central et contrôles du catalogue.

Les vecteurs de validation reprennent ceux de `shared/src/exposed_variables.rs` (Forgearr) : le
central revalide à la synchronisation, les deux implémentations doivent donc accepter et refuser
les mêmes déclarations.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import catalogue_lib as lib  # noqa: E402
import check_catalogue  # noqa: E402

OPERATION_REL = "plugins/video/operations/media-inspect.json"
FIXTURE_REL = "plugins/video/fixtures/media-inspect.json"


def exposed(name: str, path: str = "x", kind: str = "text") -> dict:
    return {"name": name, "path": path, "type": kind}


def mediainfo(variables: list[dict] | None = None, version: str = "1.0.0") -> dict:
    default = [exposed("video.codec", "mediainfo.media.track[@type=Video].Format")]
    return {
        "namespace": "mediainfo",
        "contractVersion": version,
        "variables": default if variables is None else variables,
    }


def requirement(variable: str, provider: str = "app.mediainfo") -> dict:
    return {"variable": variable, "provider": provider}


class QueryTests(unittest.TestCase):
    DOC = {
        "media": {
            "track": [
                {"@type": "General", "Format": "Matroska", "Count": 3, "Flag": True},
                {"@type": "Video", "Format": "HEVC", "Width": "1920"},
                {"@type": "Audio", "Format": "AAC", "Language": None},
            ]
        }
    }

    def test_dotted_index_wildcard_and_filter_queries(self) -> None:
        self.assertEqual(lib.query_values(self.DOC, "media.track[0].Format"), ["Matroska"])
        self.assertEqual(lib.query_values(self.DOC, "media.track[*].Format"), ["Matroska", "HEVC", "AAC"])
        self.assertEqual(lib.query_values(self.DOC, "media.track[@type=Video].Format"), ["HEVC"])
        self.assertEqual(lib.query_values(self.DOC, "media.track[@type=video].Width"), ["1920"])

    def test_filters_match_numbers_and_booleans(self) -> None:
        self.assertEqual(lib.query_values(self.DOC, "media.track[Count=3].Format"), ["Matroska"])
        self.assertEqual(lib.query_values(self.DOC, "media.track[Flag=true].Format"), ["Matroska"])

    def test_missing_paths_give_nothing_and_first_value_skips_nulls(self) -> None:
        self.assertEqual(lib.query_values(self.DOC, "media.absent.x"), [])
        self.assertEqual(lib.query_values(self.DOC, "media.track[9].Format"), [])
        self.assertEqual(lib.query_values(self.DOC, "media.track[@type=Text].Format"), [])
        self.assertIsNone(lib.first_value(self.DOC, "media.track[@type=Audio].Language"))
        self.assertEqual(lib.first_value(self.DOC, "media.track[*].Language"), None)
        self.assertEqual(lib.first_value(self.DOC, "media.track[*].Width"), "1920")


class ExposesProblemsTests(unittest.TestCase):
    def test_a_valid_exposure_is_accepted(self) -> None:
        self.assertEqual(lib.exposes_problems(mediainfo()), [])
        paths = ["a.b", "a[0].b", "a[*]", "streams.0.Codec-ID", "media.track[@type=General].Format", "t[k=un deux]"]
        for path in paths:
            self.assertEqual(lib.exposes_problems(mediainfo([exposed("v", path)])), [], path)

    def test_namespace_and_version_vectors(self) -> None:
        for bad in ["", "MediaInfo", "1media", "media-info", "media.info"]:
            exposure = mediainfo()
            exposure["namespace"] = bad
            self.assertTrue(lib.exposes_problems(exposure), bad)
        reserved = mediainfo()
        reserved["namespace"] = "nodes"
        self.assertIn("réservé", lib.exposes_problems(reserved)[0])
        for bad in ["", "1", "1.0", "1.0.0.0", "a.b.c", "1.0.x"]:
            exposure = mediainfo()
            exposure["contractVersion"] = bad
            self.assertTrue(lib.exposes_problems(exposure), bad)

    def test_name_path_and_kind_vectors(self) -> None:
        for name in ["Video.Codec", "", "a..b", "1a"]:
            self.assertTrue(lib.exposes_problems(mediainfo([exposed(name)])), name)
        for path in ["video..codec", "video codec", "", "a[", "a[=x]", "a[0", "a[x y]"]:
            self.assertTrue(lib.exposes_problems(mediainfo([exposed("v", path)])), path)
        self.assertTrue(lib.exposes_problems(mediainfo([exposed("v", "x", "secret")])))

    def test_duplicates_and_value_group_conflicts_vectors(self) -> None:
        duplicate = mediainfo([exposed("video.codec"), exposed("video.codec")])
        self.assertIn("deux fois", lib.exposes_problems(duplicate)[0])
        for other in ["video", "video.codec.id"]:
            nested = mediainfo([exposed("video.codec"), exposed(other)])
            self.assertTrue(any("groupe" in p for p in lib.exposes_problems(nested)), other)
        siblings = mediainfo([exposed("video.codec"), exposed("video.codecs")])
        self.assertEqual(lib.exposes_problems(siblings), [])

    def test_the_variable_count_is_capped(self) -> None:
        many = mediainfo([exposed(f"v{n}") for n in range(lib.MAX_EXPOSED_VARIABLES + 1)])
        self.assertTrue(lib.exposes_problems(many))


class RequirementsProblemsTests(unittest.TestCase):
    def test_valid_requirements_are_accepted(self) -> None:
        self.assertEqual(lib.requirements_problems([requirement("mediainfo.video.codec")]), [])
        with_repo = requirement("a.b")
        with_repo["repository"] = {"id": "repo.tiers", "indexUrl": "https://exemple.org/p/index.json"}
        self.assertEqual(lib.requirements_problems([with_repo]), [])

    def test_reference_provider_and_repository_vectors(self) -> None:
        for bad in ["codec", "Mediainfo.codec", "media info.codec", ""]:
            self.assertTrue(lib.requirements_problems([requirement(bad)]), bad)
        self.assertTrue(lib.requirements_problems([requirement("a.b"), requirement("a.b")]))
        self.assertTrue(lib.requirements_problems([requirement("a.b", "../x")]))
        for repo_id, url in [
            ("../x", "https://exemple.org/index.json"),
            ("repo", "ftp://exemple.org/index.json"),
            ("repo", "https://exemple.org/autre.json"),
            ("repo", "https://exemple.org/a b/index.json"),
        ]:
            bad_repo = requirement("a.b")
            bad_repo["repository"] = {"id": repo_id, "indexUrl": url}
            self.assertTrue(lib.requirements_problems([bad_repo]), (repo_id, url))

    def test_the_requirement_count_is_capped(self) -> None:
        many = [requirement(f"ns.v{n}") for n in range(lib.MAX_REQUIREMENTS + 1)]
        self.assertTrue(lib.requirements_problems(many))


class BreakingChangesTests(unittest.TestCase):
    def test_removed_renamed_or_retyped_variables_and_namespace_are_breaking(self) -> None:
        old = mediainfo([exposed("video.codec"), exposed("video.width", kind="number")])
        self.assertEqual(lib.exposes_breaking_changes(old, old), [])
        added = mediainfo(old["variables"] + [exposed("audio.codec")])
        self.assertEqual(lib.exposes_breaking_changes(old, added), [])
        removed = mediainfo([exposed("video.codec")])
        self.assertTrue(any("retirée" in c for c in lib.exposes_breaking_changes(old, removed)))
        retyped = mediainfo([exposed("video.codec"), exposed("video.width", kind="text")])
        self.assertTrue(any("type" in c for c in lib.exposes_breaking_changes(old, retyped)))
        renamed = dict(old, namespace="autre")
        self.assertTrue(any("espace de noms" in c for c in lib.exposes_breaking_changes(old, renamed)))

    def test_a_path_change_alone_is_not_breaking(self) -> None:
        old = mediainfo([exposed("video.codec", "a.b")])
        new = mediainfo([exposed("video.codec", "c.d")])
        self.assertEqual(lib.exposes_breaking_changes(old, new), [])


class CatalogueChecksTests(unittest.TestCase):
    """Contrôles de `check_catalogue` sur une copie du dépôt (fixture, clé d'enrichissement, version)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "catalogue"
        shutil.copytree(REPO_ROOT, self.root, ignore=shutil.ignore_patterns(".git"))
        self.addCleanup(os.environ.pop, check_catalogue.BASE_REF_ENV, None)

    def errors(self) -> list[str]:
        checker = check_catalogue.CatalogueChecker(
            root=self.root,
            schema_dir=self.root / "schema",
            external_indexes=[],
            allow_external_refs=False,
            require_jsonschema=False,
            strict_immutable=False,
        )
        return [e for e in checker.run() if "exposes" in e]

    def edit_operation(self, change) -> None:
        path = self.root / OPERATION_REL
        operation = json.loads(path.read_text(encoding="utf-8"))
        change(operation["exposes"])
        path.write_text(json.dumps(operation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_the_official_exposure_is_valid_and_resolves_on_its_fixture(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_a_path_missing_from_the_fixture_is_reported(self) -> None:
        self.edit_operation(lambda e: e["variables"].append(exposed("video.absent", "mediainfo.media.track[@type=Video].Absent")))
        self.assertTrue(any("video.absent" in e and "ne se résout pas" in e for e in self.errors()))

    def test_a_missing_fixture_is_reported(self) -> None:
        (self.root / FIXTURE_REL).unlink()
        self.assertTrue(any("fixture manquante" in e for e in self.errors()))

    def test_a_path_outside_the_probe_enrichment_key_is_reported(self) -> None:
        self.edit_operation(lambda e: e["variables"].append(exposed("video.autre", "media.track[0].Format")))
        self.assertTrue(any("clé d'enrichissement" in e for e in self.errors()))

    def test_a_reserved_namespace_is_reported(self) -> None:
        self.edit_operation(lambda e: e.update(namespace="nodes"))
        self.assertTrue(any("réservé" in e for e in self.errors()))

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.org", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

    def commit_base(self) -> None:
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        os.environ[check_catalogue.BASE_REF_ENV] = "HEAD"

    def test_a_breaking_change_needs_a_major_version_bump(self) -> None:
        self.commit_base()
        self.assertEqual(self.errors(), [])
        self.edit_operation(lambda e: e["variables"].pop())
        breaking = self.errors()
        self.assertTrue(any("changement cassant" in e and "retirée" in e for e in breaking), breaking)
        self.edit_operation(lambda e: e.update(contractVersion="2.0.0"))
        self.assertEqual(self.errors(), [])

    def test_the_contract_version_cannot_decrease_and_additions_are_free(self) -> None:
        self.commit_base()
        self.edit_operation(lambda e: e["variables"].append(exposed("audio.bitrate", "mediainfo.media.track[@type=Audio].Format")))
        self.assertEqual(self.errors(), [])
        self.edit_operation(lambda e: e.update(contractVersion="0.9.0"))
        self.assertTrue(any("diminue" in e for e in self.errors()))

    def test_without_a_base_revision_the_comparison_is_skipped(self) -> None:
        os.environ[check_catalogue.BASE_REF_ENV] = "0000000000000000000000000000000000000000"
        self.edit_operation(lambda e: e["variables"].pop())
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()
