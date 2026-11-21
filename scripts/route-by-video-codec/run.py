#!/usr/bin/env python3
"""Routage selon le codec vidéo, lu dans la variable exposée par MediaInfo (`{{mediainfo.video.codec}}`)."""
import json
import sys

# Noms usuels d'un même codec, ramenés à ceux que MediaInfo écrit dans `Format`.
CODEC_ALIASES = {
    "H265": "HEVC",
    "H.265": "HEVC",
    "H264": "AVC",
    "H.264": "AVC",
}


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def normalize(codec: object) -> str:
    text = str(codec or "").strip().upper()
    return CODEC_ALIASES.get(text, text)


def route(detected: object, expected: object) -> dict:
    found, wanted = normalize(detected), normalize(expected)
    if not found:
        return {"status": "error", "message": "Codec vidéo introuvable : la variable `codec` est vide"}
    if not wanted:
        return {"status": "error", "message": "Codec attendu non renseigné (variable `expected`)"}
    if found == wanted:
        return {"status": "ok", "nextPort": "true", "message": f"Codec {found} : branche « Codec attendu »"}
    return {"status": "ok", "nextPort": "false", "message": f"Codec {found} différent de {wanted} : branche « Autre codec »"}


def main() -> int:
    config = json.load(sys.stdin).get("config") or {}
    outcome = route(config.get("codec"), config.get("expected"))
    reply(outcome.pop("status"), outcome.pop("message"), **outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
