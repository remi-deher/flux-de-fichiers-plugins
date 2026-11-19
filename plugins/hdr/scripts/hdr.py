#!/usr/bin/env python3
"""HDR et Dolby Vision : conversion du profil 7 en 8.1 et réinjection des métadonnées dynamiques
(RPU Dolby Vision, HDR10+) de l'original dans un réencodage HEVC.

Protocole Flux de Fichiers : JSON sur stdin (workingFile, sourceFile, workDir, config), réponse
JSON sur stdout (status, message, workingFile). Outils attendus dans le PATH : mkvmerge,
mkvextract, dovi_tool, hdr10plus_tool.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HEVC_CODEC_ID = "V_MPEGH/ISO/HEVC"
MATROSKA = "Matroska"
DV_PROFILE_RE = re.compile(r"Profile:\s*(\d+)")
DV_CONVERT_TO_81 = "2"  # dovi_tool -m 2 : conversion du RPU vers le profil 8.1
OUTPUT_NAME = "hdr.mkv"
# MKVToolNix signale un simple avertissement par le code 1.
WARNING_TOLERANT = {"mkvmerge", "mkvextract"}


class Skip(Exception):
    """Étape sans objet pour ce fichier."""


def run(*args: str) -> str:
    done = subprocess.run(args, capture_output=True, text=True)
    accepted = (0, 1) if args[0] in WARNING_TOLERANT else (0,)
    if done.returncode not in accepted:
        raise RuntimeError(f"{args[0]} : {(done.stderr or done.stdout).strip()[-400:]}")
    return done.stdout


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def identify(path: Path) -> dict:
    return json.loads(run("mkvmerge", "-J", str(path)))


def hevc_track(info: dict, label: str) -> dict:
    if (info.get("container") or {}).get("type") != MATROSKA:
        raise Skip(f"{label} : conteneur Matroska requis")
    for track in info.get("tracks", []):
        if track.get("type") == "video":
            if (track.get("properties") or {}).get("codec_id") != HEVC_CODEC_ID:
                raise Skip(f"{label} : la vidéo n'est pas en HEVC")
            return track
    raise Skip(f"{label} : aucune piste vidéo")


def extract_video(path: Path, track: dict, target: Path) -> Path:
    run("mkvextract", str(path), "tracks", f"{track['id']}:{target}")
    return target


def dv_profile(rpu: Path) -> int | None:
    summary = run("dovi_tool", "info", "-i", str(rpu), "--summary")
    match = DV_PROFILE_RE.search(summary)
    return int(match.group(1)) if match else None


def extract_rpu(video: Path, target: Path, convert: bool) -> Path | None:
    mode = ["-m", DV_CONVERT_TO_81] if convert else []
    done = subprocess.run(["dovi_tool", *mode, "extract-rpu", "-i", str(video), "-o", str(target)],
                          capture_output=True, text=True)
    return target if done.returncode == 0 and target.is_file() and target.stat().st_size else None


def remux(original: Path, track: dict, video: Path, target: Path) -> Path:
    """Remplace la piste vidéo de `original` par `video`, en gardant cadence et langue."""
    props = track.get("properties") or {}
    options: list[str] = []
    if props.get("default_duration"):
        options += ["--default-duration", f"0:{props['default_duration']}ns"]
    language = props.get("language_ietf") or props.get("language")
    if language:
        options += ["--language", f"0:{language}"]
    if props.get("track_name"):
        options += ["--track-name", f"0:{props['track_name']}"]
    run("mkvmerge", "-o", str(target), *options, str(video), "-D", str(original))
    return target


def dv_to_profile_8(working: Path, tmp: Path) -> str:
    track = hevc_track(identify(working), "fichier")
    video = extract_video(working, track, tmp / "video.hevc")
    rpu = extract_rpu(video, tmp / "rpu.bin", convert=False)
    if rpu is None:
        raise Skip("pas de Dolby Vision")
    profile = dv_profile(rpu)
    if profile != 7:
        raise Skip(f"Dolby Vision profil {profile} : conversion inutile")
    converted = tmp / "video.p81.hevc"
    run("dovi_tool", "-m", DV_CONVERT_TO_81, "convert", "--discard", "-i", str(video), "-o", str(converted))
    remux(working, track, converted, tmp / OUTPUT_NAME)
    return "Dolby Vision converti du profil 7 en 8.1"


def reinject(working: Path, source: Path, tmp: Path, kind: str) -> str:
    if working.resolve() == source.resolve():
        raise Skip("aucun réencodage à compléter")
    ref_video = extract_video(source, hevc_track(identify(source), "original"), tmp / "original.hevc")
    track = hevc_track(identify(working), "réencodage")
    if kind == "dv":
        metadata = extract_rpu(ref_video, tmp / "rpu.bin", convert=True)
        if metadata is None:
            raise Skip("l'original n'a pas de Dolby Vision")
    else:
        metadata = tmp / "hdr10plus.json"
        done = subprocess.run(["hdr10plus_tool", "extract", "-i", str(ref_video), "-o", str(metadata)],
                              capture_output=True, text=True)
        if done.returncode != 0 or not metadata.is_file():
            raise Skip("l'original n'a pas de métadonnées HDR10+")
    ref_video.unlink()
    video = extract_video(working, track, tmp / "video.hevc")
    injected = tmp / "video.injected.hevc"
    if kind == "dv":
        run("dovi_tool", "inject-rpu", "-i", str(video), "--rpu-in", str(metadata), "-o", str(injected))
    else:
        run("hdr10plus_tool", "inject", "-i", str(video), "-j", str(metadata), "-o", str(injected))
    remux(working, track, injected, tmp / OUTPUT_NAME)
    return "RPU Dolby Vision réinjecté (profil 8.1)" if kind == "dv" else "métadonnées HDR10+ réinjectées"


ACTIONS = {
    "dv-profile-8": lambda working, source, tmp: dv_to_profile_8(working, tmp),
    "dv-reinject": lambda working, source, tmp: reinject(working, source, tmp, "dv"),
    "hdr10plus-reinject": lambda working, source, tmp: reinject(working, source, tmp, "hdr10plus"),
}


def main() -> None:
    payload = json.load(sys.stdin)
    config = payload.get("config") or {}
    action = ACTIONS.get(config.get("action", ""))
    if action is None:
        reply("error", f"action inconnue : {config.get('action')!r}")
        sys.exit(1)
    work_dir = Path(payload["workDir"])
    tmp = Path(tempfile.mkdtemp(prefix="hdr-", dir=work_dir))
    try:
        message = action(Path(payload["workingFile"]), Path(payload["sourceFile"]), tmp)
        output = work_dir / f"{tmp.name}-{OUTPUT_NAME}"
        shutil.move(tmp / OUTPUT_NAME, output)
        reply("ok", message, workingFile=output.name)
    except Skip as skipped:
        reply("skip", str(skipped))
    except (RuntimeError, OSError, json.JSONDecodeError) as error:
        reply("error", str(error))
        sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
