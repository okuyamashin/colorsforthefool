#!/usr/bin/env python3
"""Build a 1920x1080 video of the 22 majors over an arcana song."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIRST = DATA / "The First Turn — Arcana 0 to X.mp3"
SECOND = DATA / "The Second Turn — Arcana XI to XXI.mp3"
ENGLISH = ROOT / "audio" / "The Fool's Journey — Arcana 0 to XXI.mp3"
BACK = DATA / "cardback.jpg"
FIRST_LEN = 252.432
SECOND_LEN = 242.952
ENGLISH_LEN = 411.840
FADE = 0.8
FPS = 30
PAPER = "0xF4EAD8"


def face(card):
    return DATA / card / "face.jpg"


def english_timeline():
    """Boundaries are the moment the next picture is fully visible."""
    cues = [
        (0.0, BACK),
        (15.5, face("the-fool")),
        (31.5, face("the-magician")),
        (54.5, face("the-high-priestess")),
        (73.5, face("the-empress")),
        (89.5, face("the-emperor")),
        (107.5, face("the-hierophant")),
        (122.5, face("the-lovers")),
        (136.5, face("the-chariot")),
        (155.5, face("strength")),
        (169.5, face("the-hermit")),
        (188.5, face("wheel-of-fortune")),
        (202.5, face("justice")),
        (221.5, face("the-hanged-man")),
        (236.5, face("death")),
        (251.5, face("temperance")),
        (265.5, face("the-devil")),
        (283.5, face("the-tower")),
        (298.5, face("the-star")),
        (313.5, face("the-moon")),
        (331.5, face("the-sun")),
        (350.5, face("judgement")),
        (366.5, face("the-world")),
        (386.5, face("the-fool")),
    ]
    return cues, ENGLISH_LEN, [ENGLISH]


def timeline():
    """Boundaries are the moment the next picture is fully visible."""
    second = FIRST_LEN
    cues = [
        (0.0, BACK),
        (11.0, face("the-fool")),
        (31.6, face("the-magician")),
        (50.8, face("the-high-priestess")),
        (75.1, face("the-empress")),
        (91.4, face("the-emperor")),
        (109.5, face("the-hierophant")),
        (136.2, BACK),
        (146.0, face("the-lovers")),
        (163.0, face("the-chariot")),
        (179.3, face("strength")),
        (199.3, face("the-hermit")),
        (216.7, face("wheel-of-fortune")),
        (247.0, BACK),
        (second + 16.6, face("justice")),
        (second + 50.4, face("the-hanged-man")),
        (second + 67.4, face("death")),
        (second + 82.0, face("temperance")),
        (second + 96.8, face("the-devil")),
        (second + 113.7, face("the-tower")),
        (second + 131.6, face("the-star")),
        (second + 147.8, face("the-moon")),
        (second + 165.6, face("the-sun")),
        (second + 182.6, face("judgement")),
        (second + 198.8, face("the-world")),
        (second + 237.0, face("the-fool")),
    ]
    return cues, FIRST_LEN + SECOND_LEN, [FIRST, SECOND]


def clip_durations(spans):
    durations = []
    for index, span in enumerate(spans):
        if span <= FADE:
            raise SystemExit(f"segment {index} is {span:.3f}s, shorter than the fade")
        durations.append(span if index == 0 else span + FADE)
    return durations


def build(until, output, ffmpeg, song):
    cues, total, tracks = english_timeline() if song == "en" else timeline()
    if until is not None:
        if until <= cues[1][0]:
            raise SystemExit("--until must pass the first card")
        cues = [cue for cue in cues if cue[0] < until]
        total = until
    for _, image in cues:
        if not image.is_file():
            raise SystemExit(f"missing image: {image}")
    bounds = [start for start, _ in cues] + [total]
    spans = [bounds[index + 1] - bounds[index] for index in range(len(cues))]
    durations = clip_durations(spans)

    filters = []
    for index in range(len(cues)):
        filters.append(
            f"[{index}:v]scale=720:1080:flags=lanczos,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={PAPER},"
            f"setsar=1,fps={FPS},format=yuv420p[v{index}]"
        )
    current = "v0"
    elapsed = 0.0
    for index in range(len(cues) - 1):
        elapsed += durations[index]
        offset = elapsed - (index + 1) * FADE
        nxt = f"x{index + 1}"
        filters.append(
            f"[{current}][v{index + 1}]xfade=transition=fade:"
            f"duration={FADE}:offset={offset:.3f}[{nxt}]"
        )
        current = nxt
    audio_index = len(cues)
    if len(tracks) == 1:
        filters.append(
            f"[{audio_index}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]"
        )
    else:
        filters.append(
            f"[{audio_index}:a][{audio_index + 1}:a]concat=n=2:v=0:a=1,atrim=0:{total:.3f},"
            f"asetpts=PTS-STARTPTS[a]"
        )

    command = [ffmpeg, "-y", "-hide_banner"]
    for index, ((_, image), duration) in enumerate(zip(cues, durations)):
        command.extend(
            ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(image)]
        )
    for track in tracks:
        command.extend(["-i", str(track)])
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{current}]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"segments {len(cues)}  length {total:.3f}s  -> {output}")
    subprocess.run(command, check=True)


def default_ffmpeg():
    local = ROOT / "video" / "ffmpeg"
    if local.is_file():
        return str(local)
    return shutil.which("ffmpeg") or "ffmpeg"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", choices=("ja", "en"), default="ja")
    parser.add_argument("--until", type=float, help="stop at this many seconds, for a short check")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ffmpeg", default=default_ffmpeg())
    args = parser.parse_args()
    output = args.output
    if output is None:
        name = "arcana-turns-en.mp4" if args.song == "en" else "arcana-turns.mp4"
        output = ROOT / "video" / name
    try:
        build(args.until, output, args.ffmpeg, args.song)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)


if __name__ == "__main__":
    main()
