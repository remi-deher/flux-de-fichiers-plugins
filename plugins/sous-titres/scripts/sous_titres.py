#!/usr/bin/env python3
"""Sous-titres : resynchronisation des pistes texte sur l'audio (alass) et conversion des pistes
image PGS en SRT par OCR (Tesseract), dans un fichier Matroska.

Protocole Forgearr : JSON sur stdin (workingFile, workDir, config), réponse JSON sur
stdout (status, message, workingFile). Outils attendus dans le PATH : mkvmerge, mkvextract, et
selon l'action alass-cli (+ ffmpeg) ou tesseract.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

MATROSKA = "Matroska"
OUTPUT_NAME = "sous-titres.mkv"
WARNING_TOLERANT = {"mkvmerge", "mkvextract"}
TEXT_CODECS = {"S_TEXT/UTF8": "srt", "S_TEXT/ASS": "ass", "S_TEXT/SSA": "ssa"}
PGS_CODEC = "S_HDMV/PGS"
ALL = "all"

# Langue de piste (ISO 639-2/B, 639-2/T ou IETF) → modèle Tesseract embarqué.
TESSERACT_LANGUAGES = {
    "eng": "eng", "en": "eng", "fre": "fra", "fra": "fra", "fr": "fra", "ger": "deu", "deu": "deu",
    "de": "deu", "spa": "spa", "es": "spa", "ita": "ita", "it": "ita", "por": "por", "pt": "por",
    "dut": "nld", "nld": "nld", "nl": "nld",
}

# PGS (Presentation Graphic Stream) : segments « PG », horloge à 90 kHz.
PGS_MAGIC = b"PG"
PGS_HEADER = 13
PGS_CLOCK = 90_000
SEG_PDS, SEG_ODS, SEG_PCS, SEG_END = 0x14, 0x15, 0x16, 0x80
ODS_FIRST = 0x80
PCS_CROPPED = 0x40
PCS_OBJECT_SIZE, PCS_CROP_SIZE = 8, 8
DEFAULT_CAPTION_SECONDS = 4.0
IMAGE_PADDING = 12
WHITE = 255
PAGE_SEPARATOR = "\f"


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


def wanted_languages(raw: str) -> set[str] | None:
    """`None` = toutes les langues ; sinon codes en minuscules."""
    codes = {code.strip().lower() for code in (raw or ALL).split(",") if code.strip()}
    return None if not codes or ALL in codes else codes


def track_language(props: dict) -> str:
    ietf = (props.get("language_ietf") or "").split("-")[0].lower()
    return ietf or (props.get("language") or "und").lower()


def tesseract_language(props: dict) -> str | None:
    for name in (track_language(props), (props.get("language") or "").lower()):
        if name in TESSERACT_LANGUAGES:
            return TESSERACT_LANGUAGES[name]
    return None


def language_matches(props: dict, wanted: set[str] | None) -> bool:
    if wanted is None:
        return True
    names = {track_language(props), (props.get("language") or "").lower()}
    names |= {TESSERACT_LANGUAGES[n] for n in list(names) if n in TESSERACT_LANGUAGES}
    return bool(names & wanted)


def subtitle_tracks(working: Path, codecs: set[str], wanted: set[str] | None) -> list[dict]:
    info = json.loads(run("mkvmerge", "-J", str(working)))
    if (info.get("container") or {}).get("type") != MATROSKA:
        raise Skip("conteneur Matroska requis")
    return [t for t in info.get("tracks", [])
            if t.get("type") == "subtitles"
            and (t.get("properties") or {}).get("codec_id") in codecs
            and language_matches(t.get("properties") or {}, wanted)]


def track_options(props: dict, name: str | None = None) -> list[str]:
    options = ["--language", f"0:{props.get('language_ietf') or props.get('language') or 'und'}"]
    title = name if name is not None else props.get("track_name")
    if title:
        options += ["--track-name", f"0:{title}"]
    options += ["--default-track-flag", f"0:{'yes' if props.get('default_track') else 'no'}",
                "--forced-display-flag", f"0:{'yes' if props.get('forced_track') else 'no'}"]
    return options


def remux(working: Path, dropped: list[int], added: list[tuple[Path, list[str]]], target: Path) -> None:
    keep = ["--subtitle-tracks", "!" + ",".join(map(str, dropped))] if dropped else []
    args = ["mkvmerge", "-o", str(target), *keep, str(working)]
    for path, options in added:
        args += [*options, str(path)]
    run(*args)


# --- Synchronisation (alass) -------------------------------------------------------------------

def synchronize(working: Path, tmp: Path, config: dict) -> str:
    tracks = subtitle_tracks(working, set(TEXT_CODECS), wanted_languages(config.get("languages", ALL)))
    if not tracks:
        raise Skip("aucune piste de sous-titres texte à synchroniser")
    penalty = str(config.get("split_penalty", 7))
    added = []
    for track in tracks:
        props = track.get("properties") or {}
        ext = TEXT_CODECS[props["codec_id"]]
        original, synced = tmp / f"{track['id']}.{ext}", tmp / f"{track['id']}.sync.{ext}"
        run("mkvextract", str(working), "tracks", f"{track['id']}:{original}")
        options = ["--split-penalty", penalty]
        if config.get("no_splits"):
            options.append("--no-split")
        run("alass-cli", *options, str(working), str(original), str(synced))
        added.append((synced, track_options(props)))
    remux(working, [t["id"] for t in tracks], added, tmp / OUTPUT_NAME)
    return f"{len(tracks)} piste(s) de sous-titres resynchronisée(s)"


# --- PGS → SRT (Tesseract) ---------------------------------------------------------------------

@dataclass
class Caption:
    start: float
    end: float | None
    image: tuple[int, int, bytes]  # largeur, hauteur, pixels gris
    text: str = field(default="")


def decode_rle(data: bytes, width: int, height: int) -> bytes:
    """Décode l'image RLE d'un segment ODS en indices de palette (largeur × hauteur)."""
    out = bytearray()
    i, line_start = 0, 0
    while i < len(data) and len(out) < width * height:
        byte = data[i]
        i += 1
        if byte:
            out.append(byte)
            continue
        flag = data[i]
        i += 1
        if flag == 0:  # fin de ligne : complète avec la couleur 0
            filled = len(out) - line_start
            if filled < width:
                out.extend(b"\0" * (width - filled))
            line_start = len(out)
            continue
        count = flag & 0x3F
        if flag & 0x40:
            count = (count << 8) | data[i]
            i += 1
        color = 0
        if flag & 0x80:
            color = data[i]
            i += 1
        out.extend(bytes([color]) * count)
    out.extend(b"\0" * (width * height - len(out)))
    return bytes(out[: width * height])


def render(objects: dict, refs: list, palette: dict) -> tuple[int, int, bytes]:
    """Compose les objets d'une légende sur fond blanc, texte sombre (meilleur pour l'OCR)."""
    placed = [(x, y, objects[oid]) for oid, x, y in refs if oid in objects]
    if not placed:
        return 0, 0, b""
    left = min(x for x, _, _ in placed) - IMAGE_PADDING
    top = min(y for _, y, _ in placed) - IMAGE_PADDING
    width = max(x + o["width"] for x, _, o in placed) - left + IMAGE_PADDING
    height = max(y + o["height"] for _, y, o in placed) - top + IMAGE_PADDING
    canvas = bytearray([WHITE]) * (width * height)
    gray = {index: WHITE - (luma * alpha) // 255 for index, (luma, alpha) in palette.items()}
    for x, y, obj in placed:
        pixels = decode_rle(bytes(obj["rle"]), obj["width"], obj["height"])
        for row in range(obj["height"]):
            base = (y - top + row) * width + (x - left)
            line = pixels[row * obj["width"]:(row + 1) * obj["width"]]
            canvas[base:base + obj["width"]] = bytes(gray.get(index, WHITE) for index in line)
    return width, height, bytes(canvas)


def parse_pgs(data: bytes) -> list[Caption]:
    """Légendes d'un flux PGS (.sup) : début, fin et image rendue."""
    captions: list[Caption] = []
    palettes: dict[int, dict] = {}
    objects: dict[int, dict] = {}
    pending = None
    pos = 0
    while pos + PGS_HEADER <= len(data):
        if data[pos:pos + 2] != PGS_MAGIC:
            raise ValueError(f"segment PGS invalide à l'octet {pos}")
        pts = int.from_bytes(data[pos + 2:pos + 6], "big") / PGS_CLOCK
        kind = data[pos + 10]
        size = int.from_bytes(data[pos + 11:pos + 13], "big")
        body = data[pos + PGS_HEADER:pos + PGS_HEADER + size]
        pos += PGS_HEADER + size
        if kind == SEG_PCS:
            if captions and captions[-1].end is None:
                captions[-1].end = pts
            refs, offset = [], 11
            for _ in range(body[10]):
                oid = int.from_bytes(body[offset:offset + 2], "big")
                x = int.from_bytes(body[offset + 4:offset + 6], "big")
                y = int.from_bytes(body[offset + 6:offset + 8], "big")
                cropped = body[offset + 3] & PCS_CROPPED
                offset += PCS_OBJECT_SIZE + (PCS_CROP_SIZE if cropped else 0)
                refs.append((oid, x, y))
            pending = (pts, refs, body[9]) if refs else None
        elif kind == SEG_PDS:
            entries = palettes.setdefault(body[0], {})
            for k in range(2, len(body) - 4, 5):
                entries[body[k]] = (body[k + 1], body[k + 4])  # (luminance Y, alpha)
        elif kind == SEG_ODS:
            oid = int.from_bytes(body[0:2], "big")
            if body[3] & ODS_FIRST:
                objects[oid] = {"width": int.from_bytes(body[7:9], "big"),
                                "height": int.from_bytes(body[9:11], "big"),
                                "rle": bytearray(body[11:])}
            elif oid in objects:
                objects[oid]["rle"] += body[4:]
        elif kind == SEG_END and pending:
            start, refs, palette_id = pending
            image = render(objects, refs, palettes.get(palette_id, {}))
            if image[0]:
                captions.append(Caption(start, None, image))
            pending = None
    if captions and captions[-1].end is None:
        captions[-1].end = captions[-1].start + DEFAULT_CAPTION_SECONDS
    return captions


