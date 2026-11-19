#!/usr/bin/env python3
"""Contrôle d'intégrité rapide d'un média via ffprobe (ou mkvmerge -J en repli)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

NS_PER_SECOND = 1_000_000_000.0
DEFAULT_MIN_DURATION_SECONDS = 1.0


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def probe_with_ffprobe(path: Path) -> tuple[bool, float, set[str], str]:
    done = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()[-200:]
        return False, 0.0, set(), f"ffprobe a échoué : {detail}"
    try:
        data = json.loads(done.stdout)
    except ValueError as err:
        return False, 0.0, set(), f"Sortie ffprobe invalide : {err}"

    kinds = {
        s.get("codec_type")
        for s in data.get("streams", [])
        if isinstance(s, dict) and isinstance(s.get("codec_type"), str)
    }
    raw_duration = (data.get("format") or {}).get("duration")
    try:
        duration = float(raw_duration) if raw_duration is not None else 0.0
    except (TypeError, ValueError):
        duration = 0.0
    return True, duration, kinds, ""


def probe_with_mkvmerge(path: Path) -> tuple[bool, float, set[str], str]:
    done = subprocess.run(["mkvmerge", "-J", str(path)], capture_output=True, text=True)
    if done.returncode not in (0, 1):
        detail = (done.stderr or done.stdout).strip()[-200:]
        return False, 0.0, set(), f"mkvmerge a échoué : {detail}"
    try:
        data = json.loads(done.stdout)
    except ValueError as err:
        return False, 0.0, set(), f"Sortie mkvmerge invalide : {err}"
    if not (data.get("container") or {}).get("recognized", True):
        return False, 0.0, set(), "Conteneur non reconnu par mkvmerge"

    kinds = {
        t.get("type")
        for t in data.get("tracks", [])
        if isinstance(t, dict) and isinstance(t.get("type"), str)
    }
    ns = ((data.get("container") or {}).get("properties") or {}).get("duration")
    duration = float(ns) / NS_PER_SECOND if isinstance(ns, (int, float)) else 0.0
    return True, duration, kinds, ""


def check_media(
    working: Path,
    require_video: bool,
    require_audio: bool,
    min_duration: float,
) -> dict:
    if not working.is_file():
        return {"status": "ok", "nextPort": "false", "message": f"Fichier absent : {working}"}
    if working.stat().st_size <= 0:
        return {"status": "ok", "nextPort": "false", "message": "Fichier vide (0 octet)"}

    if shutil.which("ffprobe"):
        ok, duration, kinds, err = probe_with_ffprobe(working)
    elif shutil.which("mkvmerge"):
        ok, duration, kinds, err = probe_with_mkvmerge(working)
    else:
        return {
            "status": "error",
            "message": "Aucun outil d'inspection disponible (ffprobe ou mkvmerge requis)",
        }

    if not ok:
        return {"status": "ok", "nextPort": "false", "message": err}
    if require_video and "video" not in kinds:
        return {"status": "ok", "nextPort": "false", "message": "Aucune piste vidéo détectée"}
    if require_audio and "audio" not in kinds:
        return {"status": "ok", "nextPort": "false", "message": "Aucune piste audio détectée"}
    if min_duration > 0 and duration < min_duration:
        return {
            "status": "ok",
            "nextPort": "false",
            "message": f"Durée insuffisante : {duration:.2f} s < {min_duration:.2f} s",
        }

    return {
        "status": "ok",
        "nextPort": "true",
        "message": f"Média valide ({duration:.1f} s, pistes : {', '.join(sorted(kinds)) or 'aucune'})",
    }


def main() -> int:
    payload = json.load(sys.stdin)
    config = payload.get("config") or {}
    working = Path(payload.get("workingFile") or "")
    require_video = bool(config.get("require_video", True))
    require_audio = bool(config.get("require_audio", False))
    min_duration = float(config.get("min_duration_seconds", DEFAULT_MIN_DURATION_SECONDS))

    outcome = check_media(working, require_video, require_audio, min_duration)
    reply(outcome.pop("status"), outcome.pop("message"), **outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
