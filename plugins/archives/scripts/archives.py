#!/usr/bin/env python3
"""Archives : extrait une archive (7z, RAR, ZIP, TAR…) avec 7-Zip et poursuit le flux sur le plus
gros fichier vidéo qu'elle contient. Un fichier qui n'est pas une archive est laissé tel quel.

Protocole Flux de Fichiers : JSON sur stdin, réponse JSON sur stdout. Outil attendu dans le
PATH : 7zz.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".m2ts", ".webm", ".wmv", ".mpg", ".mpeg"}
# 7-Zip : 0 = succès, 1 = avertissement (fichiers verrouillés, etc.).
SEVEN_ZIP_OK = (0, 1)


class Skip(Exception):
    """Étape sans objet pour ce fichier."""


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def is_archive(path: Path) -> bool:
    """Un fichier vidéo n'en est jamais une ; sinon `7zz l` ne réussit que sur une archive reconnue."""
    if path.suffix.lower() in VIDEO_EXTENSIONS:
        return False
    listed = subprocess.run(["7zz", "l", "-p-", "-ba", str(path)], capture_output=True, text=True)
    return listed.returncode in SEVEN_ZIP_OK


def pick_video(folder: Path) -> Path:
    """Plus gros fichier vidéo extrait (les échantillons « sample » sont ignorés s'il y a mieux)."""
    videos = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    if not videos:
        raise RuntimeError("aucun fichier vidéo dans l'archive")
    return max(videos, key=lambda p: (("sample" not in p.name.lower()), p.stat().st_size))


def extract(working: Path, work_dir: Path) -> Path:
    if not is_archive(working):
        raise Skip("le fichier n'est pas une archive")
    target = Path(tempfile.mkdtemp(prefix="archive-", dir=work_dir))
    # -p- : jamais de demande de mot de passe ; une archive chiffrée échoue proprement.
    done = subprocess.run(["7zz", "x", "-y", "-p-", f"-o{target}", str(working)],
                          capture_output=True, text=True)
    if done.returncode not in SEVEN_ZIP_OK:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(f"7zz : {(done.stderr or done.stdout).strip()[-400:]}")
    return pick_video(target)


def main() -> None:
    payload = json.load(sys.stdin)
    work_dir = Path(payload["workDir"])
    try:
        video = extract(Path(payload["workingFile"]), work_dir)
        reply("ok", f"extrait : {video.name}", workingFile=str(video.relative_to(work_dir)))
    except Skip as skipped:
        reply("skip", str(skipped))
    except (RuntimeError, OSError, json.JSONDecodeError) as error:
        reply("error", str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