def write_pgm(path: Path, image: tuple[int, int, bytes]) -> None:
    width, height, pixels = image
    path.write_bytes(f"P5\n{width} {height}\n255\n".encode() + pixels)


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def to_srt(captions: list[Caption]) -> str:
    blocks, previous = [], None
    for caption in captions:
        text = caption.text.strip()
        if not text:
            continue
        if previous and previous.text.strip() == text and abs(previous.end - caption.start) < 0.05:
            previous.end = caption.end  # même légende réaffichée (mise à jour de palette)
            continue
        blocks.append(caption)
        previous = caption
    return "".join(f"{n}\n{srt_time(c.start)} --> {srt_time(c.end)}\n{c.text.strip()}\n\n"
                   for n, c in enumerate(blocks, 1))


def ocr_captions(captions: list[Caption], language: str, tmp: Path) -> None:
    """Un seul appel Tesseract pour toutes les images ; pages séparées par un saut de page."""
    listing = tmp / f"pages-{language}.txt"
    paths = []
    for index, caption in enumerate(captions):
        image = tmp / f"{language}-{index:05}.pgm"
        write_pgm(image, caption.image)
        paths.append(str(image))
    listing.write_text("\n".join(paths) + "\n")
    pages = run("tesseract", str(listing), "stdout", "-l", language, "--psm", "6").split(PAGE_SEPARATOR)
    for caption, text in zip(captions, pages):
        caption.text = text


