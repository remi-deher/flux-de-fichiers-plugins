#!/usr/bin/env python3
"""Routage conditionnel selon le format HDR de la piste vidéo (Dolby Vision, HDR10+, HDR10/HLG)."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DV_PROFILE_7_RE = re.compile(r"dvhe\.07|profile\s*7(?:\b|\.)", re.IGNORECASE)
HDR_TEXT_KEYS = (
    "HDR_Format",
    "HDR_Format_Commercial",
    "HDR_Format_Profile",
    "HDR_Format_Compatibility",
    "transfer_characteristics",
    "hdr_format",
    "hdrFormat",
    "color_transfer",
)


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def collect_video_blobs(media_info: dict | None) -> list[str]:
    if not isinstance(media_info, dict):
        return []
    blobs: list[str] = []

    def inspect_tracks(tracks: object) -> None:
        if not isinstance(tracks, list):
            return
        for track in tracks:
            if not isinstance(track, dict):
                continue
            kind = str(track.get("@type") or track.get("type") or "").lower()
            if kind and kind != "video":
                continue
            for key in HDR_TEXT_KEYS:
                val = track.get(key)
                if isinstance(val, str) and val.strip():
                    blobs.append(val)
            props = track.get("properties")
            if isinstance(props, dict):
                for key in HDR_TEXT_KEYS:
                    val = props.get(key)
                    if isinstance(val, str) and val.strip():
                        blobs.append(val)

    inspect_tracks(media_info.get("tracks"))
    media = media_info.get("media")
    if isinstance(media, dict):
        inspect_tracks(media.get("track"))
    return blobs


def probe_mediainfo(path: Path) -> dict | None:
    if not path.is_file() or not shutil.which("mediainfo"):
        return None
    done = subprocess.run(["mediainfo", "--Output=JSON", str(path)], capture_output=True, text=True)
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def detect_hdr_tags(blobs: list[str]) -> set[str]:
    joined = " | ".join(blobs)
    lower = joined.lower()
    tags: set[str] = set()
    if "dolby vision" in lower or "dvhe." in lower or "dvh1." in lower:
        tags.add("dolby-vision")
        if DV_PROFILE_7_RE.search(joined):
            tags.add("dv-profile-7")
    if "hdr10+" in lower or "smpte st 2094" in lower:
        tags.add("hdr10plus")
    if any(token in lower for token in ("hdr10", "smpte st 2086", "smpte st 2084", "pq", "hlg")):
        tags.add("hdr-static")
    return tags


def matches_target(tags: set[str], target: str) -> bool:
    if target == "dolby-vision":
        return "dolby-vision" in tags
    if target == "dv-profile-7":
        return "dv-profile-7" in tags
    if target == "hdr10plus":
        return "hdr10plus" in tags
    if target == "any-hdr":
        return bool(tags)
    return bool(tags & {"dolby-vision", "hdr10plus"})


def main() -> int:
    payload = json.load(sys.stdin)
    config = payload.get("config") or {}
    target = str(config.get("target_format") or "any-dynamic")
    working = Path(payload.get("workingFile") or "")

    blobs = collect_video_blobs(payload.get("mediaInfo"))
    if not blobs:
        probed = probe_mediainfo(working)
        blobs = collect_video_blobs(probed)

    tags = detect_hdr_tags(blobs)
    matched = matches_target(tags, target)
    summary = ", ".join(sorted(tags)) if tags else "SDR"
    reply(
        "ok",
        f"HDR détecté : {summary} (cible : {target})",
        nextPort="true" if matched else "false",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
