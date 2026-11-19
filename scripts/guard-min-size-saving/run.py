#!/usr/bin/env python3
"""Garde-fou de taille : compare workingFile à sourceFile et route via nextPort."""
import json
import sys
from pathlib import Path

DEFAULT_MIN_SAVING_PERCENT = 10.0


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def evaluate_saving(working: Path, source: Path, min_saving: float, restore_source: bool) -> dict:
    if not working.is_file():
        return {"status": "error", "message": f"Fichier courant introuvable : {working}"}
    if not source.is_file():
        return {"status": "error", "message": f"Fichier source introuvable : {source}"}

    source_size = source.stat().st_size
    working_size = working.stat().st_size
    if source_size <= 0:
        return {"status": "skip", "message": "Fichier source vide, comparaison ignorée"}

    saving_percent = ((source_size - working_size) / source_size) * 100.0
    if saving_percent >= min_saving:
        return {
            "status": "ok",
            "nextPort": "true",
            "message": f"Gain retenu : {saving_percent:.1f} % (seuil {min_saving:.1f} %)",
        }

    result = {
        "status": "ok",
        "nextPort": "false",
        "message": f"Gain insuffisant : {saving_percent:.1f} % < {min_saving:.1f} %",
    }
    if restore_source:
        result["workingFile"] = str(source)
    return result


def main() -> int:
    payload = json.load(sys.stdin)
    config = payload.get("config") or {}
    working = Path(payload.get("workingFile") or "")
    source = Path(payload.get("sourceFile") or working)
    min_saving = float(config.get("min_saving_percent", DEFAULT_MIN_SAVING_PERCENT))
    restore_source = bool(config.get("restore_source_on_reject", True))

    outcome = evaluate_saving(working, source, min_saving, restore_source)
    reply(outcome.pop("status"), outcome.pop("message"), **outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
