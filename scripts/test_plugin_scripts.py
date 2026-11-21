#!/usr/bin/env python3
"""Tests des scripts de plugins (protocole stdin/stdout JSON), avec de faux outils dans le PATH."""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = {
    "hdr": REPO_ROOT / "plugins/hdr/scripts/hdr.py",
    "archives": REPO_ROOT / "plugins/archives/scripts/archives.py",
    "sous_titres": REPO_ROOT / "plugins/sous-titres/scripts/sous_titres.py",
    "vmaf": REPO_ROOT / "plugins/vmaf/scripts/vmaf.py",
    "guard_size": REPO_ROOT / "scripts/guard-min-size-saving/run.py",
    "integrity": REPO_ROOT / "scripts/integrity-check-media/run.py",
    "route_hdr": REPO_ROOT / "scripts/route-by-hdr-format/run.py",
    "route_codec": REPO_ROOT / "scripts/route-by-video-codec/run.py",
}


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"plugin_{name}", SCRIPTS[name])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_tool(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_script(name: str, bin_dir: Path, payload: dict) -> tuple[int, dict]:
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
    done = subprocess.run([sys.executable, str(SCRIPTS[name])], input=json.dumps(payload),
                          capture_output=True, text=True, env=env)
    return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])


def pgs_segment(pts: float, kind: int, body: bytes) -> bytes:
    return b"PG" + int(pts * 90_000).to_bytes(4, "big") + b"\0\0\0\0" + bytes([kind]) + len(body).to_bytes(2, "big") + body


def synthetic_pgs() -> bytes:
    """Une légende 4×2 (« texte » blanc) de 1 s à 3 s, puis un effacement."""
    pcs_show = (b"\x07\x80\x04\x38\x10" + b"\x00\x01" + b"\x80" + b"\x00" + b"\x00" + b"\x01"
                + b"\x00\x00" + b"\x00" + b"\x00" + (100).to_bytes(2, "big") + (200).to_bytes(2, "big"))
    palette = b"\x00\x00" + bytes([1, 235, 128, 128, 255])
    # Ligne 1 : 4 pixels de couleur 1 (run long) ; ligne 2 : 2 transparents puis 2 blancs.
    rle = bytes([0, 0x80 | 4, 1, 0, 0]) + bytes([0, 2, 1, 1, 0, 0])
    ods = b"\x00\x00" + b"\x00" + b"\xc0" + (len(rle) + 4).to_bytes(3, "big") + (4).to_bytes(2, "big") + (2).to_bytes(2, "big") + rle
    pcs_clear = b"\x07\x80\x04\x38\x10" + b"\x00\x02" + b"\x00" + b"\x00" + b"\x00" + b"\x00"
    return (pgs_segment(1.0, 0x16, pcs_show) + pgs_segment(1.0, 0x14, palette) + pgs_segment(1.0, 0x15, ods)
            + pgs_segment(1.0, 0x80, b"") + pgs_segment(3.0, 0x16, pcs_clear) + pgs_segment(3.0, 0x80, b""))


MKV_INFO = {
    "container": {"type": "Matroska"},
    "tracks": [
        {"id": 0, "type": "video", "properties": {"codec_id": "V_MPEGH/ISO/HEVC", "default_duration": 41708333, "language": "und"}},
        {"id": 1, "type": "audio", "properties": {"codec_id": "A_EAC3", "language": "fre"}},
        {"id": 2, "type": "subtitles", "properties": {"codec_id": "S_HDMV/PGS", "language": "fre", "track_name": "Français"}},
        {"id": 3, "type": "subtitles", "properties": {"codec_id": "S_TEXT/UTF8", "language": "eng"}},
    ],
}
# mkvmerge factice : -J renvoie MKV_INFO ; -o journalise ses arguments et crée la sortie.
FAKE_MKVMERGE = """if [ "$1" = "-J" ]; then cat "$FAKE_INFO"; exit 0; fi
printf '%s\\n' "$@" > "$FAKE_LOG"; out=""; prev=""
for a; do [ "$prev" = "-o" ] && out=$a; prev=$a; done; printf mkv > "$out"
"""
# mkvextract factice : écrit la piste demandée (PGS synthétique pour un .sup).
FAKE_MKVEXTRACT = """spec=$3; target=${spec#*:}
case "$target" in *.sup) cp "$FAKE_SUP" "$target";; *) printf data > "$target";; esac"""