def ocr(working: Path, tmp: Path, config: dict) -> str:
    tracks = subtitle_tracks(working, {PGS_CODEC}, wanted_languages(config.get("languages", ALL)))
    tracks = [t for t in tracks if tesseract_language(t.get("properties") or {})]
    if not tracks:
        raise Skip("aucune piste PGS dans une langue reconnue")
    added = []
    for track in tracks:
        props = track.get("properties") or {}
        language = tesseract_language(props)
        sup = tmp / f"{track['id']}.sup"
        run("mkvextract", str(working), "tracks", f"{track['id']}:{sup}")
        captions = parse_pgs(sup.read_bytes())
        if not captions:
            continue
        ocr_captions(captions, language, tmp)
        srt = tmp / f"{track['id']}.srt"
        srt.write_text(to_srt(captions), encoding="utf-8")
        name = f"{props.get('track_name') or language} (OCR)"
        added.append((srt, track_options({**props, "default_track": False}, name=name)))
    if not added:
        raise Skip("pistes PGS vides")
    dropped = [t["id"] for t in tracks] if config.get("replace") else []
    remux(working, dropped, added, tmp / OUTPUT_NAME)
    return f"{len(added)} piste(s) PGS converties en SRT"


ACTIONS = {"sync": synchronize, "ocr": ocr}


def main() -> None:
    payload = json.load(sys.stdin)
    config = payload.get("config") or {}
    action = ACTIONS.get(config.get("action", ""))
    if action is None:
        reply("error", f"action inconnue : {config.get('action')!r}")
        sys.exit(1)
    work_dir = Path(payload["workDir"])
    tmp = Path(tempfile.mkdtemp(prefix="sous-titres-", dir=work_dir))
    try:
        message = action(Path(payload["workingFile"]), tmp, config)
        output = work_dir / f"{tmp.name}-{OUTPUT_NAME}"
        shutil.move(tmp / OUTPUT_NAME, output)
        reply("ok", message, workingFile=output.name)
    except Skip as skipped:
        reply("skip", str(skipped))
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as error:
        reply("error", str(error))
        sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
