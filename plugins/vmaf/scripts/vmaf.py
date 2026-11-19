#!/usr/bin/env python3
"""Qualité VMAF : mesure la qualité perçue du fichier courant par rapport à l'original de la
tâche (libvmaf) et oriente le flux vers « true » (seuil atteint) ou « false ».

Protocole Forgearr : JSON sur stdin (workingFile, sourceFile, workDir, config), réponse
JSON sur stdout (status, message, nextPort, mediaInfo). Outils attendus dans le PATH : ffmpeg et
ffprobe compilés avec libvmaf.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_THRESHOLD = 93.0
DEFAULT_SUBSAMPLE = 5
UHD_MIN_HEIGHT = 1440
MODEL_HD, MODEL_UHD = "vmaf_v0.6.1", "vmaf_4k_v0.6.1"
PORT_PASS, PORT_FAIL = "true", "false"


class Skip(Exception):
    """Étape sans objet pour ce fichier."""


def reply(status: str, message: str, **extra) -> None:
    print(json.dumps({"status": status, "message": message, **extra}))


def video_size(path: Path) -> tuple[int, int]:
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height", "-of", "json", str(path)], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"ffprobe : {done.stderr.strip()[-300:]}")
    streams = json.loads(done.stdout).get("streams") or []
    if not streams:
        raise Skip(f"aucune piste vidéo dans {path.name}")
    return int(streams[0]["width"]), int(streams[0]["height"])


def vmaf_filter(width: int, height: int, log: Path, subsample: int, threads: int) -> str:
    """Le fichier mesuré est mis à l'échelle de l'original ; les deux repartent de t=0."""
    model = MODEL_UHD if height >= UHD_MIN_HEIGHT else MODEL_HD
    return (f"[0:v]scale={width}:{height}:flags=bicubic,setpts=PTS-STARTPTS[mesure];"
            f"[1:v]setpts=PTS-STARTPTS[reference];"
            f"[mesure][reference]libvmaf=model=version={model}:log_fmt=json:log_path={log}"
            f":n_subsample={subsample}:n_threads={threads}")


def pooled_scores(log: dict) -> dict:
    vmaf = (log.get("pooled_metrics") or {}).get("vmaf") or {}
    if "mean" not in vmaf:
        raise RuntimeError("journal libvmaf sans score")
    return {"mean": round(vmaf["mean"], 3), "min": round(vmaf.get("min", vmaf["mean"]), 3),
            "harmonicMean": round(vmaf.get("harmonic_mean", vmaf["mean"]), 3)}


def decide(scores: dict, threshold: float) -> tuple[str, str]:
    ok = scores["mean"] >= threshold
    verdict = "conforme" if ok else "insuffisant"
    return (PORT_PASS if ok else PORT_FAIL), f"VMAF {scores['mean']:.2f} (seuil {threshold:g}) : {verdict}"


def measure(working: Path, source: Path, work_dir: Path, config: dict) -> tuple[str, str, dict]:
    if working.resolve() == source.resolve():
        raise Skip("aucun encodage à comparer à l'original")
    threshold = float(config.get("threshold", DEFAULT_THRESHOLD))
    subsample = max(1, int(config.get("subsample", DEFAULT_SUBSAMPLE)))
    width, height = video_size(source)
    with tempfile.TemporaryDirectory(prefix="vmaf-", dir=work_dir) as tmp:
        log = Path(tmp) / "vmaf.json"
        done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(working), "-i", str(source),
                               "-lavfi", vmaf_filter(width, height, log, subsample, os.cpu_count() or 1),
                               "-f", "null", "-"], capture_output=True, text=True)
        if done.returncode != 0 or not log.is_file():
            raise RuntimeError(f"ffmpeg : {done.stderr.strip()[-400:]}")
        scores = pooled_scores(json.loads(log.read_text()))
    port, message = decide(scores, threshold)
    scores.update(threshold=threshold, model=MODEL_UHD if height >= UHD_MIN_HEIGHT else MODEL_HD)
    return port, message, scores


def main() -> None:
    payload = json.load(sys.stdin)
    try:
        port, message, scores = measure(Path(payload["workingFile"]), Path(payload["sourceFile"]),
                                        Path(payload["workDir"]), payload.get("config") or {})
        reply("ok", message, nextPort=port, mediaInfo={"vmaf": scores})
    except Skip as skipped:
        reply("skip", str(skipped))
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        reply("error", str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