class PureFunctionsTests(unittest.TestCase):
    def test_rle_runs_and_line_ends(self) -> None:
        st = load("sous_titres")
        self.assertEqual(st.decode_rle(bytes([0, 0x80 | 3, 7, 0, 0, 5, 0, 0]), 3, 2), bytes([7, 7, 7, 5, 0, 0]))
        long_run = bytes([0, 0x40 | 1, 0x2C])  # 300 pixels transparents (compte sur 14 bits)
        self.assertEqual(st.decode_rle(long_run, 300, 1), bytes(300))

    def test_pgs_caption_timing_and_rendering(self) -> None:
        st = load("sous_titres")
        captions = st.parse_pgs(synthetic_pgs())
        self.assertEqual(len(captions), 1)
        caption = captions[0]
        self.assertEqual((caption.start, caption.end), (1.0, 3.0))
        width, height, pixels = caption.image
        pad = st.IMAGE_PADDING
        self.assertEqual((width, height), (4 + 2 * pad, 2 + 2 * pad))
        self.assertEqual(pixels[pad * width + pad], 255 - 235)  # texte sombre
        self.assertEqual(pixels[(pad + 1) * width + pad], 255)  # transparent → blanc
        self.assertEqual(pixels[0], 255)

    def test_srt_merges_repeated_captions(self) -> None:
        st = load("sous_titres")
        a = st.Caption(1.0, 2.0, (0, 0, b""), "Bonjour")
        b = st.Caption(2.0, 3.5, (0, 0, b""), "Bonjour ")
        c = st.Caption(4.0, 5.0, (0, 0, b""), "  ")
        self.assertEqual(st.to_srt([a, b, c]), "1\n00:00:01,000 --> 00:00:03,500\nBonjour\n\n")
        self.assertEqual(st.srt_time(3723.0456), "01:02:03,046")

    def test_vmaf_scores_routing_and_model(self) -> None:
        vm = load("vmaf")
        scores = vm.pooled_scores({"pooled_metrics": {"vmaf": {"mean": 94.12345, "min": 80.5, "harmonic_mean": 93.9}}})
        self.assertEqual(scores, {"mean": 94.123, "min": 80.5, "harmonicMean": 93.9})
        self.assertEqual(vm.decide(scores, 93)[0], "true")
        self.assertEqual(vm.decide(scores, 95)[0], "false")
        self.assertIn("vmaf_4k_v0.6.1", vm.vmaf_filter(3840, 2160, Path("l.json"), 5, 4))
        self.assertIn("vmaf_v0.6.1:", vm.vmaf_filter(1920, 1080, Path("l.json"), 5, 4))
        with self.assertRaises(RuntimeError):
            vm.pooled_scores({})

    def test_dolby_vision_profile_parsing(self) -> None:
        hdr = load("hdr")
        self.assertEqual(hdr.DV_PROFILE_RE.search("Summary:\n  Frames: 10\n  Profile: 7 (FEL)\n").group(1), "7")
        with self.assertRaises(hdr.Skip):
            hdr.hevc_track({"container": {"type": "MP4"}, "tracks": []}, "fichier")


class RouteByVideoCodecTests(unittest.TestCase):
    def test_names_of_the_same_codec_are_normalized(self) -> None:
        codec = load("route_codec")
        for alias, name in (("h265", "HEVC"), (" H.265 ", "HEVC"), ("avc", "AVC"), ("H.264", "AVC"), ("AV1", "AV1")):
            self.assertEqual(codec.normalize(alias), name)
        self.assertEqual(codec.normalize(None), "")

    def test_routes_on_the_codec_and_refuses_missing_values(self) -> None:
        codec = load("route_codec")
        self.assertEqual(codec.route("HEVC", "H.265")["nextPort"], "true")
        self.assertEqual(codec.route("AVC", "HEVC")["nextPort"], "false")
        self.assertEqual(codec.route("", "HEVC")["status"], "error")
        self.assertEqual(codec.route("HEVC", None)["status"], "error")

    def test_reads_resolved_variables_from_config_on_stdin(self) -> None:
        for detected, port in (("HEVC", "true"), ("AVC", "false")):
            done = subprocess.run(
                [sys.executable, str(SCRIPTS["route_codec"])],
                input=json.dumps({"config": {"codec": detected, "expected": "HEVC"}}),
                capture_output=True, text=True)
            reply = json.loads(done.stdout.strip().splitlines()[-1])
            self.assertEqual((done.returncode, reply["status"], reply["nextPort"]), (0, "ok", port), reply)


class ScriptProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.work = self.root / "work"
        self.bin.mkdir()
        self.work.mkdir()
        self.log = self.root / "mkvmerge.log"
        info = self.root / "info.json"
        info.write_text(json.dumps(MKV_INFO))
        sup = self.root / "track.sup"
        sup.write_bytes(synthetic_pgs())
        os.environ.update(FAKE_INFO=str(info), FAKE_LOG=str(self.log), FAKE_SUP=str(sup))
        fake_tool(self.bin, "mkvmerge", FAKE_MKVMERGE)
        fake_tool(self.bin, "mkvextract", FAKE_MKVEXTRACT)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def payload(self, working: Path, config: dict, source: Path | None = None) -> dict:
        return {"schemaVersion": "1.0", "workingFile": str(working), "sourceFile": str(source or working),
                "workDir": str(self.work), "mediaInfo": {}, "config": config}

    def test_archive_is_extracted_to_its_largest_video(self) -> None:
        fake_tool(self.bin, "7zz", """if [ "$1" = "l" ]; then exit 0; fi
for a; do case "$a" in -o*) dir=${a#-o};; esac; done
mkdir -p "$dir/Film"; head -c 10 /dev/zero > "$dir/Film/film-sample.mkv"; head -c 5 /dev/zero > "$dir/Film/film.mkv"
""")
        archive = self.work / "film.rar"
        archive.write_bytes(b"Rar!")
        code, reply = run_script("archives", self.bin, self.payload(archive, {}))
        self.assertEqual((code, reply["status"]), (0, "ok"), reply)
        self.assertTrue(reply["workingFile"].endswith("Film/film.mkv"))
        self.assertTrue((self.work / reply["workingFile"]).is_file())

        video = self.work / "deja.mkv"
        video.write_bytes(b"mkv")
        self.assertEqual(run_script("archives", self.bin, self.payload(video, {}))[1]["status"], "skip")

    def test_vmaf_routes_on_threshold_and_reports_scores(self) -> None:
        fake_tool(self.bin, "ffprobe", """echo '{"streams":[{"width":1920,"height":1080}]}'""")
        fake_tool(self.bin, "ffmpeg", """for a; do case "$a" in *log_path=*) p=${a#*log_path=}; p=${p%%:*};; esac; done
echo '{"pooled_metrics":{"vmaf":{"mean":91.5,"min":70,"harmonic_mean":90.8}}}' > "$p"
""")
        encoded, original = self.work / "encode.mkv", self.root / "original.mkv"
        encoded.write_bytes(b"e")
        original.write_bytes(b"o")
        code, reply = run_script("vmaf", self.bin, self.payload(encoded, {"threshold": 90}, source=original))
        self.assertEqual((code, reply["status"], reply["nextPort"]), (0, "ok", "true"), reply)
        self.assertEqual(reply["mediaInfo"]["vmaf"]["mean"], 91.5)
        self.assertEqual(run_script("vmaf", self.bin, self.payload(encoded, {"threshold": 95}, source=original))[1]["nextPort"], "false")
        self.assertEqual(run_script("vmaf", self.bin, self.payload(encoded, {}))[1]["status"], "skip")

    def test_pgs_tracks_become_srt_tracks(self) -> None:
        fake_tool(self.bin, "tesseract", """printf 'Bonjour à tous\\f'""")
        movie = self.work / "film.mkv"
        movie.write_bytes(b"mkv")
        code, reply = run_script("sous_titres", self.bin, self.payload(movie, {"action": "ocr", "languages": "fre", "replace": True}))
        self.assertEqual((code, reply["status"]), (0, "ok"), reply)
        args = self.log.read_text().splitlines()
        self.assertIn("!2", args)
        self.assertIn("0:Français (OCR)", args)
        srt = Path(args[-1])
        self.assertTrue(args[-1].endswith(".srt"))
        self.assertFalse(srt.exists(), "les fichiers temporaires doivent être supprimés")

    def test_text_subtitles_are_resynchronized_with_alass(self) -> None:
        fake_tool(self.bin, "alass-cli", """for a; do prev2=$prev; prev=$a; done; cp "$prev2" "$prev"
""")
        movie = self.work / "film.mkv"
        movie.write_bytes(b"mkv")
        code, reply = run_script("sous_titres", self.bin, self.payload(movie, {"action": "sync", "split_penalty": 12}))
        self.assertEqual((code, reply["status"]), (0, "ok"), reply)
        args = self.log.read_text().splitlines()
        self.assertIn("!3", args)
        self.assertIn("0:eng", args)
        self.assertTrue(args[-1].endswith("3.sync.srt"))

    def test_dolby_vision_profile_7_is_converted_and_others_skipped(self) -> None:
        fake_tool(self.bin, "dovi_tool", """case "$*" in
*extract-rpu*) for a; do last=$a; done; printf rpu > "$last";;
*info*) echo "Profile: ${FAKE_PROFILE:-7} (FEL)";;
*convert*) for a; do last=$a; done; printf p81 > "$last";;
esac""")
        movie = self.work / "film.mkv"
        movie.write_bytes(b"mkv")
        code, reply = run_script("hdr", self.bin, self.payload(movie, {"action": "dv-profile-8"}))
        self.assertEqual((code, reply["status"]), (0, "ok"), reply)
        args = self.log.read_text().splitlines()
        self.assertIn("0:41708333ns", args)
        self.assertIn("-D", args)
        os.environ["FAKE_PROFILE"] = "8"
        try:
            self.assertEqual(run_script("hdr", self.bin, self.payload(movie, {"action": "dv-profile-8"}))[1]["status"], "skip")
        finally:
            os.environ.pop("FAKE_PROFILE")

    def test_guard_min_size_saving_routes_and_restores_source(self) -> None:
        source = self.work / "original.mkv"
        smaller = self.work / "encoded_small.mkv"
        larger = self.work / "encoded_large.mkv"
        source.write_bytes(b"a" * 1000)
        smaller.write_bytes(b"b" * 700)
        larger.write_bytes(b"c" * 950)

        code, ok_reply = run_script(
            "guard_size",
            self.bin,
            self.payload(smaller, {"min_saving_percent": 15, "restore_source_on_reject": True}, source=source),
        )
        self.assertEqual((code, ok_reply["status"], ok_reply["nextPort"]), (0, "ok", "true"), ok_reply)
        self.assertNotIn("workingFile", ok_reply)

        code, rej_reply = run_script(
            "guard_size",
            self.bin,
            self.payload(larger, {"min_saving_percent": 15, "restore_source_on_reject": True}, source=source),
        )
        self.assertEqual((code, rej_reply["status"], rej_reply["nextPort"]), (0, "ok", "false"), rej_reply)
        self.assertEqual(rej_reply["workingFile"], str(source))

    def test_integrity_check_media_with_ffprobe_and_empty_file(self) -> None:
        fake_tool(
            self.bin,
            "ffprobe",
            """cat <<'EOF'
{"format":{"duration":"120.5"},"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}
EOF""",
        )
        movie = self.work / "film.mkv"
        movie.write_bytes(b"mkv-data")
        code, reply = run_script(
            "integrity",
            self.bin,
            self.payload(movie, {"require_video": True, "require_audio": True, "min_duration_seconds": 1}),
        )
        self.assertEqual((code, reply["status"], reply["nextPort"]), (0, "ok", "true"), reply)

        empty = self.work / "empty.mkv"
        empty.write_bytes(b"")
        code, bad_reply = run_script("integrity", self.bin, self.payload(empty, {}))
        self.assertEqual((code, bad_reply["status"], bad_reply["nextPort"]), (0, "ok", "false"), bad_reply)

    def test_route_by_hdr_format_from_mediainfo_and_cli_fallback(self) -> None:
        movie = self.work / "hdr.mkv"
        movie.write_bytes(b"mkv")
        dv_payload = self.payload(movie, {"target_format": "dv-profile-7"})
        dv_payload["mediaInfo"] = {
            "tracks": [
                {"type": "video", "HDR_Format": "Dolby Vision, Version 1.0, dvhe.07.06, BL+EL+RPU"}
            ]
        }
        code, reply = run_script("route_hdr", self.bin, dv_payload)
        self.assertEqual((code, reply["status"], reply["nextPort"]), (0, "ok", "true"), reply)

        fake_tool(
            self.bin,
            "mediainfo",
            """cat <<'EOF'
{"media":{"track":[{"@type":"Video","HDR_Format":"SMPTE ST 2094 App 4, Version 1, HDR10+ Profile B compatible"}]}}
EOF""",
        )
        code, hdr10p = run_script("route_hdr", self.bin, self.payload(movie, {"target_format": "hdr10plus"}))
        self.assertEqual((code, hdr10p["status"], hdr10p["nextPort"]), (0, "ok", "true"), hdr10p)

        code, miss = run_script("route_hdr", self.bin, self.payload(movie, {"target_format": "dolby-vision"}))
        self.assertEqual((code, miss["status"], miss["nextPort"]), (0, "ok", "false"), miss)


if __name__ == "__main__":
    unittest.main()
